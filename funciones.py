#!/usr/bin/env python3
"""
FUNCIONES DEL DRONE ACUÁTICO
Contiene todas las funciones para controlar hardware y sensores
"""

import logging
import subprocess
import serial
import threading
import os
import signal

# Configuración de logging
logger = logging.getLogger(__name__)

# ==================== CONFIGURACIÓN ====================

# Relés GPIO (BCM)
RELES_PINES = {1: 4, 2: 7, 3: 8, 4: 9, 5: 11, 6: 21, 7: 22, 8: 23, 9: 24}
ESTADO_RELES = {i: False for i in range(1, 10)}

# Motores PWM
MOTORES_PWM = {1: 18, 2: 13, 3: 19, 4: 12}

# GPS
GPS_DATOS = {
    'latitud': None,
    'longitud': None,
    'altitud': None,
    'velocidad': None,
    'satelites': 0,
    'timestamp': None,
    'valido': False
}
GPS_PUERTO = '/dev/ttyACM0'
GPS_BAUDRATE = 9600
gps_thread = None
gps_running = False
UMBRAL_PESO_KG = 5.0

# Importaciones opcionales
try:
    import RPi.GPIO as GPIO
    GPIO_DISPONIBLE = True
except ImportError:
    GPIO = None
    GPIO_DISPONIBLE = False

try:
    import pynmea2
    GPS_DISPONIBLE = True
except ImportError:
    pynmea2 = None
    GPS_DISPONIBLE = False

# ==================== GESTIÓN DE PROCESOS ====================

def matar_procesos_servidor_previos():
    """
    Busca y termina cualquier proceso del servidor que esté corriendo.
    Evita conflictos al iniciar el servidor.
    
    Returns:
        int: Número de procesos terminados
    """
    try:
        pid_actual = os.getpid()
        procesos_terminados = 0
        
        # Buscar procesos con 'servidor.py' en el nombre
        resultado = subprocess.run(
            ['pgrep', '-f', 'servidor.py'],
            capture_output=True,
            text=True
        )
        
        if resultado.returncode == 0:
            pids = resultado.stdout.strip().split('\n')
            
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    
                    # No matar el proceso actual
                    if pid == pid_actual:
                        continue
                    
                    # Intentar terminar el proceso
                    os.kill(pid, signal.SIGTERM)
                    logger.info(f"Proceso servidor previo terminado (PID: {pid})")
                    procesos_terminados += 1
                    
                except (ValueError, ProcessLookupError) as e:
                    logger.debug(f"No se pudo terminar proceso {pid_str}: {e}")
                except PermissionError:
                    logger.warning(f"Sin permisos para terminar proceso {pid_str}")
        
        if procesos_terminados > 0:
            logger.info(f"Se terminaron {procesos_terminados} proceso(s) del servidor previo(s)")
        else:
            logger.info("No se encontraron procesos del servidor previos")
        
        return procesos_terminados
    
    except Exception as e:
        logger.error(f"Error buscando procesos previos: {e}")
        return 0

# ==================== FUNCIONES GPIO ====================

def inicializar_gpio():
    """Inicializa los pines GPIO para relés y motores."""
    if not GPIO_DISPONIBLE:
        logger.warning("GPIO no disponible - Modo simulación")
        return False
    
    try:
        # Limpiar GPIO previo (sin advertencias)
        try:
            GPIO.setwarnings(False)
            GPIO.cleanup()
            logger.info("GPIO limpiado (proceso previo)")
        except:
            pass
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Configurar relés
        for numero, pin in RELES_PINES.items():
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = apagado
            logger.info(f"Relé {numero} → GPIO {pin}")
        
        # Configurar motores
        for numero, pin in MOTORES_PWM.items():
            GPIO.setup(pin, GPIO.OUT)
            logger.info(f"Motor {numero} → GPIO {pin}")
        
        logger.info("GPIO inicializado correctamente")
        return True
    
    except Exception as e:
        logger.error(f"Error inicializando GPIO: {e}")
        return False


def controlar_rele(numero, encender):
    """
    Controla un relé específico.
    
    Args:
        numero (int): Número del relé (1-9)
        encender (bool): True para encender, False para apagar
    
    Returns:
        tuple: (exito: bool, error: str o None)
    """
    if numero not in RELES_PINES:
        return False, f"Relé {numero} no válido (1-9)"
    
    if not GPIO_DISPONIBLE:
        # Modo simulación
        ESTADO_RELES[numero] = encender
        logger.info(f"[SIM] Relé {numero}: {'ON' if encender else 'OFF'}")
        return True, None
    
    try:
        pin = RELES_PINES[numero]
        # Relé activo-bajo: LOW=encendido, HIGH=apagado
        GPIO.output(pin, GPIO.LOW if encender else GPIO.HIGH)
        ESTADO_RELES[numero] = encender
        logger.info(f"Relé {numero}: {'ENCENDIDO' if encender else 'APAGADO'}")
        return True, None
    
    except Exception as e:
        logger.error(f"Error controlando relé {numero}: {e}")
        return False, str(e)


def controlar_motor(direccion, velocidad):
    """
    Controla los motores del drone.
    
    Args:
        direccion (str): 'adelante', 'atras', 'izquierda', 'derecha', 'parar'
        velocidad (int): Velocidad en porcentaje (0-100)
    
    Returns:
        tuple: (exito: bool, error: str o None)
    """
    if not GPIO_DISPONIBLE:
        logger.info(f"[SIM] Motor {direccion} al {velocidad}%")
        return True, None
    
    try:
        # Implementación simplificada - expandir según hardware
        logger.info(f"Motor {direccion} al {velocidad}%")
        # Aquí iría la lógica de PWM para controlar motores
        return True, None
    
    except Exception as e:
        logger.error(f"Error controlando motor: {e}")
        return False, str(e)


def liberar_gpio():
    """Libera los recursos GPIO al cerrar."""
    if GPIO_DISPONIBLE:
        try:
            GPIO.cleanup()
            logger.info("GPIO liberado")
        except Exception as e:
            logger.error(f"Error liberando GPIO: {e}")


# ==================== FUNCIONES DE MONITOREO ====================

def obtener_ram():
    """
    Obtiene información del uso de RAM del sistema.
    
    Returns:
        dict: {'total': int, 'used': int, 'available': int, 'percent': int}
    """
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        
        total = int([l for l in lines if 'MemTotal' in l][0].split()[1]) // 1024
        available = int([l for l in lines if 'MemAvailable' in l][0].split()[1]) // 1024
        used = total - available
        percent = int((used / total) * 100)
        
        return {
            'total': total,
            'used': used,
            'available': available,
            'percent': percent
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo RAM: {e}")
        return {'total': 0, 'used': 0, 'available': 0, 'percent': 0}


def obtener_temperatura():
    """
    Obtiene la temperatura del CPU de la Raspberry Pi.
    
    Returns:
        dict: {'temperatura': float, 'unidad': str}
    """
    try:
        temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        temp_valor = float(temp.replace("temp=", "").replace("'C\n", ""))
        
        return {
            'temperatura': temp_valor,
            'unidad': 'C'
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo temperatura: {e}")
        return {'temperatura': 0, 'unidad': 'C'}


def obtener_bateria():
    """
    Obtiene el estado de la batería.
    Actualmente simulado - reemplazar con lectura real del sensor.
    
    Returns:
        dict: {'porcentaje': int, 'voltaje': float, 'estado': str}
    """
    # TODO: Implementar lectura real del sensor de batería y panel solar
    return {
        'porcentaje': 85,
        'voltaje': 12.4,
        'estado': 'cargando',
        'cargando': True
    }


def obtener_peso():
    """
    Obtiene el peso medido por el sensor HX711.
    Actualmente simulado hasta integrar el hardware.
    """
    try:
        # TODO: Leer peso real desde HX711
        peso_kg = 1.2
        alerta = peso_kg >= UMBRAL_PESO_KG
        return {
            'peso_kg': round(peso_kg, 2),
            'umbral_kg': UMBRAL_PESO_KG,
            'alerta': alerta
        }
    except Exception as e:
        logger.error(f"Error obteniendo peso: {e}")
        return {
            'peso_kg': 0.0,
            'umbral_kg': UMBRAL_PESO_KG,
            'alerta': False
        }


def obtener_solar():
    """
    Obtiene el estado de los paneles solares y carga.
    Actualmente simulado hasta integrar lecturas reales.
    """
    try:
        # TODO: Integrar lectura real de controlador/MPPT
        panel_volt = 18.5
        panel_amp = 2.3
        potencia = round(panel_volt * panel_amp, 1)
        return {
            'panel_voltaje': panel_volt,
            'panel_corriente': panel_amp,
            'potencia': potencia,
            'bateria_voltaje': 12.4,
            'estado': 'cargando'
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos solares: {e}")
        return {
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0.0,
            'bateria_voltaje': 0.0,
            'estado': 'desconocido'
        }


def obtener_velocidad_red():
    """
    Obtiene la velocidad de conexión a internet.
    Intenta varios métodos, siendo más rápido el primero que funcione.
    Retorna la velocidad en Kbps (kilobits por segundo).
    """
    try:
        # Método 1: iperf3 (más rápido si está disponible)
        try:
            # Esto requeriría un servidor iperf3, así que saltamos
            pass
        except:
            pass
        
        # Método 2: speedtest-cli (más preciso pero más lento)
        try:
            resultado = subprocess.run(
                ['speedtest-cli', '--simple'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if resultado.returncode == 0:
                lineas = resultado.stdout.strip().split('\n')
                if len(lineas) >= 2:
                    # Formato: ping, download (Mbps), upload (Mbps)
                    velocidad_mbps = float(lineas[1])
                    velocidad_kbps = velocidad_mbps * 1000  # Convertir a Kbps
                    logger.info(f"Velocidad red (speedtest): {velocidad_mbps:.2f} Mbps")
                    return {'velocidad': velocidad_kbps}
        except subprocess.TimeoutExpired:
            logger.warning("Timeout en speedtest-cli (>60s)")
        except FileNotFoundError:
            logger.debug("speedtest-cli no instalado")
        
        # Método 3: ookla speedtest (si speedtest-cli no funciona)
        try:
            resultado = subprocess.run(
                ['speedtest', '--simple'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if resultado.returncode == 0:
                lineas = resultado.stdout.strip().split('\n')
                if len(lineas) >= 2:
                    velocidad_mbps = float(lineas[1])
                    velocidad_kbps = velocidad_mbps * 1000
                    logger.info(f"Velocidad red (ookla speedtest): {velocidad_mbps:.2f} Mbps")
                    return {'velocidad': velocidad_kbps}
        except:
            pass
        
        # Método 4: Medir con curl/wget a un servidor conocido (rápido pero menos preciso)
        try:
            import time
            # Descargar 1MB de un servidor rápido
            url = "http://speedtest.ftp.otenet.gr/files/test10Mb.db"
            inicio = time.time()
            resultado = subprocess.run(
                ['curl', '-o', '/dev/null', '-s', '-w', '%{speed_download}', url],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if resultado.returncode == 0:
                # curl retorna bytes/segundo
                velocidad_bytes_seg = float(resultado.stdout.strip())
                velocidad_kbps = velocidad_bytes_seg * 8 / 1000  # Convertir a Kbps
                logger.info(f"Velocidad red (curl): {velocidad_kbps:.2f} Kbps")
                if velocidad_kbps > 0:
                    return {'velocidad': velocidad_kbps}
        except Exception as e:
            logger.debug(f"Error con método curl: {e}")
    
    except Exception as e:
        logger.debug(f"Error obteniendo velocidad red: {e}")
    
    # Retornar velocidad desconocida si hay error
    return {'velocidad': 0}


# ==================== FUNCIONES GPS ====================

def leer_gps_serial():
    """
    Lee datos GPS continuamente desde el puerto serial.
    Esta función se ejecuta en un hilo separado.
    """
    global gps_running, GPS_DATOS
    
    if not GPS_DISPONIBLE:
        logger.warning("pynmea2 no disponible - GPS deshabilitado")
        return
    
    logger.info(f"Iniciando lectura GPS en {GPS_PUERTO} @ {GPS_BAUDRATE}")
    
    while gps_running:
        try:
            with serial.Serial(GPS_PUERTO, GPS_BAUDRATE, timeout=1) as ser:
                logger.info(f"GPS conectado en {GPS_PUERTO}")
                
                while gps_running:
                    try:
                        linea = ser.readline().decode('ascii', errors='ignore').strip()
                        
                        # Sentencia GGA: posición, altitud, satélites
                        if linea.startswith('$GPGGA') or linea.startswith('$GNGGA'):
                            msg = pynmea2.parse(linea)
                            if msg.lat and msg.lon:
                                GPS_DATOS['latitud'] = msg.latitude
                                GPS_DATOS['longitud'] = msg.longitude
                                GPS_DATOS['altitud'] = msg.altitude if msg.altitude else 0
                                GPS_DATOS['satelites'] = msg.num_sats if msg.num_sats else 0
                                GPS_DATOS['valido'] = (msg.gps_qual > 0)
                                GPS_DATOS['timestamp'] = str(msg.timestamp) if msg.timestamp else None
                        
                        # Sentencia RMC: velocidad
                        elif linea.startswith('$GPRMC') or linea.startswith('$GNRMC'):
                            msg = pynmea2.parse(linea)
                            if hasattr(msg, 'spd_over_grnd') and msg.spd_over_grnd:
                                GPS_DATOS['velocidad'] = float(msg.spd_over_grnd) * 1.852  # nudos a km/h
                    
                    except pynmea2.ParseError:
                        pass  # Ignorar líneas NMEA mal formateadas
                    
                    except Exception as e:
                        logger.error(f"Error procesando datos GPS: {e}")
        
        except serial.SerialException as e:
            logger.warning(f"Error en conexión GPS: {e}")
            if gps_running:
                logger.info("Reintentando conexión GPS en 5 segundos...")
                threading.Event().wait(5)
        
        except Exception as e:
            logger.error(f"Error inesperado en GPS: {e}")
            if gps_running:
                threading.Event().wait(5)
    
    logger.info("Hilo GPS detenido")


def iniciar_gps():
    """
    Inicia el hilo de lectura GPS en segundo plano.
    
    Returns:
        bool: True si se inició correctamente, False si no está disponible
    """
    global gps_thread, gps_running
    
    if not GPS_DISPONIBLE:
        logger.warning("GPS no disponible - pynmea2 no instalado")
        return False
    
    gps_running = True
    gps_thread = threading.Thread(target=leer_gps_serial, daemon=True)
    gps_thread.start()
    logger.info("Hilo GPS iniciado")
    return True


def detener_gps():
    """Detiene el hilo de lectura GPS."""
    global gps_running
    gps_running = False
    if gps_thread:
        gps_thread.join(timeout=2)
    logger.info("GPS detenido")


def obtener_posicion_gps():
    """
    Obtiene la posición GPS actual.
    
    Returns:
        dict: Datos GPS actuales o None si no hay señal
    """
    if GPS_DATOS['valido']:
        return {
            'lat': GPS_DATOS['latitud'],
            'lon': GPS_DATOS['longitud'],
            'alt': GPS_DATOS['altitud'],
            'velocidad': GPS_DATOS['velocidad'],
            'satelites': GPS_DATOS['satelites'],
            'timestamp': GPS_DATOS['timestamp']
        }
    return None


def guardar_posicion_gps(recorrido_id=None):
    """
    Guarda la posición GPS actual en la base de datos.
    Si no hay recorrido activo, se crea uno de uso manual.
    
    Args:
        recorrido_id (int|None): ID de recorrido activo si existe
    
    Returns:
        tuple: (exito: bool, mensaje: str)
    """
    if not GPS_DATOS['valido']:
        return False, "Sin señal GPS válida"

    try:
        # Importación diferida para evitar ciclos
        from base_datos import iniciar_recorrido, guardar_posicion_gps as guardar_posicion_bd
    except Exception as e:  # pragma: no cover - protección en tiempo de ejecución
        logger.error(f"No se pudo importar base de datos: {e}")
        return False, "Error de base de datos"

    try:
        recorrido = recorrido_id
        if recorrido is None:
            recorrido = iniciar_recorrido("Recorrido manual")
            if not recorrido:
                return False, "No se pudo crear recorrido manual"

        posicion_id = guardar_posicion_bd(
            recorrido,
            GPS_DATOS['latitud'],
            GPS_DATOS['longitud'],
            GPS_DATOS['altitud'] or 0,
            GPS_DATOS['velocidad'] or 0,
            GPS_DATOS['satelites'] or 0
        )

        if not posicion_id:
            return False, "No se pudo guardar la posición"

        logger.info(
            "Posición guardada en recorrido %s: lat=%s, lon=%s", recorrido, GPS_DATOS['latitud'], GPS_DATOS['longitud']
        )
        return True, f"Ubicación guardada (recorrido {recorrido})"

    except Exception as e:  # pragma: no cover - registros en tiempo de ejecución
        logger.error(f"Error guardando posición GPS: {e}")
        return False, str(e)


# ==================== FUNCIONES DE SISTEMA ====================

def apagar_sistema():
    """Apaga la Raspberry Pi de forma segura."""
    logger.warning("Iniciando apagado del sistema...")
    try:
        subprocess.Popen(['sudo', 'shutdown', '-h', 'now'])
        return True, "Apagando sistema..."
    except Exception as e:
        logger.error(f"Error al apagar: {e}")
        return False, str(e)


def reiniciar_sistema():
    """Reinicia la Raspberry Pi."""
    logger.warning("Iniciando reinicio del sistema...")
    try:
        subprocess.Popen(['sudo', 'reboot'])
        return True, "Reiniciando sistema..."
    except Exception as e:
        logger.error(f"Error al reiniciar: {e}")
        return False, str(e)
