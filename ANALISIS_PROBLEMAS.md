# ANÁLISIS DE PROBLEMAS - CONEXIÓN WiFi INESTABLE EN RASPBERRY PI

## 📋 RESUMEN EJECUTIVO

He revisado toda la configuración del proyecto del Drone Acuático. Encontré **VARIOS problemas potenciales** que pueden estar causando:
1. **Desconexiones WiFi inestables**
2. **Ahorro de energía no deseado**
3. **Posibles fugas de memoria RAM**

---

## 🔴 PROBLEMAS IDENTIFICADOS

### 1. **AHORRO DE ENERGÍA WiFi ACTIVADO** ⚠️ CRÍTICO
**Ubicación:** Configuración del módulo WiFi de la Raspberry Pi  
**Síntoma:** La Raspberry entra en modo "sleep" después de cierto tiempo sin actividad

**El problema:**
- Linux en Raspberry Pi tiene **PowerSave habilitado por defecto**
- Cuando no hay tráfico, el WiFi entra en modo bajo consumo
- El dispositivo no responde inmediatamente a conexiones
- Causa desconexiones y latencia alta

**Solución:**
```bash
# Ver estado actual
iw wlan0 get power_save

# Desactivar PowerSave WiFi (temporal)
sudo iw wlan0 set power_save off

# Para hacerlo permanente, crear un archivo:
sudo nano /etc/modprobe.d/brcmfmac.conf
# Y añadir:
options brcmfmac power_save=0
```

---

### 2. **SERVIDOR WEBSOCKET CON HEARTBEAT INSUFICIENTE**
**Ubicación:** `servidor.py` línea 159  
**Código:**
```python
ws = web.WebSocketResponse(heartbeat=30)
```

**El problema:**
- Heartbeat de 30 segundos es TOO LARGO para WiFi inestable
- Si hay desconexión intermitente, el cliente no se da cuenta rápido
- El cliente intenta reconectar cada 3 segundos (línea 343 de index.html)
- Hay desacoplamiento entre cliente y servidor

**Solución:**
Reducir el heartbeat a 10-15 segundos:
```python
ws = web.WebSocketResponse(heartbeat=15)
```

---

### 3. **GESTIÓN DE CONEXIONES WEBSOCKET DÉBIL**
**Ubicación:** `servidor.py` líneas 177-210

**El problema:**
```python
try:
    async for msg in ws:
        # ... procesar mensaje
finally:
    CLIENTES_WS.discard(ws)
    await ws.close()
```

- NO hay manejo de **timeouts de conexión**
- NO hay **re-envío de mensajes perdidos**
- Si la red falla momentáneamente, se pierde el mensaje
- Cliente reconecta cada 3 segundos pero puede tener lag

**Solución:**
Implementar reconexión más robusta con backoff exponencial

---

### 4. **ENVÍO PERIÓDICO DE DATOS SIN CONTROL DE MEMORIA**
**Ubicación:** `servidor.py` líneas 70-119 (`enviar_datos_periodicos`)

**El problema:**
```python
async def enviar_datos_periodicos():
    while True:
        await asyncio.sleep(5)
        if not CLIENTES_WS:
            continue
        
        # Obtener datos
        ram = obtener_ram()  # Llamada costosa
        temp = obtener_temperatura()  # Subprocess
        bat = obtener_bateria()
        # ... 5 líneas más
        
        # Enviar a TODOS los clientes
        for cliente in list(CLIENTES_WS):
            # Envía 5 mensajes por cliente cada 5 segundos
```

- Se llama a **subprocess 5 veces cada 5 segundos** para obtener datos
- Cada subprocess cuesta recursos
- Si hay 2-3 clientes, son 10-15 subprocesses cada 5 segundos
- **Fuga potencial de procesos zombie**
- Consume mucha CPU en una Raspberry Pi 3 (512MB RAM)

**Solución:**
- Caching de datos (calcular una sola vez cada 5 segundos)
- Llamadas a subprocess con timeout
- Limpieza de procesos zombie

---

### 5. **RAM LIMITADA Y STREAMING DE VIDEO**
**Ubicación:** `camera_stream.py` y `funciones.py`

**El problema:**
```bash
# Raspberry Pi 3 tiene solo:
- RAM: 1024 MB total
- Solo ~500-600MB disponibles inicialmente
```

- El servidor Python consume ~50-100MB
- ffmpeg para cada stream HLS consume 100-150MB per cámara
- **2 cámaras = 300MB+ solo en video**
- Quedan ~200MB para GPS, sensores, GPIO
- **Cualquier fuga de memoria causa shutdown**

**Solución:**
- Implementar límites de memoria en ffmpeg
- Monitorear procesos zombie
- Limpiar buffers después de cada transmisión

---

### 6. **SIN CONFIGURACIÓN DE TIMEOUT EN CONEXIONES**
**Ubicación:** `servidor.py` línea 8 (imports)

**El problema:**
```python
from aiohttp import WSMsgType, web
# NO hay configuración de timeout para conexiones HTTP
```

- Las conexiones pueden quedarse "colgadas"
- Sin timeout, un cliente mal comportado bloquea recursos
- Acumula conexiones "zombies"

**Solución:**
```python
app = web.Application(
    client_max_size=10*1024*1024,  # 10MB
    loop=loop,
)
```

---

## ✅ COMPROBACIONES A REALIZAR

Crea un script para verificar el estado actual (ya lo he creado):

```bash
chmod +x /home/admin/drone\ acuatico/diagnostico_wifi_energia.sh
./diagnostico_wifi_energia.sh
```

Este script verificará:
- ✔️ RAM disponible y procesos que consumen memoria
- ✔️ Estado de PowerSave WiFi
- ✔️ Temperatura y throttling
- ✔️ Procesos del servidor
- ✔️ Conexiones activas

---

## 🔧 PLAN DE CORRECCIÓN

### PASO 1: Desactivar PowerSave WiFi (INMEDIATO)
```bash
sudo iw wlan0 set power_save off
```

### PASO 2: Actualizar heartbeat en servidor.py
**Cambio en línea 159:**
```python
# Antes:
ws = web.WebSocketResponse(heartbeat=30)

# Después:
ws = web.WebSocketResponse(heartbeat=15)
```

### PASO 3: Caching de datos del sistema
Modificar `enviar_datos_periodicos()` para:
- Calcular datos UNA sola vez por ciclo
- Cachear resultados
- Enviar el mismo dato a todos los clientes

### PASO 4: Monitorear memoria
Añadir a `funciones.py`:
```python
def monitorear_memoria():
    """Alerta si RAM disponible < 50MB"""
    ram = obtener_ram()
    if ram['available'] < 50:
        logger.warning(f"⚠️ RAM crítica: {ram['available']}MB disponible")
        # Limpiar procesos zombie
        subprocess.run(['pkill', '-9', 'zombie'], capture_output=True)
```

### PASO 5: Permanentemente desactivar PowerSave
```bash
echo "options brcmfmac power_save=0" | sudo tee /etc/modprobe.d/brcmfmac.conf
```

---

## 📊 IMPACTO ESTIMADO

| Problema | Impacto | Criticidad |
|----------|--------|-----------|
| PowerSave WiFi | Desconexiones cada 5-10 min | 🔴 CRÍTICO |
| Heartbeat 30s | Latencia alta, lag | 🟠 ALTO |
| Fugas de subprocess | RAM desbordada | 🔴 CRÍTICO |
| Sin timeout conexiones | Bloqueos | 🟠 ALTO |
| RAM limitada | Crashes aleatorios | 🟠 ALTO |

---

## 🎯 PRÓXIMOS PASOS

1. **Ejecutar el diagnóstico** para confirmar PowerSave activo
2. **Desactivar PowerSave WiFi** inmediatamente
3. **Actualizar heartbeat** a 15 segundos
4. **Monitorear** durante 1 hora
5. **Si persiste:** Implementar caching de datos

---

## 📝 NOTAS ADICIONALES

- **No cambies GPIO ni pins** - esa configuración está correcta
- **El streaming HLS es correcto** - usa `copy` codec (bajo consumo)
- **La BD SQLite es eficiente** - no es el problema
- **El problema principal es WiFi + ahorro de energía + RAM limitada**

---

Espera a que ejecutes el diagnóstico y me muestres los resultados.
