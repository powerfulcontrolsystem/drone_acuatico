#!/usr/bin/env python3
"""
Servidor Web del Drone Acuático - OPTIMIZADO PARA BAJA RAM
Control remoto mediante WebSocket
Raspberry Pi 3 - Python 3
"""

import asyncio
import json
import logging
import gc
import serial
import pynmea2
import threading
import subprocess
import os
from datetime import datetime
from pathlib import Path
from aiohttp import web
import aiohttp

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==================== OPTIMIZACIÓN DE RAM AL INICIO ====================
def optimizar_ram_sistema():
    """Ejecuta el script de optimización de RAM antes de iniciar el servidor"""
    try:
        script_path = Path(__file__).parent.parent / "optimizacion" / "limpiar_memoria_optimizado.sh"
        
        if script_path.exists():
            logger.info("🔧 Optimizando RAM del sistema antes de iniciar...")
            resultado = subprocess.run(
                ['bash', str(script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if resultado.returncode == 0:
                logger.info("✓ RAM optimizada correctamente")
                # Mostrar resumen de memoria
                for linea in resultado.stdout.split('\n'):
                    if 'Mem:' in linea or 'disponibles' in linea.lower():
                        logger.info(f"  {linea.strip()}")
            else:
                logger.warning(f"⚠ Script de optimización terminó con código: {resultado.returncode}")
        else:
            logger.warning(f"⚠ Script de optimización no encontrado: {script_path}")
            
    except subprocess.TimeoutExpired:
        logger.error("✗ Timeout ejecutando script de optimización (>30s)")
    except Exception as e:
        logger.error(f"✗ Error optimizando RAM: {e}")
    
    # Pausa de 2 segundos para estabilizar el sistema
    import time
    time.sleep(2)

# Optimizar recolección de basura (mantener funcionalidad, mejorar eficiencia)
gc.set_threshold(700, 10, 10)  # Default pero con gc.collect() estratégico

# ==================== CONFIGURACIÓN ====================
HOST = '0.0.0.0'
PORT = 8080
PESO_UMBRAL = 5.0
MAX_UBICACIONES_GPS = 200  # Límite razonable de ubicaciones
MAX_WEBSOCKETS = 10  # Límite de conexiones simultáneas

# ==================== VARIABLES GLOBALES ====================
websockets_conectados = set()
ubicaciones_gps = []  # Limitado a MAX_UBICACIONES_GPS
ultima_lectura_peso = 0.0
GPIO_INSTANCE = None

# GPS en tiempo real
GPS_PORT = '/dev/ttyACM0'
GPS_BAUDRATE = 9600
gps_data = {'latitud': 4.6097, 'longitud': -74.0817, 'timestamp': None}  # Datos actuales del GPS
gps_lock = threading.Lock()  # Lock para acceso thread-safe


# ==================== FUNCIONES DE HARDWARE ====================

def inicializar_gpio():
    """Inicializa los pines GPIO de la Raspberry Pi"""
    global GPIO_INSTANCE
    if GPIO_INSTANCE:
        return GPIO_INSTANCE
    
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configurar pines de relés
        reles = [4, 7, 8, 9, 11, 21, 22, 23, 24]
        for pin in reles:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)
        
        # Configurar pines de motores
        motores = [18, 13, 19, 12]
        for pin in motores:
            GPIO.setup(pin, GPIO.OUT)
        
        logger.info("GPIO inicializado correctamente")
        GPIO_INSTANCE = GPIO
        gc.collect()  # Liberar memoria después de setup
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
        pines_motores = [18, 13, 19, 12]
        
        if direccion == 'adelante':
            for pin in pines_motores:
                gpio.output(pin, gpio.HIGH)
        elif direccion == 'atras':
            for pin in pines_motores:
                gpio.output(pin, gpio.LOW)
        elif direccion == 'derecha':
            gpio.output(pines_motores[0], gpio.HIGH)
            gpio.output(pines_motores[1], gpio.LOW)
            gpio.output(pines_motores[2], gpio.HIGH)
            gpio.output(pines_motores[3], gpio.LOW)
        elif direccion == 'izquierda':
            gpio.output(pines_motores[0], gpio.LOW)
            gpio.output(pines_motores[1], gpio.HIGH)
            gpio.output(pines_motores[2], gpio.LOW)
            gpio.output(pines_motores[3], gpio.HIGH)
        elif direccion == 'parar':
            for pin in pines_motores:
                gpio.output(pin, gpio.LOW)
        
        logger.info(f"Motores: {direccion}")
        return True
    except Exception as e:
        logger.error(f"Error controlando motores: {e}")
        return False


def leer_gps():
    """Lee la posición actual del GPS desde la variable global"""
    try:
        with gps_lock:
            return {
                'latitud': gps_data['latitud'],
                'longitud': gps_data['longitud'],
                'timestamp': gps_data.get('timestamp') or datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error leyendo datos GPS: {e}")
        return None


def leer_gps_thread():
    """Thread dedicado para leer GPS en tiempo real desde /dev/ttyACM0"""
    logger.info(f"Iniciando lectura de GPS desde {GPS_PORT}...")
    
    while True:
        try:
            # Conectar al GPS
            with serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=1) as ser:
                logger.info(f"GPS conectado en {GPS_PORT}")
                
                while True:
                    try:
                        # Leer línea del GPS
                        line = ser.readline().decode('ascii', errors='ignore').strip()
                        
                        if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                            # Parsear sentencia NMEA GGA (posición)
                            msg = pynmea2.parse(line)
                            
                            if msg.latitude and msg.longitude:
                                with gps_lock:
                                    gps_data['latitud'] = msg.latitude
                                    gps_data['longitud'] = msg.longitude
                                    gps_data['timestamp'] = datetime.now().isoformat()
                                
                                logger.info(f"GPS: {msg.latitude:.6f}, {msg.longitude:.6f}")
                        
                        elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                            # Parsear sentencia NMEA RMC (posición + velocidad)
                            msg = pynmea2.parse(line)
                            
                            if msg.latitude and msg.longitude:
                                with gps_lock:
                                    gps_data['latitud'] = msg.latitude
                                    gps_data['longitud'] = msg.longitude
                                    gps_data['timestamp'] = datetime.now().isoformat()
                    
                    except (pynmea2.ParseError, UnicodeDecodeError) as e:
                        # Ignorar líneas mal formadas
                        continue
                    except Exception as e:
                        logger.error(f"Error parseando GPS: {e}")
                        continue
        
        except serial.SerialException as e:
            logger.error(f"Error conectando GPS en {GPS_PORT}: {e}")
            logger.info("Reintentando conexión GPS en 10 segundos...")
            threading.Event().wait(10)  # Esperar 10s antes de reintentar
        
        except Exception as e:
            logger.error(f"Error inesperado en GPS thread: {e}")
            threading.Event().wait(10)


def leer_memoria_ram():
    """Lee el estado actual de la memoria RAM del sistema"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        
        mem_info = {}
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                mem_info[key.strip()] = int(value.strip().split()[0])  # Valor en KB
        
        total = mem_info.get('MemTotal', 0) / 1024  # MB
        available = mem_info.get('MemAvailable', 0) / 1024  # MB
        used = total - available
        percent = (used / total * 100) if total > 0 else 0
        
        return {
            'total': round(total, 1),
            'used': round(used, 1),
            'available': round(available, 1),
            'percent': round(percent, 1)
        }
    except Exception as e:
        logger.error(f"Error leyendo RAM: {e}")
        return {'total': 0, 'used': 0, 'available': 0, 'percent': 0}


def leer_temperatura():
    """Lee la temperatura de la Raspberry Pi en grados Celsius"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_millis = int(f.read().strip())
        
        temp_celsius = temp_millis / 1000.0
        return {
            'celsius': round(temp_celsius, 1),
            'fahrenheit': round((temp_celsius * 9/5) + 32, 1)
        }
    except Exception as e:
        logger.error(f"Error leyendo temperatura: {e}")
        return {'celsius': 0.0, 'fahrenheit': 0.0}


def leer_sensor_peso():
    """Lee el valor del sensor de peso HX711"""
    global ultima_lectura_peso
    try:
        # TODO: Implementar lectura real del HX711 cuando se conecte
        # Por ahora retorna 0 para evitar alertas falsas
        # import RPi.GPIO as GPIO
        # from hx711 import HX711
        # hx = HX711(dout_pin=5, pd_sck_pin=6)
        # peso = hx.get_weight_mean(5)  # Promedio de 5 lecturas
        # ultima_lectura_peso = peso
        # return ultima_lectura_peso
        
        ultima_lectura_peso = 0.0  # Sin sensor conectado
        return ultima_lectura_peso
    except Exception as e:
        logger.error(f"Error leyendo sensor de peso: {e}")
        return 0.0


# ==================== WEBSOCKET ====================

async def websocket_handler(request):
    """Manejador de conexiones WebSocket"""
    # Limitar conexiones simultáneas para estabilidad
    if len(websockets_conectados) >= MAX_WEBSOCKETS:
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        await ws.send_json({'tipo': 'error', 'mensaje': 'Máximo de conexiones alcanzado'})
        await ws.close()
        return ws
    
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)
    websockets_conectados.add(ws)
    
    logger.info(f"Cliente WebSocket conectado. Total: {len(websockets_conectados)}")
    
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
        gc.collect()  # Optimización: limpiar memoria
    
    return ws


async def procesar_mensaje_websocket(ws, mensaje):
    """Procesa mensajes recibidos por WebSocket"""
    try:
        datos = json.loads(mensaje)
        tipo = datos.get('tipo')
        gpio = GPIO_INSTANCE or inicializar_gpio()
        
        if tipo == 'rele':
            numero = datos.get('numero')
            estado = datos.get('estado')
            exito = controlar_rele(gpio, numero, estado)
            await ws.send_json({'tipo': 'respuesta', 'exito': exito, 'accion': 'rele'})
        
        elif tipo == 'motor':
            direccion = datos.get('direccion')
            exito = controlar_motor(gpio, direccion)
            await ws.send_json({'tipo': 'respuesta', 'exito': exito, 'accion': 'motor'})
        
        elif tipo == 'guardar_gps':
            posicion = leer_gps()
            if posicion:
                # Limitar ubicaciones guardadas para evitar crecimiento infinito
                if len(ubicaciones_gps) >= MAX_UBICACIONES_GPS:
                    ubicaciones_gps.pop(0)
                ubicaciones_gps.append(posicion)
                await broadcast_mensaje({
                    'tipo': 'gps_guardado',
                    'posicion': posicion,
                    'total': len(ubicaciones_gps)
                })
        
        elif tipo == 'obtener_gps':
            posicion = leer_gps()
            if posicion:
                await ws.send_json({'tipo': 'gps', 'posicion': posicion})
        
        elif tipo == 'obtener_ubicaciones':
            await ws.send_json({'tipo': 'ubicaciones', 'datos': ubicaciones_gps})
        
        elif tipo == 'navegar_a':
            # Recibir comando de navegación a un punto específico
            lat = datos.get('latitud')
            lng = datos.get('longitud')
            logger.info(f"Comando de navegación recibido: Lat {lat}, Lng {lng}")
            
            # TODO: Implementar navegación autónoma
            # Por ahora solo registra el comando
            await ws.send_json({
                'tipo': 'respuesta',
                'exito': True,
                'accion': 'navegar',
                'mensaje': f'Navegando a {lat}, {lng}'
            })
            
            # Broadcast para informar a todos los clientes
            await broadcast_mensaje({
                'tipo': 'navegacion_iniciada',
                'destino': {'latitud': lat, 'longitud': lng}
            })
        
    except json.JSONDecodeError:
        logger.error(f"Error decodificando JSON: {mensaje}")
        await ws.send_json({'tipo': 'error', 'mensaje': 'JSON inválido'})
    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        await ws.send_json({'tipo': 'error', 'mensaje': str(e)})


async def broadcast_mensaje(mensaje):
    """Broadcast a todos los WebSockets"""
    if websockets_conectados:
        await asyncio.gather(
            *[ws.send_json(mensaje) for ws in websockets_conectados],
            return_exceptions=True
        )


# ==================== TAREAS EN SEGUNDO PLANO ====================

async def monitorear_peso(app):
    """Tarea que monitorea el sensor de peso continuamente"""
    # NOTA: Sensor de peso desactivado hasta conectar HX711
    logger.info("Monitoreo de peso: esperando conexión del sensor HX711")
    
    while True:
        try:
            peso = leer_sensor_peso()
            
            # Solo enviar si el peso es mayor a 0 (sensor conectado)
            if peso > 0.1:  # Umbral mínimo para detectar sensor conectado
                if peso > PESO_UMBRAL:
                    await broadcast_mensaje({
                        'tipo': 'alerta_peso',
                        'peso': peso,
                        'umbral': PESO_UMBRAL,
                        'timestamp': datetime.now().isoformat()
                    })
                else:
                    await broadcast_mensaje({
                        'tipo': 'peso',
                        'peso': peso,
                        'timestamp': datetime.now().isoformat()
                    })
            
            await asyncio.sleep(2)
            gc.collect()  # Optimización: limpiar memoria periódicamente
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
            await asyncio.sleep(5)
            gc.collect()  # Optimización: limpiar memoria periódicamente
        except Exception as e:
            logger.error(f"Error en monitoreo GPS: {e}")
            await asyncio.sleep(10)


async def monitorear_ram(app):
    """Tarea que envía estado de RAM continuamente"""
    while True:
        try:
            ram = leer_memoria_ram()
            await broadcast_mensaje({
                'tipo': 'ram',
                'datos': ram
            })
            await asyncio.sleep(10)  # Actualizar cada 10 segundos
        except Exception as e:
            logger.error(f"Error en monitoreo RAM: {e}")
            await asyncio.sleep(10)


async def monitorear_temperatura(app):
    """Tarea que envía temperatura de la Raspberry Pi continuamente"""
    while True:
        try:
            temp = leer_temperatura()
            await broadcast_mensaje({
                'tipo': 'temperatura',
                'datos': temp
            })
            await asyncio.sleep(5)  # Actualizar cada 5 segundos
        except Exception as e:
            logger.error(f"Error en monitoreo de temperatura: {e}")
            await asyncio.sleep(5)


# ==================== SERVIDOR WEB ====================

async def index_handler(request):
    """Sirve la página principal"""
    archivo = Path(__file__).parent / 'control remoto digital' / 'index.html'
    return web.FileResponse(archivo)


async def on_startup(app):
    """Ejecutado al iniciar el servidor"""
    logger.info("Iniciando servidor del drone acuático...")
    
    gpio = inicializar_gpio()
    app['gpio'] = gpio
    
    # Iniciar thread de lectura GPS (en segundo plano)
    gps_thread = threading.Thread(target=leer_gps_thread, daemon=True)
    gps_thread.start()
    logger.info("Thread de GPS iniciado")
    
    # Iniciar tareas en segundo plano
    app['tarea_peso'] = asyncio.create_task(monitorear_peso(app))
    app['tarea_gps'] = asyncio.create_task(monitorear_gps(app))
    app['tarea_ram'] = asyncio.create_task(monitorear_ram(app))
    app['tarea_temp'] = asyncio.create_task(monitorear_temperatura(app))
    
    gc.collect()  # Optimización inicial
    logger.info(f"Servidor iniciado en http://{HOST}:{PORT}")


async def on_shutdown(app):
    """Ejecutado al detener el servidor"""
    logger.info("Deteniendo servidor...")
    
    if 'tarea_peso' in app:
        app['tarea_peso'].cancel()
    if 'tarea_gps' in app:
        app['tarea_gps'].cancel()
    if 'tarea_ram' in app:
        app['tarea_ram'].cancel()
    if 'tarea_temp' in app:
        app['tarea_temp'].cancel()
    
    if app.get('gpio'):
        app['gpio'].cleanup()
    
    for ws in list(websockets_conectados):
        await ws.close()
    
    gc.collect()


def crear_app():
    """Crea y configura la aplicación web"""
    app = web.Application(client_max_size=5*1024*1024)  # 5MB max (razonable)
    
    app.router.add_get('/', index_handler)
    app.router.add_get('/ws', websocket_handler)
    app.router.add_static('/static', Path(__file__).parent / 'control remoto digital', name='static')
    
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    return app


# ==================== MAIN ====================

if __name__ == '__main__':
    # PASO 1: Optimizar RAM del sistema antes de iniciar
    optimizar_ram_sistema()
    
    # PASO 2: Verificar permisos del puerto GPS
    import os
    if os.path.exists(GPS_PORT):
        logger.info(f"Puerto GPS encontrado: {GPS_PORT}")
    else:
        logger.warning(f"Puerto GPS no encontrado: {GPS_PORT}. El GPS usará datos mock.")
    
    # PASO 3: Iniciar servidor
    try:
        logger.info("🚀 Iniciando servidor del drone acuático...")
        app = crear_app()
        web.run_app(
            app, 
            host=HOST, 
            port=PORT,
            access_log=None,  # Optimización: sin access log detallado
            shutdown_timeout=10.0
        )
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
