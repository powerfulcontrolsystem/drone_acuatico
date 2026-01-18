#!/usr/bin/env python3
"""
SERVIDOR WEB DEL DRONE ACUÁTICO
Servidor HTTP/WebSocket para control remoto del drone
"""

import asyncio
import json
import logging
import socket
import uuid
import re
from pathlib import Path
from aiohttp import WSMsgType, web

# Importar todas las funciones del módulo funciones
from funciones import (
    matar_procesos_servidor_previos,
    inicializar_gpio,
    controlar_rele,
    controlar_motor,
    liberar_gpio,
    obtener_ram,
    obtener_temperatura,
    obtener_cpu,
    obtener_almacenamiento,
    obtener_bateria,
    obtener_peso,
    obtener_solar,
    obtener_velocidad_red,
    obtener_wifi,
    obtener_voltaje_raspberry,
    obtener_io_sd,
    obtener_uso_disco_porcentaje,
    
    
    iniciar_gps,
    detener_gps,
    obtener_posicion_gps,
    guardar_posicion_gps,
    apagar_sistema,
    reiniciar_sistema
)
import funciones  # Importar módulo para acceder a ESTADO_RELES

# Importar funciones de base de datos
from base_de_datos.base_datos import (
    inicializar_bd,
    obtener_configuracion,
    guardar_configuracion,
    obtener_estado_reles,
    guardar_estado_rele,
    restaurar_estados_reles,
    iniciar_recorrido,
    guardar_posicion_gps as guardar_posicion_bd,
    obtener_todos_recorridos,
    obtener_recorrido,
    obtener_ubicaciones,
    guardar_velocidad_actual,
    obtener_velocidad_actual,
    guardar_destino,
    obtener_destino
)

from camera_stream import (
    asegurar_carpetas as hls_asegurar,
    construir_rtsp_url,
    construir_rtsp_candidatos,
    iniciar_hls,
    detener_todos as hls_detener_todos,
    detener_hls
)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN DEL SERVIDOR ====================

HOST = '0.0.0.0'
PUERTO = 8080
VELOCIDAD_ACTUAL = 50
CLIENTES_WS = set()
RECORRIDO_ACTIVO = None  # ID del recorrido GPS actual
TAREA_GUARDADO_GPS = None  # Tarea de guardado automático GPS

# Cache de datos del sistema para evitar múltiples subprocesses
DATOS_SISTEMA_CACHE = {
    'ram': None,
    'temperatura': None,
    'bateria': None,
    'peso': None,
    'solar': None,
    'gps': None,
    'ultima_actualizacion': 0
}


def descubrir_onvif(timeout=3):
    """Realiza un probe WS-Discovery para cámaras ONVIF en la red local.

    Devuelve una lista de diccionarios con host, puerto (estimado) y XAddrs.
    """
    multicast_group = ('239.255.255.250', 3702)
    message_id = f"uuid:{uuid.uuid4()}"
    probe = f"""
<?xml version='1.0' encoding='UTF-8'?>
<e:Envelope xmlns:e='http://www.w3.org/2003/05/soap-envelope'
            xmlns:w='http://schemas.xmlsoap.org/ws/2004/08/addressing'
            xmlns:d='http://schemas.xmlsoap.org/ws/2005/04/discovery'
            xmlns:dn='http://www.onvif.org/ver10/network/wsdl'>
  <e:Header>
    <w:MessageID>{message_id}</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>
""".strip().encode('utf-8')

    dispositivos = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.settimeout(timeout)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ttl = 1
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        sock.sendto(probe, multicast_group)

        while True:
            try:
                data, addr = sock.recvfrom(8192)
            except socket.timeout:
                break
            except Exception:
                break

            host = addr[0]
            txt = data.decode(errors='ignore')
            # Buscar XAddrs
            m = re.search(r"<.*?XAddrs.*?>([^<]+)<", txt)
            xaddrs = m.group(1).strip() if m else ''
            # Inferir puerto desde XAddrs si aparece, si no usar 8899
            puerto = 8899
            m2 = re.search(r"://[^:/]+:(\d+)", xaddrs)
            if m2:
                puerto = int(m2.group(1))

            dispositivos[host] = {
                'host': host,
                'puerto': puerto,
                'xaddrs': xaddrs,
            }
    finally:
        try:
            sock.close()
        except Exception:
            pass

    return list(dispositivos.values())


def obtener_payload_gps():
    """Devuelve datos GPS o un marcador de ausencia de señal."""
    gps = obtener_posicion_gps()
    if gps:
        gps['valido'] = True
        return gps
    return {'valido': False}

# ==================== FUNCIONES WEBSOCKET ====================

async def enviar_datos_periodicos():
    """
    Envía datos del sistema (RAM, temperatura, batería, GPS) 
    a todos los clientes conectados cada 5 segundos.
    
    OPTIMIZACIÓN: Calcula datos UNA sola vez por ciclo,
    evitando múltiples subprocesses costosos.
    """
    # Esperar 3 segundos antes de empezar
    await asyncio.sleep(3)
    
    while True:
        await asyncio.sleep(5)
        
        if not CLIENTES_WS:
            continue
        
        try:
            # Obtener datos del sistema UNA SOLA VEZ
            # (ejecutor previene bloqueo del event loop)
            loop = asyncio.get_event_loop()
            
            ram = await loop.run_in_executor(None, obtener_ram)
            temp = await loop.run_in_executor(None, obtener_temperatura)
            cpu = await loop.run_in_executor(None, obtener_cpu)
            almacenamiento = await loop.run_in_executor(None, obtener_almacenamiento)
            disco_uso = await loop.run_in_executor(None, obtener_uso_disco_porcentaje)
            bat = await loop.run_in_executor(None, obtener_bateria)
            peso = await loop.run_in_executor(None, obtener_peso)
            solar = await loop.run_in_executor(None, obtener_solar)
            wifi = await loop.run_in_executor(None, obtener_wifi)
            gps = obtener_payload_gps()
            voltaje = await loop.run_in_executor(None, obtener_voltaje_raspberry)
            
            # Crear mensajes
            mensaje_ram = {'tipo': 'ram', 'datos': ram}
            mensaje_temp = {'tipo': 'temperatura', 'datos': temp}
            mensaje_cpu = {'tipo': 'cpu', 'datos': cpu}
            mensaje_almacenamiento = {'tipo': 'almacenamiento', 'datos': almacenamiento}
            mensaje_disco = {'tipo': 'disco_uso', 'datos': disco_uso}
            mensaje_bat = {'tipo': 'bateria', 'datos': bat}
            mensaje_peso = {'tipo': 'peso', 'datos': peso}
            mensaje_solar = {'tipo': 'solar', 'datos': solar}
            mensaje_wifi = {'tipo': 'wifi', 'datos': wifi}
            mensaje_voltaje = {'tipo': 'voltaje', 'datos': voltaje}
            
            # Enviar a todos los clientes (mismo dato a todos = eficiente)
            desconectados = []
            for cliente in list(CLIENTES_WS):
                try:
                    await cliente.send_json(mensaje_ram)
                    await cliente.send_json(mensaje_temp)
                    await cliente.send_json(mensaje_cpu)
                    await cliente.send_json(mensaje_almacenamiento)
                    await cliente.send_json(mensaje_disco)
                    await cliente.send_json(mensaje_bat)
                    await cliente.send_json(mensaje_peso)
                    await cliente.send_json(mensaje_solar)
                    await cliente.send_json(mensaje_wifi)
                    await cliente.send_json(mensaje_voltaje)
                    # Enviar GPS siempre (con bandera de válido)
                    await cliente.send_json({'tipo': 'gps', 'datos': gps})
                except Exception as e:
                    logger.debug(f"Error enviando datos a cliente: {e}")
                    desconectados.append(cliente)
            
            # Limpiar clientes desconectados
            for cliente in desconectados:
                CLIENTES_WS.discard(cliente)
        
        except Exception as e:
            logger.error(f"Error en enviar_datos_periodicos: {e}")


async def enviar_velocidad_red_periodica():
    """
    Envía la velocidad de conexión a internet a todos los clientes
    conectados cada 30 segundos (menos frecuente que otros datos).
    """
    # Esperar 5 segundos antes de empezar
    await asyncio.sleep(5)
    
    while True:
        await asyncio.sleep(30)
        
        if not CLIENTES_WS:
            continue
        
        try:
            # Ejecutar en un executor para no bloquear el event loop
            velocidad_red = await asyncio.get_event_loop().run_in_executor(
                None, obtener_velocidad_red
            )
            mensaje = {'tipo': 'velocidad_red', 'datos': velocidad_red}
            
            # Enviar a todos los clientes
            for cliente in list(CLIENTES_WS):
                try:
                    await cliente.send_json(mensaje)
                except Exception as e:
                    logger.debug(f"Error enviando velocidad de red a cliente: {e}")
        
        except Exception as e:
            logger.error(f"Error en enviar_velocidad_red_periodica: {e}")


async def guardar_gps_automatico():
    """
    Guarda la posición GPS automáticamente según la configuración.
    Se ejecuta en segundo plano cuando está activado.
    """
    global RECORRIDO_ACTIVO
    
    while True:
        try:
            # Obtener configuración actual
            loop = asyncio.get_event_loop()
            config = await loop.run_in_executor(None, obtener_configuracion) or {}
            
            # Verificar si el guardado automático está activado
            if not config.get('guardar_recorrido', False):
                await asyncio.sleep(5)  # Verificar cada 5 segundos si se activó
                continue
            
            # Obtener frecuencia de guardado (por defecto 30 segundos)
            frecuencia = config.get('frecuencia_guardado', 30)
            if frecuencia < 5:
                frecuencia = 5  # Mínimo 5 segundos
            
            # Crear recorrido si no existe
            if RECORRIDO_ACTIVO is None:
                RECORRIDO_ACTIVO = iniciar_recorrido()
                logger.info(f"Recorrido GPS automático iniciado: ID {RECORRIDO_ACTIVO}")
            
            # Guardar posición actual
            exito, mensaje = guardar_posicion_gps(RECORRIDO_ACTIVO)
            if exito:
                logger.debug(f"GPS guardado automáticamente: {mensaje}")
            
            # Esperar según la frecuencia configurada
            await asyncio.sleep(frecuencia)
        
        except Exception as e:
            logger.error(f"Error en guardado automático GPS: {e}")
            await asyncio.sleep(30)  # Esperar más tiempo si hay error


async def websocket_handler(request):
    """
    Manejador de conexiones WebSocket.
    Recibe comandos y envía respuestas en tiempo real.
    
    MEJORA: Heartbeat de 30s óptimo para conexión por cable Ethernet
    """
    global VELOCIDAD_ACTUAL
    
    # Crear conexión WebSocket con heartbeat de 30 segundos y timeout aumentado
    # Para conexión por cable: heartbeat 30s es suficiente y reduce overhead
    ws = web.WebSocketResponse(heartbeat=30, timeout=60)
    await ws.prepare(request)
    CLIENTES_WS.add(ws)
    
    # Enviar mensaje inicial con estado completo (sin bloquear)
    try:
        loop = asyncio.get_event_loop()
        config_inicial = await loop.run_in_executor(None, obtener_configuracion) or {}
        destino_inicial = await loop.run_in_executor(None, obtener_destino)
        reles_desde_bd = await loop.run_in_executor(None, obtener_estado_reles) or {}
        # Asegurar que las claves de relés sean enteros
        reles_normalizados = {int(k) if isinstance(k, str) else k: v for k, v in reles_desde_bd.items()}
        
        await ws.send_json({
            'tipo': 'conexion',
            'mensaje': 'WebSocket conectado',
            'reles': reles_normalizados,
            'nombres_reles': config_inicial.get('reles', {}),
            'velocidad': VELOCIDAD_ACTUAL,
            'ram': obtener_ram(),
            'temperatura': obtener_temperatura(),
            'bateria': obtener_bateria(),
            'peso': obtener_peso(),
            'solar': obtener_solar(),
            'gps': obtener_payload_gps(),
            'destino': destino_inicial
        })
    except Exception as e:
        logger.error(f"Error en mensaje inicial WebSocket: {e}")
    
    logger.info(f"Cliente WebSocket conectado: {request.remote}")
    
    try:
        # Escuchar mensajes del cliente
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    datos = json.loads(msg.data)
                    await procesar_mensaje_ws(ws, datos)
                
                except json.JSONDecodeError:
                    await ws.send_json({
                        'tipo': 'error',
                        'mensaje': 'JSON inválido'
                    })
                
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    await ws.send_json({
                        'tipo': 'error',
                        'mensaje': str(e)
                    })
            
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"Error en WebSocket: {ws.exception()}")
    
    finally:
        CLIENTES_WS.discard(ws)
        await ws.close()
        logger.info("Cliente WebSocket desconectado")
    
    return ws


async def procesar_mensaje_ws(ws, datos):
    """
    Procesa los mensajes recibidos por WebSocket.
    
    Args:
        ws: Conexión WebSocket
        datos: Datos JSON recibidos
    """
    global VELOCIDAD_ACTUAL, RECORRIDO_ACTIVO
    
    tipo = datos.get('tipo')
    
    # Control de relés
    if tipo == 'rele':
        numero = int(datos.get('numero', 0))
        estado = bool(datos.get('estado', False))
        logger.info(f"Comando de relé recibido: número={numero}, estado={estado}")
        exito, error = controlar_rele(numero, estado)
        logger.info(f"Resultado de controlar_rele: exito={exito}, error={error}")
        
        await ws.send_json({
            'tipo': 'respuesta_rele',
            'numero': numero,
            'estado': 'on' if estado else 'off',
            'exito': exito,
            'error': error
        })

        # Notificar a todos los clientes el estado actualizado de los relés
        try:
            reles_bd = obtener_estado_reles() or {}
            # Asegurar que las claves sean enteros
            reles_normalizados = {int(k) if isinstance(k, str) else k: v for k, v in reles_bd.items()}
            for cliente in list(CLIENTES_WS):
                try:
                    await cliente.send_json({'tipo': 'reles', 'reles': reles_normalizados})
                except Exception:
                    pass
        except Exception:
            pass
    
    # Control de motores
    elif tipo == 'motor':
        direccion = datos.get('direccion', 'parar')
        exito, error = controlar_motor(direccion, VELOCIDAD_ACTUAL)
        
        await ws.send_json({
            'tipo': 'respuesta_motor',
            'direccion': direccion,
            'exito': exito,
            'error': error
        })
    
    # Cambio de velocidad
    elif tipo == 'velocidad':
        VELOCIDAD_ACTUAL = int(datos.get('nivel', 50))
        guardar_velocidad_actual(VELOCIDAD_ACTUAL)

        await ws.send_json({
            'tipo': 'respuesta_velocidad',
            'velocidad': VELOCIDAD_ACTUAL,
            'exito': True
        })
        # Broadcast a todos los clientes el nivel actualizado
        for cliente in list(CLIENTES_WS):
            try:
                await cliente.send_json({'tipo': 'velocidad', 'velocidad': VELOCIDAD_ACTUAL})
            except Exception:
                pass
    
    # Comandos de sistema
    elif tipo == 'sistema':
        comando = datos.get('comando')
        
        if comando == 'apagar':
            exito, mensaje = apagar_sistema()
            await ws.send_json({
                'tipo': 'sistema',
                'comando': 'apagar',
                'mensaje': mensaje
            })
        
        elif comando == 'reiniciar':
            exito, mensaje = reiniciar_sistema()
            await ws.send_json({
                'tipo': 'sistema',
                'comando': 'reiniciar',
                'mensaje': mensaje
            })
    
    # Comandos GPS
    elif tipo == 'gps_guardar':
        exito, mensaje = guardar_posicion_gps(RECORRIDO_ACTIVO)
        await ws.send_json({
            'tipo': 'respuesta_gps',
            'accion': 'guardar',
            'exito': exito,
            'mensaje': mensaje
        })

    elif tipo == 'gps_destino':
        try:
            lat = float(datos.get('latitud'))
            lon = float(datos.get('longitud'))
            nombre = datos.get('nombre')
            ok = guardar_destino(lat, lon, nombre)
            respuesta = {
                'tipo': 'destino_actual',
                'exito': bool(ok),
                'latitud': lat,
                'longitud': lon,
                'nombre': nombre
            }
            await ws.send_json(respuesta)
            # Notificar a todos los clientes conectados
            if ok:
                for cliente in list(CLIENTES_WS):
                    try:
                        await cliente.send_json(respuesta)
                    except Exception:
                        pass
        except Exception as e:
            await ws.send_json({
                'tipo': 'destino_actual',
                'exito': False,
                'mensaje': f'Coordenadas inválidas: {e}'
            })

    # Control de cámaras (RTSP→HLS)
    elif tipo == 'camara':
        indice = int(datos.get('indice', 1))
        accion = datos.get('accion', 'iniciar')
        cam_id = 'cam1' if indice == 1 else 'cam2'
        loop = asyncio.get_event_loop()
        config = await loop.run_in_executor(None, obtener_configuracion) or {}
        if accion == 'iniciar':
            candidatos = construir_rtsp_candidatos(config, indice)
            rtsp = candidatos[0] if candidatos else None
            # Obtener velocidad de red para modo automático
            velocidad_datos = await loop.run_in_executor(None, obtener_velocidad_red)
            velocidad = velocidad_datos.get('velocidad', None) if velocidad_datos else None
            exito, mensaje = iniciar_hls(cam_id, candidatos, config, velocidad)
            await ws.send_json({
                'tipo': 'camara',
                'indice': indice,
                'accion': 'iniciar',
                'exito': exito,
                'rtsp': rtsp,
                'mensaje': mensaje
            })
        elif accion == 'detener':
            detener_hls(cam_id)
            await ws.send_json({
                'tipo': 'camara',
                'indice': indice,
                'accion': 'detener',
                'exito': True
            })
    
    # Solicitar datos actuales
    elif tipo == 'obtener_datos':
        from base_de_datos.base_datos import obtener_estado_reles
        reles_datos = obtener_estado_reles() or {}
        reles_normalizados = {int(k) if isinstance(k, str) else k: v for k, v in reles_datos.items()}
        await ws.send_json({'tipo': 'reles', 'reles': reles_normalizados})
        await ws.send_json({'tipo': 'ram', 'datos': obtener_ram()})
        await ws.send_json({'tipo': 'temperatura', 'datos': obtener_temperatura()})
        await ws.send_json({'tipo': 'cpu', 'datos': obtener_cpu()})
        await ws.send_json({'tipo': 'almacenamiento', 'datos': obtener_almacenamiento()})
        await ws.send_json({'tipo': 'disco_uso', 'datos': obtener_uso_disco_porcentaje()})
        await ws.send_json({'tipo': 'bateria', 'datos': obtener_bateria()})
        await ws.send_json({'tipo': 'peso', 'datos': obtener_peso()})
        await ws.send_json({'tipo': 'solar', 'datos': obtener_solar()})
        await ws.send_json({'tipo': 'gps', 'datos': obtener_payload_gps()})
        await ws.send_json({'tipo': 'velocidad', 'velocidad': VELOCIDAD_ACTUAL})
    
    # Guardar configuración
    elif tipo == 'guardar_config':
        config = datos.get('config', {})
        if guardar_configuracion(config):
            await ws.send_json({
                'tipo': 'config_guardada',
                'exito': True,
                'mensaje': 'Configuración guardada en la base de datos'
            })
        else:
            await ws.send_json({
                'tipo': 'config_guardada',
                'exito': False,
                'mensaje': 'Error al guardar configuración'
            })
    
    # Obtener configuración
    elif tipo == 'obtener_config':
        loop = asyncio.get_event_loop()
        config = await loop.run_in_executor(None, obtener_configuracion)
        await ws.send_json({
            'tipo': 'config_actual',
            'datos': config if config else {}
        })
    
    # Iniciar grabación de recorrido GPS
    elif tipo == 'iniciar_recorrido':
        nombre = datos.get('nombre', 'Recorrido sin título')
        RECORRIDO_ACTIVO = iniciar_recorrido(nombre)
        
        await ws.send_json({
            'tipo': 'recorrido_iniciado',
            'recorrido_id': RECORRIDO_ACTIVO,
            'nombre': nombre
        })
    
    # Finalizar grabación de recorrido GPS
    elif tipo == 'finalizar_recorrido':
        if RECORRIDO_ACTIVO:
            from base_de_datos.base_datos import finalizar_recorrido
            finalizar_recorrido(RECORRIDO_ACTIVO)
            RECORRIDO_ACTIVO = None
            
            await ws.send_json({
                'tipo': 'recorrido_finalizado',
                'exito': True
            })
        else:
            await ws.send_json({
                'tipo': 'recorrido_finalizado',
                'exito': False,
                'mensaje': 'No hay recorrido activo'
            })
    
    # Obtener lista de recorridos
    elif tipo == 'obtener_recorridos':
        recorridos = obtener_todos_recorridos()
        await ws.send_json({
            'tipo': 'lista_recorridos',
            'recorridos': recorridos
        })
    
    # Comando desconocido
    else:
        await ws.send_json({
            'tipo': 'error',
            'mensaje': f'Comando "{tipo}" no reconocido'
        })


# ==================== MANEJADORES HTTP ====================

async def index_handler(request):
    """
    Manejador para la página principal.
    Sirve únicamente 'control remoto digital.html'.
    """
    archivo = Path(__file__).parent / 'paginas' / 'control remoto digital.html'
    if not archivo.exists():
        return web.json_response({'error': 'Página no encontrada'}, status=404)
    return web.FileResponse(archivo)

async def configuracion_handler(request):
    """Manejador de la página de configuración."""
    archivo = Path(__file__).parent / 'paginas' / 'configuracion.html'
    if not archivo.exists():
        return web.json_response({'error': 'Página de configuración no encontrada'}, status=404)
    return web.FileResponse(archivo)


async def mapa_gps_handler(request):
    """Manejador de la página de mapa GPS (ubicaciones y recorridos)."""
    archivo = Path(__file__).parent / 'paginas' / 'mapa_gps.html'
    if not archivo.exists():
        return web.json_response({'error': 'Página de mapa no encontrada'}, status=404)
    return web.FileResponse(archivo)


async def energia_solar_handler(request):
    """Manejador de la página de energía solar."""
    archivo = Path(__file__).parent / 'paginas' / 'energia_solar.html'
    if not archivo.exists():
        return web.json_response({'error': 'Página de energía solar no encontrada'}, status=404)
    return web.FileResponse(archivo)


async def api_config_handler(request):
    """
    API REST para obtener y guardar configuración.
    GET: Obtiene la configuración actual
    POST: Guarda la configuración
    """
    if request.method == 'GET':
        loop = asyncio.get_event_loop()
        config = await loop.run_in_executor(None, obtener_configuracion)
        if config:
            return web.json_response(config)
        else:
            return web.json_response({'error': 'No hay configuración'}, status=404)
    
    elif request.method == 'POST':
        try:
            datos = await request.json()
            if guardar_configuracion(datos):
                # Notificar a todos los clientes conectados que la configuración fue actualizada
                mensaje = {
                    'tipo': 'config_actualizada',
                    'mensaje': 'Nombres de relés actualizados'
                }
                for cliente in CLIENTES_WS:
                    try:
                        await cliente.send_json(mensaje)
                    except Exception as e:
                        logger.warning(f"Error notificando cliente: {e}")
                
                return web.json_response({
                    'exito': True,
                    'mensaje': 'Configuración guardada correctamente'
                })
            else:
                return web.json_response({
                    'exito': False,
                    'mensaje': 'Error al guardar configuración'
                }, status=500)
        except Exception as e:
            logger.error(f"Error en API de configuración: {e}")
            return web.json_response({
                'exito': False,
                'error': str(e)
            }, status=400)

async def api_onvif_discover_handler(request):
    loop = asyncio.get_event_loop()
    dispositivos = await loop.run_in_executor(None, descubrir_onvif)
    return web.json_response({'exito': True, 'dispositivos': dispositivos})


async def api_reiniciar_handler(request):
    """
    API REST para reiniciar el sistema.
    POST: Reinicia la Raspberry Pi
    """
    try:
        logger.info("Solicitud de reinicio recibida")
        # Ejecutar el reinicio en un executor para no bloquear
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, reiniciar_sistema)
        return web.json_response({
            'exito': True,
            'mensaje': 'Sistema reiniciándose...'
        })
    except Exception as e:
        logger.error(f"Error al reiniciar sistema: {e}")
        return web.json_response({
            'exito': False,
            'error': str(e)
        }, status=500)


async def api_apagar_handler(request):
    """
    API REST para apagar el sistema.
    POST: Apaga la Raspberry Pi
    """
    try:
        logger.info("Solicitud de apagado recibida")
        # Ejecutar el apagado en un executor para no bloquear
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, apagar_sistema)
        return web.json_response({
            'exito': True,
            'mensaje': 'Sistema apagándose...'
        })
    except Exception as e:
        logger.error(f"Error al apagar sistema: {e}")
        return web.json_response({
            'exito': False,
            'error': str(e)
        }, status=500)


async def api_ubicaciones_handler(request):
    """GET: Devuelve ubicaciones guardadas. POST: Guarda una nueva ubicación."""
    if request.method == 'GET':
        try:
            busqueda = request.query.get('q') or request.query.get('busqueda') or ''
            categoria = request.query.get('categoria', '')
            ubicaciones = obtener_ubicaciones(categoria, busqueda)
            return web.json_response({
                'exito': True,
                'ubicaciones': ubicaciones
            })
        except Exception as e:
            logger.error(f"Error obteniendo ubicaciones: {e}")
            return web.json_response({
                'exito': False,
                'error': str(e)
            }, status=500)
    elif request.method == 'POST':
        try:
            datos = await request.json()
            nombre = datos.get('nombre') or ''
            descripcion = datos.get('descripcion') or ''
            latitud = datos.get('latitud')
            longitud = datos.get('longitud')
            if not (isinstance(latitud, (float, int)) and isinstance(longitud, (float, int))):
                return web.json_response({'exito': False, 'error': 'Latitud y longitud requeridas'}, status=400)
            from base_de_datos.base_datos import guardar_ubicacion
            ubic_id = guardar_ubicacion(nombre, descripcion, latitud, longitud)
            if ubic_id:
                return web.json_response({'exito': True, 'id': ubic_id})
            else:
                return web.json_response({'exito': False, 'error': 'No se pudo guardar la ubicación'}, status=500)
        except Exception as e:
            logger.error(f"Error guardando ubicación: {e}")
            return web.json_response({'exito': False, 'error': str(e)}, status=500)
    else:
        return web.json_response({'exito': False, 'error': 'Método no permitido'}, status=405)


async def api_gps_actual_handler(request):
    """API REST para obtener la posición GPS actual."""
    try:
        gps = obtener_posicion_gps()
        if gps:
            return web.json_response({
                'exito': True,
                'datos': {
                    'latitud': gps.get('latitud'),
                    'longitud': gps.get('longitud'),
                    'altitud': gps.get('altitud'),
                    'velocidad': gps.get('velocidad'),
                    'rumbo': gps.get('rumbo'),
                    'satelites': gps.get('satelites'),
                    'precision': gps.get('precision'),
                    'valido': gps.get('valido', False)
                }
            })
        else:
            return web.json_response({
                'exito': False,
                'error': 'No hay datos GPS disponibles'
            }, status=404)
    except Exception as e:
        logger.error(f"Error obteniendo GPS actual: {e}")
        return web.json_response({
            'exito': False,
            'error': str(e)
        }, status=500)
    categoria = request.query.get('categoria') or None
    busqueda = request.query.get('q') or request.query.get('busqueda') or None
    loop = asyncio.get_event_loop()
    ubicaciones = await loop.run_in_executor(None, lambda: obtener_ubicaciones(categoria, busqueda))
    return web.json_response({'exito': True, 'ubicaciones': ubicaciones})


async def api_recorridos_handler(request):
    """Lista los recorridos GPS (opcionalmente solo activos)."""
    activos_flag = (request.query.get('activos') or '').lower() in ('1', 'true', 'si', 'sí', 'yes')
    loop = asyncio.get_event_loop()
    recorridos = await loop.run_in_executor(None, lambda: obtener_todos_recorridos(activos_flag))
    return web.json_response({'exito': True, 'recorridos': recorridos})


async def api_recorrido_detalle_handler(request):
    """Devuelve un recorrido con todas sus posiciones."""
    try:
        recorrido_id = int(request.match_info.get('recorrido_id', '0'))
    except ValueError:
        return web.json_response({'exito': False, 'error': 'ID de recorrido inválido'}, status=400)

    loop = asyncio.get_event_loop()
    detalle = await loop.run_in_executor(None, lambda: obtener_recorrido(recorrido_id))
    if not detalle:
        return web.json_response({'exito': False, 'error': 'Recorrido no encontrado'}, status=404)
    return web.json_response({'exito': True, 'recorrido': detalle})


async def api_test_wifi_handler(request):
    """Endpoint de prueba para obtener información del WiFi."""
    try:
        loop = asyncio.get_event_loop()
        wifi_data = await loop.run_in_executor(None, obtener_wifi)
        logger.info(f"Datos WiFi obtenidos: {wifi_data}")
        return web.json_response({
            'exito': True,
            'datos': wifi_data
        })
    except Exception as e:
        logger.error(f"Error obteniendo WiFi: {e}")
        return web.json_response({
            'exito': False,
            'error': str(e)
        }, status=500)


# ==================== EVENTOS DEL SERVIDOR ====================

async def on_startup(app):
    """Se ejecuta al iniciar el servidor."""
    # Inicializar base de datos
    inicializar_bd()
    logger.info("Base de datos inicializada")
    
    # Cargar configuración desde BD
    loop = asyncio.get_event_loop()
    config = await loop.run_in_executor(None, obtener_configuracion)
    if config:
        logger.info(f"Configuración cargada: IP={config['ip_publica']}, Tamaño mapa={config['tamano_mapa']}px")
        # Cargar velocidad almacenada
        global VELOCIDAD_ACTUAL
        VELOCIDAD_ACTUAL = config.get('velocidad_actual', VELOCIDAD_ACTUAL)
        # Preparar carpeta HLS y arrancar cámaras si están configuradas
        hls_asegurar()

        # Iniciar cámara 1 si está habilitada y con auto-start
        if not config.get('desactivar_camara1', False) and config.get('iniciar_auto_camara1', True):
            candidatos1 = construir_rtsp_candidatos(config, 1)
            if candidatos1:
                # Iniciar con velocidad None (modo automático usará valor por defecto)
                # La velocidad real se detectará cuando se reinicie la cámara
                exito, msg = iniciar_hls('cam1', candidatos1, config, None)
                if exito:
                    logger.info(f"✓ Cámara 1 iniciada (ONVIF): {candidatos1[0]}")
                else:
                    logger.warning(f"⚠ No se pudo iniciar cámara 1 (ONVIF): {msg}")

        # Iniciar cámara 2 si está habilitada y con auto-start
        if not config.get('desactivar_camara2', False) and config.get('iniciar_auto_camara2', True):
            candidatos2 = construir_rtsp_candidatos(config, 2)
            if candidatos2:
                # Iniciar con velocidad None (modo automático usará valor por defecto)
                # La velocidad real se detectará cuando se reinicie la cámara
                exito, msg = iniciar_hls('cam2', candidatos2, config, None)
                if exito:
                    logger.info(f"✓ Cámara 2 iniciada (ONVIF): {candidatos2[0]}")
                else:
                    logger.warning(f"⚠ No se pudo iniciar cámara 2 (ONVIF): {msg}")
    
    # Cargar estado de relés desde BD
    estados_bd = obtener_estado_reles()
    if estados_bd:
        funciones.ESTADO_RELES.update({k: v for k, v in estados_bd.items()})
        logger.info("Estado de relés cargado desde BD")
    
    # Iniciar tarea de envío periódico de datos
    app['datos_task'] = asyncio.create_task(enviar_datos_periodicos())
    app['velocidad_red_task'] = asyncio.create_task(enviar_velocidad_red_periodica())
    app['gps_auto_task'] = asyncio.create_task(guardar_gps_automatico())
    logger.info("Tareas de envío periódico y guardado GPS automático iniciadas")


async def on_shutdown(app):
    """Se ejecuta al cerrar el servidor."""
    global RECORRIDO_ACTIVO
    
    # Cancelar tareas periódicas
    if 'datos_task' in app:
        app['datos_task'].cancel()
    if 'velocidad_red_task' in app:
        app['velocidad_red_task'].cancel()
    if 'gps_auto_task' in app:
        app['gps_auto_task'].cancel()
    
    # Finalizar recorrido GPS activo si existe
    if RECORRIDO_ACTIVO:
        from base_de_datos.base_datos import finalizar_recorrido
        finalizar_recorrido(RECORRIDO_ACTIVO)
        logger.info(f"Recorrido GPS finalizado: ID={RECORRIDO_ACTIVO}")
    
    # Detener GPS
    detener_gps()
    
    # Liberar GPIO
    liberar_gpio()
    
    # Detener pipelines de cámaras
    hls_detener_todos()
    
    logger.info("Servidor detenido correctamente")


# ==================== APLICACIÓN ====================

def crear_app():
    """
    Crea y configura la aplicación web.
    
    Returns:
        web.Application: Aplicación aiohttp configurada
    """
    app = web.Application()
    
    # Rutas HTTP
    app.router.add_get('/', index_handler)
    app.router.add_get('/configuracion.html', configuracion_handler)
    app.router.add_get('/mapa_gps.html', mapa_gps_handler)
    app.router.add_get('/energia_solar.html', energia_solar_handler)
    app.router.add_get('/api/config', api_config_handler)
    app.router.add_post('/api/config', api_config_handler)
    app.router.add_get('/api/gps/actual', api_gps_actual_handler)
    app.router.add_get('/api/test/wifi', api_test_wifi_handler)
    app.router.add_get('/api/onvif/discover', api_onvif_discover_handler)
    app.router.add_route('*', '/api/ubicaciones', api_ubicaciones_handler)
    app.router.add_get('/api/recorridos', api_recorridos_handler)
    app.router.add_get('/api/recorridos/{recorrido_id}', api_recorrido_detalle_handler)
    app.router.add_get('/ws', websocket_handler)
    # Endpoints para apagar y reiniciar el sistema
    app.router.add_post('/api/reiniciar', api_reiniciar_handler)
    app.router.add_post('/api/apagar', api_apagar_handler)
    
    # Archivos estáticos (CSS, JS, imágenes)
    app.router.add_static(
        '/static',
        Path(__file__).parent / 'paginas',
        name='static'
    )

    # Carpeta HLS para reproducir cámaras (RTSP → HLS)
    hls_dir = Path(__file__).parent / 'hls'
    hls_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static(
        '/hls',
        hls_dir,
        name='hls'
    )
    
    # Eventos
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app


def configurar_keepalive(app):
    """Configura TCP keepalive para mantener conexiones estables por cable."""
    try:
        import socket
        # El servidor aiohttp ya maneja keepalive, pero podemos ajustar parámetros
        # mediante las opciones de TCPSite que usa web.run_app internamente
        logger.info("✓ TCP keepalive habilitado automáticamente por aiohttp")
    except Exception as e:
        logger.warning(f"No se pudo configurar keepalive: {e}")


# ==================== PUNTO DE ENTRADA ====================

def main():
    """Función principal que inicia el servidor."""
    logger.info("=" * 60)
    logger.info("  SERVIDOR DRONE ACUÁTICO - CONTROL REMOTO WEB")
    logger.info("=" * 60)
    logger.info(f"Iniciando en http://192.168.1.7:{PUERTO}")
    logger.info("=" * 60)
    
    # Terminar procesos previos del servidor
    matar_procesos_servidor_previos()
    
    # Inicializar base de datos
    inicializar_bd()

    # Cargar velocidad almacenada
    global VELOCIDAD_ACTUAL
    VELOCIDAD_ACTUAL = obtener_velocidad_actual()
    
    # Inicializar hardware
    inicializar_gpio()
    
    # Restaurar estados de relés desde la base de datos
    logger.info("Restaurando estados de relés desde base de datos...")
    estados_guardados = restaurar_estados_reles()
    import time
    for numero, estado in estados_guardados.items():
        if estado:  # Solo activar los que estaban prendidos
            exito, error = controlar_rele(numero, True)
            if exito:
                logger.info(f"✓ Relé {numero} activado (restaurado desde BD)")
            else:
                logger.warning(f"⚠ No se pudo activar relé {numero}: {error}")
            # Delay de 1 segundo entre cada relé para arranque secuencial
            time.sleep(1)
    
    iniciar_gps()
    
    
    
    # Crear y ejecutar aplicación
    app = crear_app()
    
    # Configuración optimizada para conexión Ethernet (cable)
    # keepalive_timeout: 75s mantiene conexiones idle activas
    # access_log: None reduce I/O y mejora performance
    # print=None evita que VS Code abra navegador automáticamente
    web.run_app(
        app, 
        host=HOST, 
        port=PUERTO,
        keepalive_timeout=75,  # Mantener conexiones TCP vivas
        access_log=None,  # Desactivar logs HTTP para mejor performance
        print=None  # No imprimir URL (evita apertura automática en VS Code)
    )


if __name__ == '__main__':
    main()
