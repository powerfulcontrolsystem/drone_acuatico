import os
from datetime import datetime
from pathlib import Path
from aiohttp import web
import base64

CAPTURAS_DIR = Path(__file__).parent / 'capturas de camaras'
CAPTURAS_DIR.mkdir(exist_ok=True)

async def capturar_foto_handler(request):
    data = await request.json()
    imagen_b64 = data.get('imagen')
    camara = data.get('camara', 'cam')
    if not imagen_b64:
        return web.json_response({'ok': False, 'error': 'No se recibió imagen'}, status=400)
    try:
        # Decodificar imagen base64
        header, b64data = imagen_b64.split(',', 1) if ',' in imagen_b64 else ('', imagen_b64)
        img_bytes = base64.b64decode(b64data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{camara}_{timestamp}.jpg'
        filepath = CAPTURAS_DIR / filename
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        return web.json_response({'ok': True, 'archivo': str(filepath.name)})
    except Exception as e:
        return web.json_response({'ok': False, 'error': str(e)}, status=500)
