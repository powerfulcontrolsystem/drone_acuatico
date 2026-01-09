# 📹 Configuración de Cámaras en Vivo

## ✅ Cambios Realizados

He actualizado el sistema para que funcione correctamente con URLs RTSP:

1. **camera_stream.py** - Ahora usa los campos simplificados `url_camara1` y `url_camara2`
2. **servidor.py** - Inicia las cámaras automáticamente al arrancar si están configuradas
3. **Base de datos** - Migración automática de campos antiguos a nuevos

## 🔧 Cómo Configurar tus Cámaras

### Paso 1: Obtener la URL RTSP de tus cámaras
Tus cámaras IP te proporcionan una URL RTSP, que típicamente tiene este formato:
```
rtsp://usuario:contraseña@192.168.1.X:554/ruta/stream
```

Ejemplos comunes:
- **Hikvision**: `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`
- **Dahua**: `rtsp://admin:password@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0`
- **Generic**: `rtsp://admin:admin@192.168.1.10:554/live/ch0`

### Paso 2: Configurar en la Interfaz Web

1. Inicia el servidor:
   ```bash
   cd /home/admin/drone\ acuatico
   bash iniciar_servidor.sh
   ```

2. Abre el navegador y ve a: `http://localhost:8080`

3. Haz clic en "Configuración"

4. En la sección **Cámaras**, ingresa:
   - **Cámara 1 - URL RTSP**: Tu URL RTSP completa de la cámara 1
   - **Cámara 2 - URL RTSP**: Tu URL RTSP completa de la cámara 2

5. Asegúrate de que:
   - ✓ Las opciones "Iniciar automáticamente la cámara" estén marcadas
   - Las opciones "Desactivar Cámara" estén desmarcadas

6. Haz clic en "💾 Guardar"

### Paso 3: Ver las Cámaras en Vivo

1. Regresa a la página principal (Control Remoto)
2. Las cámaras deberían iniciarse automáticamente
3. Si no se inician, haz clic en el botón de menú (⋮) de cada cámara y selecciona "▶ Play/Stop"

## 🔍 Verificación y Solución de Problemas

### Verificar que las URLs RTSP funcionan

Prueba manualmente tu URL RTSP con ffmpeg:
```bash
ffmpeg -rtsp_transport tcp -i "rtsp://tu-url-completa" -t 5 -f null -
```

Si ves errores, verifica:
- ✓ Usuario y contraseña correctos
- ✓ IP de la cámara accesible desde la Raspberry Pi
- ✓ Puerto correcto (usualmente 554)
- ✓ Ruta del stream correcta

### Ver logs del servidor

Para ver si las cámaras se están iniciando correctamente:
```bash
cd /home/admin/drone\ acuatico
bash iniciar_servidor.sh
```

Deberías ver mensajes como:
```
✓ Cámara 1 iniciada: rtsp://...
✓ Cámara 2 iniciada: rtsp://...
```

### Verificar archivos HLS generados

```bash
ls -lh /home/admin/drone\ acuatico/hls/cam1/
ls -lh /home/admin/drone\ acuatico/hls/cam2/
```

Deberías ver archivos `.ts` y `.m3u8` siendo creados.

## 📝 Notas Importantes

- El sistema convierte RTSP a HLS (HTTP Live Streaming) para reproducción en el navegador
- La conversión la hace `ffmpeg` en segundo plano
- Las cámaras se inician automáticamente al arrancar el servidor si:
  - Tienen una URL RTSP configurada
  - No están desactivadas
  - Tienen la opción "Iniciar automáticamente" activada
- Si cambias la URL de una cámara, necesitas reiniciar el servidor

## 🎯 Siguiente Paso

1. Obtén las URLs RTSP de tus cámaras IP
2. Inicia el servidor: `bash iniciar_servidor.sh`
3. Ve a configuración y guarda las URLs
4. Reinicia el servidor
5. ¡Disfruta de tus cámaras en vivo! 🎥✨
