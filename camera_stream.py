#!/usr/bin/env python3
"""
Módulo para manejo de streaming de cámaras RTSP → HLS con ffmpeg.
Provee utilidades que usa el servidor:
- asegurar_carpetas()
- construir_rtsp_url(config, indice, calidad)
- iniciar_hls(cam_id, url_rtsp)
- detener_hls(cam_id)
- detener_todos()
"""

import logging
import os
import time
from pathlib import Path
import shutil
import signal
import subprocess
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Configuración
HLS_OUTPUT_DIR = Path(__file__).parent / "hls"
HLS_PLAYLIST_NAME = {
    "cam1": "cam1.m3u8",
    "cam2": "cam2.m3u8",
}

# Registro de procesos ffmpeg por cámara
PROCESOS: Dict[str, subprocess.Popen] = {}

def asegurar_carpetas():
    """Crea las carpetas necesarias para HLS."""
    try:
        HLS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        for cam in ("cam1", "cam2"):
            (HLS_OUTPUT_DIR / cam).mkdir(parents=True, exist_ok=True)
        logger.info("✓ Carpetas HLS listas")
        return True
    except Exception as e:
        logger.error(f"✗ Error creando carpetas HLS: {e}")
        return False

def construir_rtsp_url(config: dict, indice: int, calidad: str = "sd") -> Optional[str]:
    """Devuelve la URL RTSP desde la configuración.

    Args:
        config: Diccionario de configuración (desde base_datos.obtener_configuracion()).
        indice: 1 o 2 para seleccionar cámara.
        calidad: "sd" o "hd" para escoger el campo adecuado.

    Returns:
        URL RTSP normalizada (con prefijo rtsp://) o None si no hay.
    """
    try:
        if not config:
            return None
        calidad = (calidad or "sd").lower()
        if indice == 1:
            key = "url_camara1_hd" if calidad == "hd" else "url_camara1_sd"
        else:
            key = "url_camara2_hd" if calidad == "hd" else "url_camara2_sd"
        url = (config.get(key) or "").strip()
        if not url:
            return None
        if not url.startswith("rtsp://"):
            url = f"rtsp://{url}"
        return url
    except Exception as e:
        logger.error(f"✗ Error construyendo URL RTSP: {e}")
        return None

def _resolver_cam_id(indice_o_id) -> Optional[str]:
    if isinstance(indice_o_id, str):
        if indice_o_id in ("cam1", "cam2"):
            return indice_o_id
        return None
    try:
        i = int(indice_o_id)
        return "cam1" if i == 1 else ("cam2" if i == 2 else None)
    except Exception:
        return None


def _limpiar_salida(cam_id: str) -> None:
    carpeta = HLS_OUTPUT_DIR / cam_id
    try:
        for p in carpeta.glob("*.ts"):
            p.unlink(missing_ok=True)
        for p in carpeta.glob("*.m3u8"):
            p.unlink(missing_ok=True)
    except Exception:
        pass


def iniciar_hls(indice_o_id, url_rtsp: Optional[str]) -> Tuple[bool, str]:
    """Inicia un proceso ffmpeg que convierte RTSP a HLS.

    Args:
        indice_o_id: 1/2 o "cam1"/"cam2".
        url_rtsp: URL RTSP completa.

    Returns:
        (exito, mensaje)
    """
    cam_id = _resolver_cam_id(indice_o_id)
    if not cam_id:
        logger.error(f"✗ Identificador de cámara inválido: {indice_o_id}")
        return False, "Identificador de cámara inválido"

    try:
        if not url_rtsp:
            logger.warning(f"⚠ URL RTSP vacía para {cam_id}")
            return False, "URL RTSP vacía"

        # Verificar ffmpeg
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            logger.error("✗ ffmpeg no encontrado en el sistema. Instálelo para HLS.")
            return False, "ffmpeg no encontrado en el sistema"

        asegurar_carpetas()

        # Detener si ya hay uno
        if cam_id in PROCESOS:
            detener_hls(cam_id)

        carpeta = HLS_OUTPUT_DIR / cam_id
        _limpiar_salida(cam_id)

        playlist_path = carpeta / HLS_PLAYLIST_NAME.get(cam_id, f"{cam_id}.m3u8")
        segment_pattern = carpeta / f"{cam_id}_%03d.ts"

        # Comando ffmpeg: copiar video para baja carga en la Raspberry
        cmd = [
            ffmpeg,
            "-nostdin",
            "-loglevel", "error",
            "-rtsp_transport", "tcp",
            "-i", url_rtsp,
            "-an",  # descartar audio para simplificar
            "-c:v", "copy",
            "-f", "hls",
            "-hls_time", "2",
            "-hls_list_size", "5",
            "-hls_flags", "delete_segments+program_date_time+append_list",
            "-hls_segment_filename", str(segment_pattern),
            str(playlist_path),
        ]

        proc = subprocess.Popen(cmd)
        PROCESOS[cam_id] = proc
        logger.info(f"✓ Iniciando HLS {cam_id} desde {url_rtsp} (PID {proc.pid})")

        # Validación rápida: proceso vivo y playlist creada
        playlist_path = carpeta / HLS_PLAYLIST_NAME.get(cam_id, f"{cam_id}.m3u8")
        for _ in range(6):  # ~3s
            time.sleep(0.5)
            if proc.poll() is not None:
                PROCESOS.pop(cam_id, None)
                logger.error(f"✗ ffmpeg terminó temprano para {cam_id} (código {proc.returncode})")
                return False, "No se pudo abrir el RTSP (proceso terminó)"
            if playlist_path.exists() and playlist_path.stat().st_size > 0:
                return True, "HLS iniciado"

        # Si sigue vivo pero sin playlist, consideramos que sigue en progreso
        return True, "HLS iniciado (validación pendiente)"
    except Exception as e:
        logger.error(f"✗ Error iniciando HLS para {cam_id}: {e}")
        return False, str(e)

def detener_hls(indice_o_id) -> bool:
    """Detiene el ffmpeg de una cámara y libera recursos."""
    cam_id = _resolver_cam_id(indice_o_id)
    if not cam_id:
        return False
    try:
        proc = PROCESOS.get(cam_id)
        if not proc:
            return True
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        finally:
            PROCESOS.pop(cam_id, None)
        logger.info(f"✓ HLS detenido para {cam_id}")
        return True
    except Exception as e:
        logger.error(f"✗ Error deteniendo HLS para {cam_id}: {e}")
        return False

def detener_todos() -> bool:
    """Detiene todos los procesos ffmpeg activos."""
    ok = True
    for cam_id in list(PROCESOS.keys()):
        ok = detener_hls(cam_id) and ok
    return ok

if __name__ == "__main__":
    asegurar_carpetas()
    print("✓ camera_stream.py cargado correctamente")
