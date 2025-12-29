#!/usr/bin/env python3
"""
MÓDULO DE BASE DE DATOS SQLITE
Gestiona la persistencia de configuración y recorridos GPS del drone acuático.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logger = logging.getLogger(__name__)

# Ruta de la base de datos
DB_PATH = Path(__file__).parent / 'drone-acuatico.db'


def obtener_conexion():
    """
    Obtiene una conexión con la base de datos SQLite.
    
    Returns:
        sqlite3.Connection: Conexión a la base de datos
    """
    try:
        conexion = sqlite3.connect(str(DB_PATH))
        conexion.row_factory = sqlite3.Row
        return conexion
    except sqlite3.Error as e:
        logger.error(f"Error conectando a base de datos: {e}")
        return None


def inicializar_bd():
    """
    Inicializa la base de datos creando las tablas si no existen.
    Se ejecuta una sola vez al iniciar el servidor.
    """
    conexion = obtener_conexion()
    if not conexion:
        logger.error("No se pudo inicializar la base de datos")
        return False
    
    try:
        cursor = conexion.cursor()
        
        # Tabla de CONFIGURACIÓN
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY,
                ip_publica TEXT,
                solicitar_password INTEGER DEFAULT 0,
                correo TEXT,
                password_hash TEXT,
                tamano_mapa INTEGER DEFAULT 400,
                guardar_recorrido INTEGER DEFAULT 1,
                frecuencia_guardado INTEGER DEFAULT 30,
                url_camara1_sd TEXT,
                url_camara1_hd TEXT,
                desactivar_camara1 INTEGER DEFAULT 0,
                url_camara2_sd TEXT,
                url_camara2_hd TEXT,
                desactivar_camara2 INTEGER DEFAULT 0,
                nombre_rele1 TEXT DEFAULT 'Relé 1',
                nombre_rele2 TEXT DEFAULT 'Relé 2',
                nombre_rele3 TEXT DEFAULT 'Relé 3',
                nombre_rele4 TEXT DEFAULT 'Relé 4',
                nombre_rele5 TEXT DEFAULT 'Relé 5',
                nombre_rele6 TEXT DEFAULT 'Relé 6',
                nombre_rele7 TEXT DEFAULT 'Relé 7',
                nombre_rele8 TEXT DEFAULT 'Relé 8',
                nombre_rele9 TEXT DEFAULT 'Relé 9',
                tema_oscuro INTEGER DEFAULT 1,
                tamano_letra_datos INTEGER DEFAULT 12,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de RECORRIDOS GPS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recorridos_gps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_fin TIMESTAMP,
                distancia_km REAL DEFAULT 0,
                puntos_json TEXT,
                activo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabla de POSICIONES GPS (puntos individuales del recorrido)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posiciones_gps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorrido_id INTEGER NOT NULL,
                latitud REAL,
                longitud REAL,
                altitud REAL,
                velocidad REAL,
                satelites INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recorrido_id) REFERENCES recorridos_gps(id)
            )
        ''')
        
        # Tabla de ESTADO DE RELÉS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS estado_reles (
                id INTEGER PRIMARY KEY,
                numero INTEGER UNIQUE,
                estado INTEGER DEFAULT 0,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conexion.commit()
        
        # Asegurar columnas nuevas en BD existente (migración)
        # Migraciones de columnas nuevas (silenciosas si ya existen)
        for stmt in [
            "ALTER TABLE configuracion ADD COLUMN url_camara1_sd TEXT",
            "ALTER TABLE configuracion ADD COLUMN url_camara1_hd TEXT",
            "ALTER TABLE configuracion ADD COLUMN url_camara2_sd TEXT",
            "ALTER TABLE configuracion ADD COLUMN url_camara2_hd TEXT",
            "ALTER TABLE configuracion ADD COLUMN tema_oscuro INTEGER DEFAULT 1",
            "ALTER TABLE configuracion ADD COLUMN tamano_letra_datos INTEGER DEFAULT 12",
            "ALTER TABLE configuracion ADD COLUMN frecuencia_guardado INTEGER DEFAULT 30",
        ]:
            try:
                cursor.execute(stmt)
            except sqlite3.Error:
                pass
        conexion.commit()
        logger.info("Base de datos inicializada correctamente")
        
        # Crear configuración por defecto si no existe
        cursor.execute('SELECT COUNT(*) FROM configuracion')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO configuracion (ip_publica) VALUES (?)
            ''', ('192.168.1.7',))
            conexion.commit()
            logger.info("Configuración por defecto creada")
        
        # Inicializar estado de los 9 relés si no existen
        cursor.execute('SELECT COUNT(*) FROM estado_reles')
        if cursor.fetchone()[0] == 0:
            for i in range(1, 10):
                cursor.execute('''
                    INSERT INTO estado_reles (numero, estado) VALUES (?, ?)
                ''', (i, 0))
            conexion.commit()
            logger.info("Estados de relés inicializados (todos apagados)")
        
        # Crear entradas de relés si no existen
        for i in range(1, 10):
            cursor.execute('INSERT OR IGNORE INTO estado_reles (numero, estado) VALUES (?, ?)', (i, 0))
        conexion.commit()
        
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error inicializando base de datos: {e}")
        return False
    
    finally:
        conexion.close()


# ==================== FUNCIONES DE CONFIGURACIÓN ====================

def obtener_configuracion():
    """
    Obtiene toda la configuración del drone desde la base de datos.
    
    Returns:
        dict: Diccionario con toda la configuración
    """
    conexion = obtener_conexion()
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute('SELECT * FROM configuracion LIMIT 1')
        fila = cursor.fetchone()
        
        if fila:
            config = {
                'id': fila['id'],
                'ip_publica': fila['ip_publica'],
                'solicitar_password': bool(fila['solicitar_password']),
                'correo': fila['correo'],
                'tamano_mapa': fila['tamano_mapa'],
                'guardar_recorrido': bool(fila['guardar_recorrido']),
                'url_camara1_sd': fila['url_camara1_sd'] if 'url_camara1_sd' in fila.keys() else '',
                'url_camara1_hd': fila['url_camara1_hd'] if 'url_camara1_hd' in fila.keys() else '',
                'desactivar_camara1': bool(fila['desactivar_camara1']),
                'url_camara2_sd': fila['url_camara2_sd'] if 'url_camara2_sd' in fila.keys() else '',
                'url_camara2_hd': fila['url_camara2_hd'] if 'url_camara2_hd' in fila.keys() else '',
                'desactivar_camara2': bool(fila['desactivar_camara2']),
                'tamano_letra_datos': int(fila['tamano_letra_datos']) if 'tamano_letra_datos' in fila.keys() else 12,
                'reles': {
                    1: fila['nombre_rele1'],
                    2: fila['nombre_rele2'],
                    3: fila['nombre_rele3'],
                    4: fila['nombre_rele4'],
                    5: fila['nombre_rele5'],
                    6: fila['nombre_rele6'],
                    7: fila['nombre_rele7'],
                    8: fila['nombre_rele8'],
                    9: fila['nombre_rele9']
                }
            }
            return config
        return None
    
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo configuración: {e}")
        return None
    
    finally:
        conexion.close()


def guardar_configuracion(config):
    """
    Guarda la configuración en la base de datos.
    
    Args:
        config (dict): Diccionario con los datos de configuración
    
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    conexion = obtener_conexion()
    if not conexion:
        return False
    
    try:
        # Normalizar nombres de relés: admitir claves '1'..'9' (strings) o enteros
        reles_cfg = config.get('reles', {}) or {}
        try:
            reles_normalizados = {int(str(k)): (v or '').strip() for k, v in reles_cfg.items() if str(k).isdigit()}
        except Exception:
            reles_normalizados = {}

        cursor = conexion.cursor()
        cursor.execute('''
            UPDATE configuracion SET
                ip_publica = ?,
                solicitar_password = ?,
                correo = ?,
                tamano_mapa = ?,
                tamano_letra_datos = ?,
                guardar_recorrido = ?,
                url_camara1_sd = ?,
                url_camara1_hd = ?,
                desactivar_camara1 = ?,
                url_camara2_sd = ?,
                url_camara2_hd = ?,
                desactivar_camara2 = ?,
                nombre_rele1 = ?,
                nombre_rele2 = ?,
                nombre_rele3 = ?,
                nombre_rele4 = ?,
                nombre_rele5 = ?,
                nombre_rele6 = ?,
                nombre_rele7 = ?,
                nombre_rele8 = ?,
                nombre_rele9 = ?,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (
            config.get('ip_publica', ''),
            int(config.get('solicitar_password', False)),
            config.get('correo', ''),
            int(config.get('tamano_mapa', 400)),
            int(config.get('tamano_letra_datos', 12)),
            int(config.get('guardar_recorrido', True)),
            config.get('url_camara1_sd', ''),
            config.get('url_camara1_hd', ''),
            int(config.get('desactivar_camara1', False)),
            config.get('url_camara2_sd', ''),
            config.get('url_camara2_hd', ''),
            int(config.get('desactivar_camara2', False)),
            reles_normalizados.get(1, 'Relé 1') or 'Relé 1',
            reles_normalizados.get(2, 'Relé 2') or 'Relé 2',
            reles_normalizados.get(3, 'Relé 3') or 'Relé 3',
            reles_normalizados.get(4, 'Relé 4') or 'Relé 4',
            reles_normalizados.get(5, 'Relé 5') or 'Relé 5',
            reles_normalizados.get(6, 'Relé 6') or 'Relé 6',
            reles_normalizados.get(7, 'Relé 7') or 'Relé 7',
            reles_normalizados.get(8, 'Relé 8') or 'Relé 8',
            reles_normalizados.get(9, 'Relé 9') or 'Relé 9'
        ))
        
        conexion.commit()
        logger.info("Configuración guardada correctamente")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error guardando configuración: {e}")
        return False
    
    finally:
        conexion.close()


# ==================== FUNCIONES DE RECORRIDOS GPS ====================

def iniciar_recorrido(nombre='Recorrido sin título'):
    """
    Inicia un nuevo recorrido GPS.
    
    Args:
        nombre (str): Nombre del recorrido
    
    Returns:
        int: ID del recorrido creado, o None si hay error
    """
    conexion = obtener_conexion()
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute('''
            INSERT INTO recorridos_gps (nombre, activo)
            VALUES (?, 1)
        ''', (nombre,))
        conexion.commit()
        recorrido_id = cursor.lastrowid
        logger.info(f"Recorrido GPS iniciado: ID={recorrido_id}, Nombre={nombre}")
        return recorrido_id
    
    except sqlite3.Error as e:
        logger.error(f"Error iniciando recorrido: {e}")
        return None
    
    finally:
        conexion.close()


def finalizar_recorrido(recorrido_id):
    """
    Finaliza un recorrido GPS.
    
    Args:
        recorrido_id (int): ID del recorrido a finalizar
    
    Returns:
        bool: True si se finalizó correctamente
    """
    conexion = obtener_conexion()
    if not conexion:
        return False
    
    try:
        cursor = conexion.cursor()
        cursor.execute('''
            UPDATE recorridos_gps
            SET activo = 0, fecha_fin = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (recorrido_id,))
        conexion.commit()
        logger.info(f"Recorrido GPS finalizado: ID={recorrido_id}")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error finalizando recorrido: {e}")
        return False
    
    finally:
        conexion.close()


def guardar_posicion_gps(recorrido_id, latitud, longitud, altitud=0, velocidad=0, satelites=0):
    """
    Guarda una posición GPS en un recorrido.
    
    Args:
        recorrido_id (int): ID del recorrido
        latitud (float): Latitud
        longitud (float): Longitud
        altitud (float): Altitud en metros
        velocidad (float): Velocidad en km/h
        satelites (int): Número de satélites
    
    Returns:
        int: ID de la posición guardada, o None si hay error
    """
    conexion = obtener_conexion()
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        cursor.execute('''
            INSERT INTO posiciones_gps 
            (recorrido_id, latitud, longitud, altitud, velocidad, satelites)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (recorrido_id, latitud, longitud, altitud, velocidad, satelites))
        conexion.commit()
        return cursor.lastrowid
    
    except sqlite3.Error as e:
        logger.error(f"Error guardando posición GPS: {e}")
        return None
    
    finally:
        conexion.close()


def obtener_recorrido(recorrido_id):
    """
    Obtiene un recorrido completo con todas sus posiciones.
    
    Args:
        recorrido_id (int): ID del recorrido
    
    Returns:
        dict: Diccionario con datos del recorrido y posiciones
    """
    conexion = obtener_conexion()
    if not conexion:
        return None
    
    try:
        cursor = conexion.cursor()
        
        # Obtener datos del recorrido
        cursor.execute('SELECT * FROM recorridos_gps WHERE id = ?', (recorrido_id,))
        recorrido = cursor.fetchone()
        
        if not recorrido:
            return None
        
        # Obtener posiciones del recorrido
        cursor.execute('''
            SELECT latitud, longitud, altitud, velocidad, satelites, timestamp
            FROM posiciones_gps
            WHERE recorrido_id = ?
            ORDER BY timestamp ASC
        ''', (recorrido_id,))
        
        posiciones = [
            {
                'latitud': row['latitud'],
                'longitud': row['longitud'],
                'altitud': row['altitud'],
                'velocidad': row['velocidad'],
                'satelites': row['satelites'],
                'timestamp': row['timestamp']
            }
            for row in cursor.fetchall()
        ]
        
        return {
            'id': recorrido['id'],
            'nombre': recorrido['nombre'],
            'fecha_inicio': recorrido['fecha_inicio'],
            'fecha_fin': recorrido['fecha_fin'],
            'activo': bool(recorrido['activo']),
            'posiciones': posiciones
        }
    
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo recorrido: {e}")
        return None
    
    finally:
        conexion.close()


def obtener_todos_recorridos(activos_solo=False):
    """
    Obtiene lista de todos los recorridos.
    
    Args:
        activos_solo (bool): Si True, solo devuelve recorridos activos
    
    Returns:
        list: Lista de recorridos
    """
    conexion = obtener_conexion()
    if not conexion:
        return []
    
    try:
        cursor = conexion.cursor()
        
        if activos_solo:
            cursor.execute('''
                SELECT id, nombre, fecha_inicio, fecha_fin, activo
                FROM recorridos_gps
                WHERE activo = 1
                ORDER BY fecha_inicio DESC
            ''')
        else:
            cursor.execute('''
                SELECT id, nombre, fecha_inicio, fecha_fin, activo
                FROM recorridos_gps
                ORDER BY fecha_inicio DESC
            ''')
        
        recorridos = [
            {
                'id': row['id'],
                'nombre': row['nombre'],
                'fecha_inicio': row['fecha_inicio'],
                'fecha_fin': row['fecha_fin'],
                'activo': bool(row['activo'])
            }
            for row in cursor.fetchall()
        ]
        
        return recorridos
    
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo recorridos: {e}")
        return []
    
    finally:
        conexion.close()


def eliminar_recorrido(recorrido_id):
    """
    Elimina un recorrido y todas sus posiciones.
    
    Args:
        recorrido_id (int): ID del recorrido a eliminar
    
    Returns:
        bool: True si se eliminó correctamente
    """
    conexion = obtener_conexion()
    if not conexion:
        return False
    
    try:
        cursor = conexion.cursor()
        
        # Eliminar posiciones primero (por clave foránea)
        cursor.execute('DELETE FROM posiciones_gps WHERE recorrido_id = ?', (recorrido_id,))
        
        # Eliminar recorrido
        cursor.execute('DELETE FROM recorridos_gps WHERE id = ?', (recorrido_id,))
        
        conexion.commit()
        logger.info(f"Recorrido eliminado: ID={recorrido_id}")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error eliminando recorrido: {e}")
        return False
    
    finally:
        conexion.close()


# ==================== FUNCIONES DE ESTADO DE RELÉS ====================

def obtener_estado_reles():
    """
    Obtiene el estado de todos los relés.
    
    Returns:
        dict: Diccionario con número de relé como clave y estado como valor
    """
    conexion = obtener_conexion()
    if not conexion:
        return {}
    
    try:
        cursor = conexion.cursor()
        cursor.execute('SELECT numero, estado FROM estado_reles ORDER BY numero')
        
        estados = {row['numero']: bool(row['estado']) for row in cursor.fetchall()}
        return estados
    
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo estado de relés: {e}")
        return {}
    
    finally:
        conexion.close()


def guardar_estado_rele(numero, estado):
    """
    Guarda el estado de un relé.
    
    Args:
        numero (int): Número del relé (1-9)
        estado (int): Estado del relé (0 o 1)
    
    Returns:
        bool: True si se guardó correctamente
    """
    conexion = obtener_conexion()
    if not conexion:
        return False
    
    try:
        cursor = conexion.cursor()
        cursor.execute('''
            INSERT INTO estado_reles (numero, estado, fecha_actualizacion)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(numero) DO UPDATE SET
                estado = excluded.estado,
                fecha_actualizacion = CURRENT_TIMESTAMP
        ''', (numero, int(estado)))
        conexion.commit()
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error guardando estado de relé: {e}")
        return False
    
    finally:
        conexion.close()


def restaurar_estados_reles():
    """
    Restaura los estados de todos los relés desde la base de datos.
    
    Returns:
        dict: Diccionario con número de relé como clave y estado como valor
              Ej: {1: True, 2: False, 3: True, ...}
    """
    estados = obtener_estado_reles()
    
    # Si no hay estados guardados, inicializar todos como apagados
    if not estados:
        return {i: False for i in range(1, 10)}
    
    # Asegurar que existen todos los 9 relés
    for i in range(1, 10):
        if i not in estados:
            estados[i] = False
    
    logger.info(f"Estados de relés restaurados desde BD: {estados}")
    return estados


def obtener_tema():
    """
    Obtiene el tema guardado en la configuración.
    
    Returns:
        str: 'oscuro' o 'claro'
    """
    conexion = obtener_conexion()
    if not conexion:
        return 'oscuro'  # Por defecto oscuro
    
    try:
        cursor = conexion.cursor()
        cursor.execute('SELECT tema_oscuro FROM configuracion WHERE id = 1')
        resultado = cursor.fetchone()
        
        if resultado:
            return 'oscuro' if resultado['tema_oscuro'] else 'claro'
        return 'oscuro'
    
    except sqlite3.Error as e:
        logger.error(f"Error obteniendo tema: {e}")
        return 'oscuro'
    
    finally:
        conexion.close()


def guardar_tema(tema_oscuro):
    """
    Guarda el tema en la configuración.
    
    Args:
        tema_oscuro (bool): True para modo oscuro, False para modo claro
    
    Returns:
        bool: True si se guardó correctamente
    """
    conexion = obtener_conexion()
    if not conexion:
        return False
    
    try:
        cursor = conexion.cursor()
        cursor.execute('''
            UPDATE configuracion
            SET tema_oscuro = ?, fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (1 if tema_oscuro else 0,))
        conexion.commit()
        logger.info(f"Tema guardado: {'oscuro' if tema_oscuro else 'claro'}")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Error guardando tema: {e}")
        return False
    
    finally:
        conexion.close()
