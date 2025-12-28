#!/usr/bin/env python3
"""
SERVIDOR WEB DEL DRONE ACUÁTICO
Servidor HTTP/WebSocket para control remoto del drone
"""

import asyncio
import json
import logging
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
    obtener_bateria,
    obtener_peso,
    obtener_solar,
    obtener_velocidad_red,
    iniciar_gps,
    detener_gps,
    obtener_posicion_gps,
    guardar_posicion_gps,
    apagar_sistema,
    reiniciar_sistema,
    ESTADO_RELES
)

# Importar funciones de base de datos
from base_datos import (
    inicializar_bd,
    obtener_configuracion,
    guardar_configuracion,
    obtener_estado_reles,
    guardar_estado_rele,
    restaurar_estados_reles,
    iniciar_recorrido,
    guardar_posicion_gps as guardar_posicion_bd,
    obtener_todos_recorridos,
    obtener_tema,
    guardar_tema
)
from camera_stream import (
    asegurar_carpetas as hls_asegurar,
    construir_rtsp_url,
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
            bat = await loop.run_in_executor(None, obtener_bateria)
            peso = await loop.run_in_executor(None, obtener_peso)
            solar = await loop.run_in_executor(None, obtener_solar)
            gps = obtener_payload_gps()
            
            # Crear mensajes
            mensaje_ram = {'tipo': 'ram', 'datos': ram}
            mensaje_temp = {'tipo': 'temperatura', 'datos': temp}
            mensaje_bat = {'tipo': 'bateria', 'datos': bat}
            mensaje_peso = {'tipo': 'peso', 'datos': peso}
            mensaje_solar = {'tipo': 'solar', 'datos': solar}
            
            # Enviar a todos los clientes (mismo dato a todos = eficiente)
            desconectados = []
            for cliente in list(CLIENTES_WS):
                try:
                    await cliente.send_json(mensaje_ram)
                    await cliente.send_json(mensaje_temp)
                    await cliente.send_json(mensaje_bat)
                    await cliente.send_json(mensaje_peso)
                    await cliente.send_json(mensaje_solar)
                    
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
                    logger.debug(f"Error enviando velocidad_red a cliente: {e}")
                    CLIENTES_WS.discard(cliente)
        
        except Exception as e:
            logger.error(f"Error obteniendo velocidad de red: {e}")


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
        
        await ws.send_json({
            'tipo': 'conexion',
            'mensaje': 'WebSocket conectado',
            'reles': ESTADO_RELES,
            'nombres_reles': config_inicial.get('reles', {}),
            'velocidad': VELOCIDAD_ACTUAL,
            'ram': obtener_ram(),
            'temperatura': obtener_temperatura(),
            'bateria': obtener_bateria(),
            'peso': obtener_peso(),
            'solar': obtener_solar(),
            'gps': obtener_payload_gps()
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
        exito, error = controlar_rele(numero, estado)
        
        # Guardar estado en base de datos para persistencia
        if exito:
            guardar_estado_rele(numero, 1 if estado else 0)
            logger.info(f"Estado del relé {numero} guardado en BD: {'ON' if estado else 'OFF'}")
        
        await ws.send_json({
            'tipo': 'respuesta_rele',
            'numero': numero,
            'estado': 'on' if estado else 'off',
            'exito': exito,
            'error': error
        })
    
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
        
        await ws.send_json({
            'tipo': 'respuesta_velocidad',
            'velocidad': VELOCIDAD_ACTUAL
        })
    
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

    # Control de cámaras (RTSP→HLS)
    elif tipo == 'camara':
        indice = int(datos.get('indice', 1))
        accion = datos.get('accion', 'iniciar')
        calidad = datos.get('calidad', 'sd')  # sd o hd
        cam_id = 'cam1' if indice == 1 else 'cam2'
        config = obtener_configuracion() or {}
        if accion == 'iniciar':
            rtsp = construir_rtsp_url(config, indice, calidad)
            exito, mensaje = iniciar_hls(cam_id, rtsp)
            await ws.send_json({
                'tipo': 'camara',
                'indice': indice,
                'accion': 'iniciar',
                'calidad': calidad,
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
        await ws.send_json({'tipo': 'ram', 'datos': obtener_ram()})
        await ws.send_json({'tipo': 'temperatura', 'datos': obtener_temperatura()})
        await ws.send_json({'tipo': 'bateria', 'datos': obtener_bateria()})
        await ws.send_json({'tipo': 'peso', 'datos': obtener_peso()})
        await ws.send_json({'tipo': 'solar', 'datos': obtener_solar()})
        await ws.send_json({'tipo': 'gps', 'datos': obtener_payload_gps()})
    
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
        config = obtener_configuracion()
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
            from base_datos import finalizar_recorrido
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


async def api_tema_get_handler(request):
    """Obtiene el tema guardado en la BD (sin bloquear el event loop)."""
    try:
        # Ejecutar operación de BD en executor para no bloquear
        loop = asyncio.get_event_loop()
        tema = await loop.run_in_executor(None, obtener_tema)
        return web.json_response({'tema': tema})
    except Exception as e:
        logger.error(f"Error obteniendo tema: {e}")
        return web.json_response({'tema': 'oscuro', 'error': str(e)}, status=500)


async def api_tema_post_handler(request):
    """Guarda el tema en la BD (sin bloquear el event loop)."""
    try:
        datos = await request.json()
        tema = datos.get('tema', 'oscuro')
        tema_oscuro = (tema == 'oscuro')
        
        # Ejecutar operación de BD en executor para no bloquear
        loop = asyncio.get_event_loop()
        exito = await asyncio.wait_for(
            loop.run_in_executor(None, guardar_tema, tema_oscuro),
            timeout=5.0  # Timeout de 5 segundos
        )
        
        if exito:
            logger.info(f"Tema cambiado a {tema} exitosamente")
            return web.json_response({'exito': True, 'tema': tema})
        else:
            return web.json_response({'exito': False, 'error': 'No se pudo guardar el tema'}, status=500)
    
    except asyncio.TimeoutError:
        logger.error("Timeout al guardar tema (5s)")
        return web.json_response({'exito': False, 'error': 'Timeout al guardar tema'}, status=504)
    except Exception as e:
        logger.error(f"Error guardando tema: {e}")
        return web.json_response({'exito': False, 'error': str(e)}, status=500)


async def api_config_handler(request):
    """
    API REST para obtener y guardar configuración.
    GET: Obtiene la configuración actual
    POST: Guarda la configuración
    """
    if request.method == 'GET':
        config = obtener_configuracion()
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


# ==================== EVENTOS DEL SERVIDOR ====================

async def on_startup(app):
    """Se ejecuta al iniciar el servidor."""
    # Inicializar base de datos
    inicializar_bd()
    logger.info("Base de datos inicializada")
    
    # Cargar configuración desde BD
    config = obtener_configuracion()
    if config:
        logger.info(f"Configuración cargada: IP={config['ip_publica']}, Tamaño mapa={config['tamano_mapa']}px")
        # Preparar carpeta HLS y arrancar cámaras si están configuradas
        hls_asegurar()
        rtsp1_hd = construir_rtsp_url(config, 1, 'hd')
        rtsp2_hd = construir_rtsp_url(config, 2, 'hd')
        iniciar_hls('cam1', rtsp1_hd)
        iniciar_hls('cam2', rtsp2_hd)
    
    # Cargar estado de relés desde BD
    estados_bd = obtener_estado_reles()
    if estados_bd:
        ESTADO_RELES.update({k: v for k, v in estados_bd.items()})
        logger.info("Estado de relés cargado desde BD")
    
    # Iniciar tarea de envío periódico de datos
    app['datos_task'] = asyncio.create_task(enviar_datos_periodicos())
    app['velocidad_red_task'] = asyncio.create_task(enviar_velocidad_red_periodica())
    logger.info("Tareas de envío periódico iniciadas")


async def on_shutdown(app):
    """Se ejecuta al cerrar el servidor."""
    global RECORRIDO_ACTIVO
    
    # Cancelar tareas periódicas
    if 'datos_task' in app:
        app['datos_task'].cancel()
    if 'velocidad_red_task' in app:
        app['velocidad_red_task'].cancel()
    
    # Finalizar recorrido GPS activo si existe
    if RECORRIDO_ACTIVO:
        from base_datos import finalizar_recorrido
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
    app.router.add_get('/api/config', api_config_handler)
    app.router.add_post('/api/config', api_config_handler)
    app.router.add_get('/api/tema', api_tema_get_handler)
    app.router.add_post('/api/tema', api_tema_post_handler)
    app.router.add_get('/ws', websocket_handler)
    
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
    
    # Inicializar hardware
    inicializar_gpio()
    
    # Restaurar estados de relés desde la base de datos
    logger.info("Restaurando estados de relés desde base de datos...")
    estados_guardados = restaurar_estados_reles()
    for numero, estado in estados_guardados.items():
        if estado:  # Solo activar los que estaban prendidos
            exito, error = controlar_rele(numero, True)
            if exito:
                logger.info(f"✓ Relé {numero} activado (restaurado desde BD)")
            else:
                logger.warning(f"⚠ No se pudo activar relé {numero}: {error}")
    
    iniciar_gps()
    
    # Crear y ejecutar aplicación
    app = crear_app()
    
    # Configuración optimizada para conexión Ethernet (cable)
    # keepalive_timeout: 75s mantiene conexiones idle activas
    # access_log: None reduce I/O y mejora performance
    web.run_app(
        app, 
        host=HOST, 
        port=PUERTO,
        keepalive_timeout=75,  # Mantener conexiones TCP vivas
        access_log=None  # Desactivar logs HTTP para mejor performance
    )


if __name__ == '__main__':
    main()
