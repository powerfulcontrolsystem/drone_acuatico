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
import time

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

# Detectar puerto GPS automáticamente
def _detectar_puerto_gps():
    """Detecta automáticamente el puerto del módulo GPS"""
    import glob
    puertos = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    return puertos[0] if puertos else '/dev/ttyACM0'

GPS_PUERTO = _detectar_puerto_gps()
GPS_BAUDRATE = 9600
gps_thread = None
gps_running = False
UMBRAL_PESO_KG = 5.0

# Estado inicial de IO para precalcular MB/s

# Estado inicial de IO para precalcular MB/s

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
    # Guardar estado en base de datos
    try:
        from base_de_datos.base_datos import guardar_estado_rele
        guardar_estado_rele(numero, int(encender))
    except Exception as e:
        logger.error(f"No se pudo guardar estado de relé en BD: {e}")
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
        logger.info(f"[SIM] Motor {direccion} al {velocidad}% (tanque)")
        return True, None

    try:
        # Pines de motores tanque
        pin_izq = MOTORES_PWM[1]  # GPIO 18
        pin_der = MOTORES_PWM[2]  # GPIO 13

        # Inicializar PWM si no existe
        if not hasattr(controlar_motor, 'pwm_izq') or controlar_motor.pwm_izq is None:
            controlar_motor.pwm_izq = GPIO.PWM(pin_izq, 100)
            controlar_motor.pwm_izq.start(0)
        if not hasattr(controlar_motor, 'pwm_der') or controlar_motor.pwm_der is None:
            controlar_motor.pwm_der = GPIO.PWM(pin_der, 100)
            controlar_motor.pwm_der.start(0)

        if direccion == 'adelante':
            controlar_motor.pwm_izq.ChangeDutyCycle(velocidad)
            controlar_motor.pwm_der.ChangeDutyCycle(velocidad)
            logger.info(f"Motores adelante: izq={velocidad}%, der={velocidad}%")
        elif direccion == 'atras':
            # Si hay lógica de reversa, implementar aquí
            controlar_motor.pwm_izq.ChangeDutyCycle(0)
            controlar_motor.pwm_der.ChangeDutyCycle(0)
            logger.info("Motores atrás (no implementado, ambos detenidos)")
        elif direccion == 'izquierda':
            controlar_motor.pwm_izq.ChangeDutyCycle(0)
            controlar_motor.pwm_der.ChangeDutyCycle(velocidad)
            logger.info(f"Giro izquierda: izq=0%, der={velocidad}%")
        elif direccion == 'derecha':
            controlar_motor.pwm_izq.ChangeDutyCycle(velocidad)
            controlar_motor.pwm_der.ChangeDutyCycle(0)
            logger.info(f"Giro derecha: izq={velocidad}%, der=0%")
        elif direccion == 'parar':
            controlar_motor.pwm_izq.ChangeDutyCycle(0)
            controlar_motor.pwm_der.ChangeDutyCycle(0)
            logger.info("Motores detenidos")
        else:
            logger.warning(f"Dirección desconocida: {direccion}")
            controlar_motor.pwm_izq.ChangeDutyCycle(0)
            controlar_motor.pwm_der.ChangeDutyCycle(0)
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
def obtener_voltaje_raspberry():
    """
    Obtiene el estado de voltaje de la Raspberry Pi usando vcgencmd get_throttled.
    Retorna dict con voltaje (simulado), alerta (bool) y estado raw.
    """
    try:
        # Leer estado de throttling para alerta
        salida = subprocess.check_output(['vcgencmd', 'get_throttled']).decode().strip()
        valor = salida.split('=')[1] if '=' in salida else salida
        alerta = False
        if valor.endswith('5') or valor.endswith('05') or valor.endswith('50005') or valor.endswith('80005'):
            alerta = True
        voltaje = 5.0 if not alerta else 4.5  # Valor simbólico, solo para mostrar
        return {
            'voltaje': voltaje,
            'alerta': alerta,
            'estado_raw': valor
        }
    except Exception as e:
        logger.error(f"Error obteniendo voltaje Raspberry Pi: {e}")
        return {'voltaje': 0.0, 'alerta': False, 'estado_raw': 'error'}
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


def obtener_cpu():
    """
    Obtiene el uso del procesador (CPU) en porcentaje.
    
    Returns:
        dict: {'porcentaje': int, 'cores': int}
    """
    try:
        # Leer /proc/stat para calcular el uso de CPU
        with open('/proc/stat', 'r') as f:
            linea = f.readline()
        
        campos = linea.split()
        # cpu user nice system idle iowait irq softirq steal guest guest_nice
        if campos[0] == 'cpu':
            user = int(campos[1])
            nice = int(campos[2])
            system = int(campos[3])
            idle = int(campos[4])
            iowait = int(campos[5])
            
            total = user + nice + system + idle + iowait
            uso_cpu = int((total - idle) / total * 100) if total > 0 else 0
            
            # Contar número de cores
            try:
                num_cores = os.cpu_count() or 1
            except:
                num_cores = 1
            
            return {
                'porcentaje': uso_cpu,
                'cores': num_cores
            }
    except Exception as e:
        logger.error(f"Error obteniendo CPU: {e}")
        return {'porcentaje': 0, 'cores': 1}


def obtener_almacenamiento():
    """
    Obtiene información del almacenamiento (microSD) de la Raspberry Pi.
    
    Returns:
        dict: {'total_gb': float, 'usado_gb': float, 'disponible_gb': float, 'porcentaje': int}
    """
    try:
        import shutil
        # Obtener información del filesystem raíz (donde está la microSD)
        stats = shutil.disk_usage('/')
        
        total_gb = stats.total / (1024**3)  # Convertir bytes a GB
        usado_gb = stats.used / (1024**3)
        disponible_gb = stats.free / (1024**3)
        porcentaje = int((stats.used / stats.total) * 100) if stats.total > 0 else 0
        
        return {
            'total_gb': round(total_gb, 2),
            'usado_gb': round(usado_gb, 2),
            'disponible_gb': round(disponible_gb, 2),
            'porcentaje': porcentaje
        }
    except Exception as e:
        logger.error(f"Error obteniendo almacenamiento: {e}")
        return {
            'total_gb': 0.0,
            'usado_gb': 0.0,
            'disponible_gb': 0.0,
            'porcentaje': 0
        }


def obtener_io_sd(dispositivo='mmcblk0'):
    """
    Lee contadores de E/S del dispositivo (microSD) desde /proc/diskstats.
    Devuelve contadores acumulados para que el cliente calcule tasas.

    Returns:
        dict: {
            'dispositivo': str,
            'sectores_leidos': int,
            'sectores_escritos': int,
            'tamano_sector': int,  # bytes
            'timestamp': float
        }
    """
    try:
        sector_size = 512
        sector_path = f"/sys/block/{dispositivo}/queue/hw_sector_size"
        if os.path.exists(sector_path):
            with open(sector_path, 'r') as f:
                sector_size = int(f.read().strip()) or 512

        with open('/proc/diskstats', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 14:
                    continue
                if parts[2] == dispositivo:
                    sectores_leidos = int(parts[5])
                    sectores_escritos = int(parts[9])
                    return {
                        'dispositivo': dispositivo,
                        'sectores_leidos': sectores_leidos,
                        'sectores_escritos': sectores_escritos,
                        'tamano_sector': sector_size,
                        'timestamp': time.time()
                    }
        # Si no se encontró el dispositivo, devolver ceros
        return {
            'dispositivo': dispositivo,
            'sectores_leidos': 0,
            'sectores_escritos': 0,
            'tamano_sector': sector_size,
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error obteniendo IO de disco: {e}")
        return {
            'dispositivo': dispositivo,
            'sectores_leidos': 0,
            'sectores_escritos': 0,
            'tamano_sector': 512,
            'timestamp': time.time()
        }



def obtener_uso_disco_porcentaje(dispositivo='/'):
    """
    Obtiene el porcentaje de uso del disco sin realizar cálculos I/O.
    Muy eficiente, no genera impacto en el sistema.
    
    Returns:
        dict: {'uso_porcentaje': float (0-100), 'timestamp': float}
    """
    try:
        import shutil
        stats = shutil.disk_usage(dispositivo)
        uso_pct = (stats.used / stats.total) * 100
        
        return {
            'uso_porcentaje': round(uso_pct, 1),
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error obteniendo uso de disco: {e}")
        return {'uso_porcentaje': 0, 'timestamp': time.time()}

def obtener_uso_disco_porcentaje(dispositivo='/'):
    """
    Obtiene el porcentaje de uso del disco sin realizar cálculos I/O.
    Muy eficiente, no genera impacto en el sistema.
    
    Returns:
        dict: {'uso_porcentaje': float (0-100), 'timestamp': float}
    """
    try:
        import shutil
        stats = shutil.disk_usage(dispositivo)
        uso_pct = (stats.used / stats.total) * 100
        
        return {
            'uso_porcentaje': round(uso_pct, 1),
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error obteniendo uso de disco: {e}")
        return {'uso_porcentaje': 0, 'timestamp': time.time()}

def obtener_bateria():
    """
    Obtiene el estado de la batería desde el controlador Victron.
    Lee datos reales del puerto serial VE.Direct.
    
    Returns:
        dict: {'porcentaje': int, 'voltaje': float, 'estado': str, 'conectado': bool}
    """
    try:
        # Leer datos del Victron
        datos_victron = leer_victron()
        
        if datos_victron and datos_victron.get('exito'):
            # Extraer voltaje de batería del Victron
            voltaje = datos_victron.get('bateria_voltaje', 0.0)
            corriente = datos_victron.get('bateria_corriente', 0.0)
            estado = datos_victron.get('estado', 'desconectado')
            
            # Calcular porcentaje de carga basado en voltaje (aproximado para batería de 12V)
            # Rango típico: 10.5V (0%) a 14.7V (100%) para batería de litio
            # Para ácido-plomo: 10.5V (0%) a 12.6V (100%)
            # Usando rango litio por defecto (más preciso)
            porcentaje = max(0, min(100, int((voltaje - 10.5) / (14.7 - 10.5) * 100)))
            
            return {
                'porcentaje': porcentaje,
                'voltaje': voltaje,
                'corriente': corriente,
                'estado': estado,
                'conectado': True
            }
        else:
            # Victron no disponible
            logger.warning("Victron no disponible para obtener datos de batería")
            return {
                'porcentaje': 0,
                'voltaje': 0.0,
                'corriente': 0.0,
                'estado': 'desconectado',
                'conectado': False,
                'error': datos_victron.get('error', 'No conectado') if datos_victron else 'No detectado'
            }
    except Exception as e:
        logger.error(f"Error obteniendo datos de batería: {e}")
        return {
            'porcentaje': 0,
            'voltaje': 0.0,
            'corriente': 0.0,
            'estado': 'error',
            'conectado': False,
            'error': str(e)
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
    Obtiene el estado de los paneles solares y carga del controlador Victron 75/15.
    Lee datos reales desde el puerto serial VE.Direct.
    Solo retorna datos reales, NO datos simulados.
    """
    try:
        # Intentar leer del Victron
        datos_victron = leer_victron()
        if datos_victron and datos_victron.get('exito'):
            datos_victron['conectado'] = True
            return datos_victron
        
        # Si falla, retornar estructura vacía indicando desconexión
        logger.warning("Victron no disponible - sin datos")
        return {
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0,
            'bateria_voltaje': 0.0,
            'bateria_corriente': 0.0,
            'estado': 'desconectado',
            'conectado': False,
            'exito': False,
            'error': datos_victron.get('error', 'No conectado') if datos_victron else 'No detectado',
            'intervalo_frame_s': None
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos solares: {e}")
        return {
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0,
            'bateria_voltaje': 0.0,
            'bateria_corriente': 0.0,
            'estado': 'error',
            'conectado': False,
            'exito': False,
            'error': str(e),
            'intervalo_frame_s': None
        }


def detectar_puerto_victron():
    """
    Detecta automáticamente el puerto serial del controlador Victron.
    Busca en /dev/ttyUSB* y /dev/ttyACM*
    
    Returns:
        str: Ruta del puerto detectado o None
    """
    import glob
    
    # Puertos comunes para Victron VE.Direct
    posibles_puertos = (
        glob.glob('/dev/ttyUSB*') + 
        glob.glob('/dev/ttyACM*') +
        glob.glob('/dev/serial/by-id/*Victron*') +
        glob.glob('/dev/serial/by-id/*VE*')
    )
    
    for puerto in posibles_puertos:
        try:
            # Intentar abrir el puerto brevemente
            with serial.Serial(puerto, 19200, timeout=0.5) as ser:
                # Leer algunas líneas para verificar formato VE.Direct
                for _ in range(10):
                    linea = ser.readline().decode('ascii', errors='ignore').strip()
                    if linea.startswith('V\t') or linea.startswith('I\t') or linea.startswith('VPV\t'):
                        logger.info(f"Victron detectado en {puerto}")
                        return puerto
        except Exception as e:
            logger.debug(f"Puerto {puerto} no es Victron: {e}")
            continue
    
    logger.warning("No se detectó controlador Victron en ningún puerto serial")
    return None


def leer_victron(puerto=None, timeout=5):
    """
    Lee datos del controlador Victron 75/15 por VE.Direct (protocolo serial).
    
    Protocolo VE.Direct:
    - Baudrate: 19200
    - Data bits: 8
    - Parity: None
    - Stop bits: 1
    - Flow control: None
    
    Formato de datos (texto ASCII):
    V    12450    (Voltaje batería en mV)
    I    5000     (Corriente batería en mA)
    VPV  18500    (Voltaje panel en mV)
    PPV  45       (Potencia panel en W)
    CS   3        (Estado de carga)
    ERR  0        (Código de error)
    LOAD ON       (Estado de carga)
    IL   0        (Corriente de carga)
    H19  456      (Energía total generada)
    H20  123      (Energía generada hoy)
    H21  456      (Máxima potencia hoy)
    H22  789      (Energía generada ayer)
    H23  234      (Máxima potencia ayer)
    Checksum X    (Checksum del bloque)
    
    Args:
        puerto (str): Puerto serial (auto-detecta si es None)
        timeout (float): Timeout de lectura en segundos (aumentado a 5s para mejor estabilidad)
    
    Returns:
        dict: Datos del Victron o None si hay error
    """
    try:
        # Auto-detectar puerto si no se especifica
        if puerto is None:
            puerto = detectar_puerto_victron()
            if puerto is None:
                return {
                    'exito': False,
                    'error': 'Puerto Victron no encontrado',
                    'panel_voltaje': 0.0,
                    'panel_corriente': 0.0,
                    'potencia': 0,
                    'bateria_voltaje': 0.0,
                    'bateria_corriente': 0.0,
                    'estado': 'desconectado'
                }
        
            # Abrir puerto serial
            with serial.Serial(puerto, 19200, timeout=timeout) as ser:
                # Limpiar buffer antes de leer
                ser.reset_input_buffer()
            
                inicio = time.time()
                datos_frame_actual = {}
                datos_frame_final = None
                checksum_t1 = None
                intervalo_frame_s = None
            
                # Leer hasta obtener al menos un bloque completo (termina con Checksum)
                # y, si es posible, medir el intervalo entre dos bloques consecutivos.
                while (time.time() - inicio) < timeout:
                    try:
                        linea = ser.readline().decode('ascii', errors='ignore').strip()
                    
                        if not linea:
                            continue
                    
                        # Dividir por tabulación
                        partes = linea.split('\t')
                        if len(partes) == 2:
                            clave, valor = partes[0], partes[1]
                            datos_frame_actual[clave] = valor
                    
                        # Si encontramos Checksum, tenemos un bloque completo
                        if linea.startswith('Checksum'):
                            if datos_frame_actual:
                                datos_frame_final = datos_frame_actual
                            if checksum_t1 is None:
                                checksum_t1 = time.time()
                                datos_frame_actual = {}
                                continue
                            else:
                                checksum_t2 = time.time()
                                intervalo_frame_s = checksum_t2 - checksum_t1
                                break
                
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        logger.debug(f"Error leyendo línea Victron: {e}")
                        continue
            
                datos = datos_frame_final or datos_frame_actual
            
                # Verificar que recibimos datos mínimos
                if not datos or 'V' not in datos:
                    logger.warning("Victron: Bloque de datos incompleto")
                    return {
                        'exito': False,
                        'error': 'Datos incompletos o timeout',
                        'panel_voltaje': 0.0,
                        'panel_corriente': 0.0,
                        'potencia': 0,
                        'bateria_voltaje': 0.0,
                        'bateria_corriente': 0.0,
                        'estado': 'error',
                        'intervalo_frame_s': None
                    }
            
                # Convertir datos a formato usable
                resultado = parsear_datos_victron(datos)
                resultado['exito'] = True
                resultado['puerto'] = puerto
                resultado['intervalo_frame_s'] = intervalo_frame_s
            
                return resultado
    
    except serial.SerialException as e:
        logger.error(f"Error serial Victron: {e}")
        return {
            'exito': False,
            'error': f'Error serial: {str(e)}',
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0,
            'bateria_voltaje': 0.0,
            'estado': 'error',
            'intervalo_frame_s': None
        }
    except Exception as e:
        logger.error(f"Error leyendo Victron: {e}")
        return {
            'exito': False,
            'error': str(e),
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0,
            'bateria_voltaje': 0.0,
            'estado': 'error',
            'intervalo_frame_s': None
        }


def parsear_datos_victron(datos):
    """
    Convierte los datos raw del Victron a formato legible.
    
    Args:
        datos (dict): Datos raw del Victron (claves como 'V', 'I', 'VPV', etc.)
    
    Returns:
        dict: Datos parseados con unidades correctas
    """
    try:
        # Estados de carga del Victron
        estados_carga = {
            '0': 'apagado',
            '2': 'falla',
            '3': 'bulk',
            '4': 'absorption',
            '5': 'float',
            '7': 'equalize',
            '252': 'external_control'
        }
        
        # Voltaje batería (mV a V)
        bateria_voltaje = float(datos.get('V', 0)) / 1000.0
        
        # Corriente batería (mA a A) - puede ser negativa
        bateria_corriente = float(datos.get('I', 0)) / 1000.0
        
        # Voltaje panel (mV a V)
        panel_voltaje = float(datos.get('VPV', 0)) / 1000.0
        
        # Potencia panel (W)
        potencia_panel = int(datos.get('PPV', 0))
        
        # Calcular corriente panel aproximada (P = V × I)
        if panel_voltaje > 0:
            panel_corriente = potencia_panel / panel_voltaje
        else:
            panel_corriente = 0.0
        
        # Estado de carga
        estado_code = datos.get('CS', '0')
        estado = estados_carga.get(estado_code, 'desconocido')
        
        # Código de error
        error_code = int(datos.get('ERR', 0))
        
        # Yield today (Wh generados hoy)
        yield_today = int(datos.get('H20', 0))
        
        # Potencia máxima hoy (W)
        max_power_today = int(datos.get('H21', 0))
        
        # Yield total (kWh × 10)
        yield_total = float(datos.get('H19', 0)) / 10.0
        
        # Yield ayer (Wh)
        yield_ayer = int(datos.get('H22', 0))
        
        # Potencia máxima ayer (W)
        max_power_ayer = int(datos.get('H23', 0))
        
        # Calcular porcentaje de batería basado en voltaje (estimación)
        # Rango típico batería LiFePO4: 10V (0%) - 14.2V (100%)
        # Rango típico batería SLA/AGM: 11.5V (0%) - 13.8V (100%)
        # Usamos rango genérico: 10V-14V
        min_voltaje = 10.0
        max_voltaje = 14.0
        porcentaje_bateria = max(0, min(100, int((bateria_voltaje - min_voltaje) / (max_voltaje - min_voltaje) * 100)))
        
        logger.info(f"Victron: Panel {panel_voltaje:.1f}V {panel_corriente:.2f}A ({potencia_panel}W), "
                   f"Batería {bateria_voltaje:.1f}V {bateria_corriente:.2f}A ({porcentaje_bateria}%), Estado: {estado}")
        
        return {
            'panel_voltaje': round(panel_voltaje, 2),
            'panel_corriente': round(panel_corriente, 2),
            'potencia': potencia_panel,
            'bateria_voltaje': round(bateria_voltaje, 2),
            'bateria_corriente': round(bateria_corriente, 2),
            'porcentaje': porcentaje_bateria,
            'estado': estado,
            'error_code': error_code,
            'yield_today': yield_today,
            'yield_total': yield_total,
            'max_power_today': max_power_today,
            'yield_ayer': yield_ayer,
            'max_power_ayer': max_power_ayer,
            'cargando': potencia_panel > 0,
            'raw_data': datos
        }
    
    except Exception as e:
        logger.error(f"Error parseando datos Victron: {e}")
        return {
            'panel_voltaje': 0.0,
            'panel_corriente': 0.0,
            'potencia': 0,
            'bateria_voltaje': 0.0,
            'bateria_corriente': 0.0,
            'estado': 'error',
            'error': str(e)
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


def obtener_wifi():
    """
    Obtiene el estado de la conexión WiFi (SSID, RSSI dBm y calidad %).
    Usa nmcli como método principal (más confiable en Raspberry Pi).
    """
    try:
        # Método principal: nmcli dev wifi list (más confiable)
        try:
            res = subprocess.run(
                ['nmcli', 'dev', 'wifi', 'list', '--rescan', 'no'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                out = res.stdout
                ssid = ''
                calidad = None
                rssi = None
                
                # Buscar la primera línea con SSID (la red conectada tiene asterisco *)
                # Formato: BSSID  SSID  IN FRA  CHAN  RATE  SIGNAL  BARS  SECURITY
                import re
                lineas = out.split('\n')
                
                # Buscar red conectada (con asterisco) primero
                for linea in lineas:
                    if '*' in linea:  # Red conectada
                        # Extraer campos usando regex
                        # Formato aproximado: AA:BB:CC:DD:EE:FF  SSID  ...  SIGNAL(0-100)
                        partes = linea.split()
                        if len(partes) >= 7:
                            try:
                                # El campo de signal está típicamente en posición 6
                                calidad = int(partes[6])
                                # Extraer SSID (entre BSSID y los siguientes campos)
                                # SSID empieza después del BSSID
                                for i, parte in enumerate(partes):
                                    if ':' in parte and len(parte.split(':')) == 6:  # Es un MAC
                                        if i + 1 < len(partes):
                                            ssid = partes[i + 1]
                                        break
                                
                                if calidad and calidad > 0:
                                    # Convertir porcentaje a dBm (aproximado)
                                    rssi = int(calidad / 2 - 100)
                                    logger.info(f"WiFi (nmcli) - SSID: {ssid}, Calidad: {calidad}%, RSSI: {rssi} dBm")
                                    return {'ssid': ssid or '', 'rssi_dbm': rssi, 'calidad': int(calidad)}
                            except (ValueError, IndexError) as e:
                                logger.debug(f"Error parseando línea WiFi: {e}")
                                continue
                
                # Si no encontró red conectada, buscar cualquier red con calidad > 0
                for linea in lineas:
                    if linea.strip() and not linea.startswith('BSSID'):
                        partes = linea.split()
                        if len(partes) >= 7:
                            try:
                                calidad = int(partes[6])
                                if calidad and calidad > 0:
                                    for i, parte in enumerate(partes):
                                        if ':' in parte and len(parte.split(':')) == 6:
                                            if i + 1 < len(partes):
                                                ssid = partes[i + 1]
                                            break
                                    rssi = int(calidad / 2 - 100)
                                    logger.info(f"WiFi (nmcli fallback) - SSID: {ssid}, Calidad: {calidad}%, RSSI: {rssi} dBm")
                                    return {'ssid': ssid or '', 'rssi_dbm': rssi, 'calidad': int(calidad)}
                            except (ValueError, IndexError):
                                continue
        except FileNotFoundError:
            logger.debug("Comando 'nmcli' no encontrado")
        except Exception as e:
            logger.debug(f"Error con nmcli: {e}")
        
        # Método alternativo: wpa_cli
        try:
            res = subprocess.run(
                ['wpa_cli', 'signal_poll'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if res.returncode == 0:
                out = res.stdout
                rssi = None
                
                import re
                # RSSI en formato: RSSI=-40
                rssi_match = re.search(r'RSSI=(-?\d+)', out)
                if rssi_match:
                    rssi = int(rssi_match.group(1))
                    if rssi and rssi < 0:
                        calidad = max(0, min(100, 2 * (rssi + 100)))
                        if calidad > 0:
                            logger.info(f"WiFi (wpa_cli) - RSSI: {rssi} dBm, Calidad: {calidad}%")
                            return {'ssid': '', 'rssi_dbm': rssi, 'calidad': int(calidad)}
        except (FileNotFoundError, Exception) as e:
            logger.debug(f"wpa_cli no disponible: {e}")
        
    except Exception as e:
        logger.warning(f"Error obteniendo WiFi: {e}")
    
    logger.warning("No se pudo obtener información WiFi")
    return {'ssid': '', 'rssi_dbm': None, 'calidad': None}


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
            'latitud': GPS_DATOS['latitud'],
            'longitud': GPS_DATOS['longitud'],
            'altitud': GPS_DATOS['altitud'],
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
        from base_de_datos.base_datos import iniciar_recorrido, guardar_posicion_gps as guardar_posicion_bd
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
