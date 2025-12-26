#!/usr/bin/env python3
"""
Gestor de pipelines FFmpeg para convertir RTSP a HLS y reproducir en la web.
"""
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
PROCESOS = { 'cam1': None, 'cam2': None }

BASE_DIR = Path(__file__).parent
HLS_BASE = BASE_DIR / 'hls'


def asegurar_carpetas():
    try:
        (HLS_BASE / 'cam1').mkdir(parents=True, exist_ok=True)
        (HLS_BASE / 'cam2').mkdir(parents=True, exist_ok=True)
        logger.info("Carpetas HLS aseguradas en %s", HLS_BASE)
    except Exception as e:
        logger.error("No se pudo crear carpetas HLS: %s", e)


def construir_rtsp_url(cfg: dict, cam_index: int, calidad: str = 'sd') -> str:
    """Obtiene la URL RTSP completa según la calidad (sd o hd)"""
    if calidad.lower() in ['hd', '2k']:
        url = (cfg.get(f'url_camara{cam_index}_hd') or '').strip()
    else:
        url = (cfg.get(f'url_camara{cam_index}_sd') or '').strip()
    
    # Si no hay URL HD, usar SD como fallback
    if not url and calidad.lower() in ['hd', '2k']:
        url = (cfg.get(f'url_camara{cam_index}_sd') or '').strip()
    
    # Verificar si la cámara está desactivada
    desactivar = bool(cfg.get(f'desactivar_camara{cam_index}', False))
    if desactivar:
        return ''
    
    return url


def iniciar_hls(camara: str, rtsp_url: str) -> bool:
    """Inicia ffmpeg para convertir RTSP a HLS en hls/<camara>/<camara>.m3u8"""
    if not rtsp_url:
        logger.info("%s: RTSP no definido/desactivado", camara)
        return False

    asegurar_carpetas()

    salida = HLS_BASE / camara / f'{camara}.m3u8'
    cmd = [
        'ffmpeg', '-nostdin', '-rtsp_transport', 'tcp', '-i', rtsp_url,
        '-map', '0:v:0', '-c:v', 'copy', '-f', 'hls',
        '-hls_time', '2', '-hls_list_size', '10', '-hls_flags', 'delete_segments+omit_endlist',
        str(salida)
    ]

    try:
        # Si existe proceso previo, terminar
        detener_hls(camara)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        PROCESOS[camara] = proc
        logger.info("%s: FFmpeg iniciado (PID=%s) → %s", camara, proc.pid, salida)
        return True
    except FileNotFoundError:
        logger.error("ffmpeg no encontrado. Instala con: sudo apt-get install -y ffmpeg")
        return False
    except Exception as e:
        logger.error("%s: Error iniciando HLS: %s", camara, e)
        return False


def detener_hls(camara: str):
    proc = PROCESOS.get(camara)
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            logger.info("%s: FFmpeg terminado", camara)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    PROCESOS[camara] = None


def detener_todos():
    detener_hls('cam1')
    detener_hls('cam2')
