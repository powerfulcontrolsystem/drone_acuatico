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
    """Devuelve la primera URL RTSP candidata para compatibilidad hacia atrás.

    Mantiene la firma antigua, pero ahora delega a `construir_rtsp_candidatos`
    y devuelve únicamente la primera URL disponible.
    """
    candidatos = construir_rtsp_candidatos(config, indice)
    return candidatos[0] if candidatos else None


def construir_rtsp_candidatos(config: dict, indice: int) -> list[str]:
    """Construye una lista de URLs RTSP a partir de los parámetros ONVIF o URL completa.

    - Si existe rtsp_camaraN_url, la usa directamente como primera candidata.
    - Si no, construye URLs desde host/puerto/usuario/contraseña/perfil ONVIF.
    - Genera candidatos probando puertos habituales: 554 (RTSP) y el puerto
      ONVIF indicado (por defecto 8899) si es diferente.
    """
    try:
        if not config:
            return []

        # Obtener URL RTSP completa si existe (prioritaria)
        url_completa = ""
        if indice == 1:
            url_completa = (config.get("rtsp_camara1_url") or "").strip()
        else:
            url_completa = (config.get("rtsp_camara2_url") or "").strip()
        
        # Si hay URL completa, usarla como primera opción
        candidatos = []
        if url_completa and url_completa.startswith("rtsp://"):
            candidatos.append(url_completa)

        # Construir URLs desde parámetros ONVIF individuales
        if indice == 1:
            host = (config.get("onvif_camara1_host") or "").strip()
            puerto_onvif = int(config.get("onvif_camara1_puerto", 8899) or 8899)
            usuario = (config.get("onvif_camara1_usuario") or "").strip()
            contrasena = config.get("onvif_camara1_contrasena") or ""
            perfil = (config.get("onvif_camara1_perfil") or "Streaming/Channels/101").strip("/")
        else:
            host = (config.get("onvif_camara2_host") or "").strip()
            puerto_onvif = int(config.get("onvif_camara2_puerto", 8899) or 8899)
            usuario = (config.get("onvif_camara2_usuario") or "").strip()
            contrasena = config.get("onvif_camara2_contrasena") or ""
            perfil = (config.get("onvif_camara2_perfil") or "Streaming/Channels/101").strip("/")

        if host:
            auth = ""
            if usuario:
                auth = usuario
                if contrasena:
                    auth += f":{contrasena}"
                auth += "@"

            puertos = [554]
            if puerto_onvif not in puertos:
                puertos.append(puerto_onvif)

            # Agregar candidatos desde parámetros ONVIF (si no están ya)
            for p in puertos:
                url = f"rtsp://{auth}{host}:{p}/{perfil}"
                if url not in candidatos:
                    candidatos.append(url)

        return candidatos
    except Exception as e:
        logger.error(f"✗ Error construyendo candidatos RTSP desde ONVIF: {e}")
        return []

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


def _iniciar_hls_single(cam_id: str, url_rtsp: str) -> Tuple[bool, str]:
    """Lanza ffmpeg para una URL específica."""
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

    cmd = [
        ffmpeg,
        "-nostdin",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",
        "-i", url_rtsp,
        "-an",
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

    for _ in range(6):
        time.sleep(0.5)
        if proc.poll() is not None:
            PROCESOS.pop(cam_id, None)
            logger.error(f"✗ ffmpeg terminó temprano para {cam_id} (código {proc.returncode})")
            return False, "No se pudo abrir el RTSP (proceso terminó)"
        if playlist_path.exists() and playlist_path.stat().st_size > 0:
            return True, "HLS iniciado"
    return True, "HLS iniciado (validación pendiente)"


def iniciar_hls(indice_o_id, url_rtsp: Optional[str | list[str]]) -> Tuple[bool, str]:
    """Inicia un proceso ffmpeg que convierte RTSP a HLS.

    Permite una lista de URLs candidatas; intentará en orden hasta que una funcione.
    """
    cam_id = _resolver_cam_id(indice_o_id)
    if not cam_id:
        logger.error(f"✗ Identificador de cámara inválido: {indice_o_id}")
        return False, "Identificador de cámara inválido"

    candidatos = []
    if isinstance(url_rtsp, (list, tuple)):
        candidatos = [u for u in url_rtsp if u]
    elif url_rtsp:
        candidatos = [url_rtsp]

    if not candidatos:
        logger.warning(f"⚠ Sin URLs RTSP candidatas para {cam_id}")
        return False, "URL RTSP vacía"

    ultimo_error = "URL RTSP no válida"
    for idx, url in enumerate(candidatos, start=1):
        try:
            ok, msg = _iniciar_hls_single(cam_id, url)
            if ok:
                if idx > 1:
                    msg = f"{msg} (usando candidato {idx})"
                return True, msg
            ultimo_error = msg
        except Exception as e:  # pragma: no cover (log de robustez)
            ultimo_error = str(e)
            logger.error(f"✗ Error iniciando HLS para {cam_id} con candidato {idx}: {e}")
    return False, ultimo_error

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
