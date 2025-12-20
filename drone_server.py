#!/usr/bin/env python3
"""
Servidor Web del Drone Acuático
Control remoto mediante WebSocket
Raspberry Pi 3 - Python 3
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from aiohttp import web
import aiohttp

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================
HOST = '0.0.0.0'  # Escuchar en todas las interfaces
PORT = 8080  # Puerto del servidor web
PESO_UMBRAL = 5.0  # Umbral de peso en kg para alertas

# ==================== VARIABLES GLOBALES ====================
websockets_conectados = set()  # Conjunto de WebSockets conectados
ubicaciones_gps = []  # Lista de ubicaciones GPS guardadas
ultima_lectura_peso = 0.0  # Última lectura del sensor de peso
GPIO_INSTANCE = None  # Instancia global de GPIO


# ==================== FUNCIONES DE HARDWARE ====================

def inicializar_gpio():
    """Inicializa los pines GPIO de la Raspberry Pi"""
    global GPIO_INSTANCE
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)  # Usar numeración BCM
        GPIO.setwarnings(False)  # Desactivar advertencias
        
        # Configurar pines de relés como salida (LOW = apagado inicialmente)
        reles = [4, 7, 8, 9, 11, 21, 22, 23, 24]
        for pin in reles:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = relé apagado (lógica inversa)
        
        # Configurar pines PWM para motores
        motores = [18, 13, 19, 12]
        for pin in motores:
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, 50)  # 50 Hz para ESC
            pwm.start(0)  # Iniciar en 0%
        
        logger.info("GPIO inicializado correctamente")
        GPIO_INSTANCE = GPIO
        return GPIO
    except Exception as e:
        logger.error(f"Error inicializando GPIO: {e}")
        return None


def controlar_rele(gpio, numero, estado):
    """
    Controla un relé específico
    numero: 1-9 (número del relé)
    estado: True (encender) o False (apagar)
    """
    pines_reles = {1: 4, 2: 7, 3: 8, 4: 9, 5: 11, 6: 21, 7: 22, 8: 23, 9: 24}
    
    if numero not in pines_reles:
        logger.error(f"Número de relé inválido: {numero}")
        return False
    
    try:
        pin = pines_reles[numero]
        # Lógica inversa: LOW = encendido, HIGH = apagado
        gpio.output(pin, gpio.LOW if estado else gpio.HIGH)
        logger.info(f"Relé {numero} {'encendido' if estado else 'apagado'}")
        return True
    except Exception as e:
        logger.error(f"Error controlando relé {numero}: {e}")
        return False


def controlar_motor(gpio, direccion):
    """
    Controla los motores según la dirección
    direccion: 'adelante', 'atras', 'derecha', 'izquierda', 'parar'
    """
    try:
        pines_motores = [18, 13, 19, 12]  # Motor 1, 2, 3, 4
        
        if direccion == 'adelante':
            # Todos los motores hacia adelante
            for pin in pines_motores:
                gpio.output(pin, gpio.HIGH)
        elif direccion == 'atras':
            # Todos los motores hacia atrás (invertir señal)
            for pin in pines_motores:
                gpio.output(pin, gpio.LOW)
        elif direccion == 'derecha':
            # Motores izquierdos adelante, derechos atrás
            gpio.output(pines_motores[0], gpio.HIGH)  # Motor 1 adelante
            gpio.output(pines_motores[1], gpio.LOW)   # Motor 2 atrás
            gpio.output(pines_motores[2], gpio.HIGH)  # Motor 3 adelante
            gpio.output(pines_motores[3], gpio.LOW)   # Motor 4 atrás
        elif direccion == 'izquierda':
            # Motores derechos adelante, izquierdos atrás
            gpio.output(pines_motores[0], gpio.LOW)   # Motor 1 atrás
            gpio.output(pines_motores[1], gpio.HIGH)  # Motor 2 adelante
            gpio.output(pines_motores[2], gpio.LOW)   # Motor 3 atrás
            gpio.output(pines_motores[3], gpio.HIGH)  # Motor 4 adelante
        elif direccion == 'parar':
            # Detener todos los motores
            for pin in pines_motores:
                gpio.output(pin, gpio.LOW)
        
        logger.info(f"Motores: {direccion}")
        return True
    except Exception as e:
        logger.error(f"Error controlando motores: {e}")
        return False


def leer_gps():
    """Lee la posición actual del GPS"""
    try:
        # TODO: Implementar lectura real del GPS USB
        # Por ahora retorna posición de ejemplo
        return {
            'latitud': 4.6097,  # Ejemplo: Bogotá
            'longitud': -74.0817,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error leyendo GPS: {e}")
        return None


def leer_sensor_peso():
    """Lee el valor del sensor de peso HX711"""
    global ultima_lectura_peso
    try:
        # TODO: Implementar lectura real del HX711
        # Por ahora retorna valor de ejemplo
        import random
        ultima_lectura_peso = random.uniform(0, 10)
        return ultima_lectura_peso
    except Exception as e:
        logger.error(f"Error leyendo sensor de peso: {e}")
        return 0.0


# ==================== WEBSOCKET ====================

async def websocket_handler(request):
    """Manejador de conexiones WebSocket"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    websockets_conectados.add(ws)
    logger.info(f"Cliente WebSocket conectado. Total: {len(websockets_conectados)}")
    
    # Enviar estado inicial
    await ws.send_json({
        'tipo': 'conexion',
        'mensaje': 'Conectado al drone',
        'timestamp': datetime.now().isoformat()
    })
    
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await procesar_mensaje_websocket(ws, msg.data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f'Error en WebSocket: {ws.exception()}')
    finally:
        websockets_conectados.discard(ws)
        logger.info(f"Cliente WebSocket desconectado. Total: {len(websockets_conectados)}")
    
    return ws


async def procesar_mensaje_websocket(ws, mensaje):
    """Procesa mensajes recibidos por WebSocket"""
    try:
        datos = json.loads(mensaje)
        tipo = datos.get('tipo')
        
        # Usar GPIO global
        gpio = GPIO_INSTANCE
        
        # Procesar según tipo de mensaje
        if tipo == 'rele':
            # Controlar relé
            numero = datos.get('numero')
            estado = datos.get('estado')
            exito = controlar_rele(gpio, numero, estado)
            await ws.send_json({'tipo': 'respuesta', 'exito': exito, 'accion': 'rele'})
        
        elif tipo == 'motor':
            # Controlar motor
            direccion = datos.get('direccion')
            exito = controlar_motor(gpio, direccion)
            await ws.send_json({'tipo': 'respuesta', 'exito': exito, 'accion': 'motor'})
        
        elif tipo == 'guardar_gps':
            # Guardar ubicación GPS
            posicion = leer_gps()
            if posicion:
                ubicaciones_gps.append(posicion)
                await broadcast_mensaje({
                    'tipo': 'gps_guardado',
                    'posicion': posicion,
                    'total': len(ubicaciones_gps)
                })
        
        elif tipo == 'obtener_gps':
            # Enviar posición GPS actual
            posicion = leer_gps()
            if posicion:
                await ws.send_json({'tipo': 'gps', 'posicion': posicion})
        
        elif tipo == 'obtener_ubicaciones':
            # Enviar todas las ubicaciones guardadas
            await ws.send_json({'tipo': 'ubicaciones', 'datos': ubicaciones_gps})
        
    except json.JSONDecodeError:
        logger.error(f"Error decodificando JSON: {mensaje}")
        await ws.send_json({'tipo': 'error', 'mensaje': 'JSON inválido'})
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        await ws.send_json({'tipo': 'error', 'mensaje': str(e)})


async def broadcast_mensaje(mensaje):
    """Envía un mensaje a todos los WebSockets conectados"""
    if websockets_conectados:
        await asyncio.gather(
            *[ws.send_json(mensaje) for ws in websockets_conectados],
            return_exceptions=True
        )


# ==================== TAREAS EN SEGUNDO PLANO ====================

async def monitorear_peso(app):
    """Tarea que monitorea el sensor de peso continuamente"""
    while True:
        try:
            peso = leer_sensor_peso()
            
            # Si supera el umbral, enviar alerta
            if peso > PESO_UMBRAL:
                await broadcast_mensaje({
                    'tipo': 'alerta_peso',
                    'peso': peso,
                    'umbral': PESO_UMBRAL,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Enviar lectura normal
                await broadcast_mensaje({
                    'tipo': 'peso',
                    'peso': peso,
                    'timestamp': datetime.now().isoformat()
                })
            
            await asyncio.sleep(2)  # Leer cada 2 segundos
        except Exception as e:
            logger.error(f"Error en monitoreo de peso: {e}")
            await asyncio.sleep(5)


async def monitorear_gps(app):
    """Tarea que envía posición GPS continuamente"""
    while True:
        try:
            posicion = leer_gps()
            if posicion:
                await broadcast_mensaje({
                    'tipo': 'gps_actual',
                    'posicion': posicion
                })
            await asyncio.sleep(5)  # Actualizar cada 5 segundos
        except Exception as e:
            logger.error(f"Error en monitoreo GPS: {e}")
            await asyncio.sleep(10)


# ==================== SERVIDOR WEB ====================

async def index_handler(request):
    """Sirve la página principal"""
    archivo = Path(__file__).parent / 'control remoto digital' / 'index.html'
    return web.FileResponse(archivo)


async def on_startup(app):
    """Ejecutado al iniciar el servidor"""
    logger.info("Iniciando servidor del drone acuático...")
    
    # Inicializar GPIO
    gpio = inicializar_gpio()
    app['gpio'] = gpio
    
    # Iniciar tareas en segundo plano
    # app['tarea_peso'] = asyncio.create_task(monitorear_peso(app))  # DESACTIVADO: genera ruido
    app['tarea_gps'] = asyncio.create_task(monitorear_gps(app))
    
    logger.info(f"Servidor iniciado en http://{HOST}:{PORT}")


async def on_shutdown(app):
    """Ejecutado al detener el servidor"""
    logger.info("Deteniendo servidor...")
    
    # Cancelar tareas
    # if 'tarea_peso' in app:
    #     app['tarea_peso'].cancel()
    if 'tarea_gps' in app:
        app['tarea_gps'].cancel()
    
    # Limpiar GPIO
    if app['gpio']:
        app['gpio'].cleanup()
    
    # Cerrar WebSockets
    for ws in list(websockets_conectados):  # Usar list() para evitar "Set changed size during iteration"
        await ws.close()


def crear_app():
    """Crea y configura la aplicación web"""
    app = web.Application()
    
    # Rutas
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_static('/static', Path(__file__).parent / 'control remoto digital', name='static')
    
    # Eventos
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app


# ==================== MAIN ====================

if __name__ == '__main__':
    try:
        app = crear_app()
        web.run_app(app, host=HOST, port=PORT)
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
