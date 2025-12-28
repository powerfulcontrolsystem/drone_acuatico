# Optimizaciones - Arreglo de Caída SSH al Cambiar Tema

## Problema Identificado
La conexión SSH se caía cuando se intentaba cambiar el tema de oscuro a claro debido a **operaciones síncronas (bloqueantes) en el event loop asincrónico** del servidor.

### Root Cause (Causa Raíz)
1. **Operaciones de BD síncronas**: `obtener_tema()` y `guardar_tema()` eran llamadas directamente sin usar `run_in_executor`
2. **Bloqueo del event loop**: El servidor aiohttp es asincrónico pero las operaciones de BD sqlite3 bloqueaban el thread principal
3. **Sin timeout**: Las operaciones de BD podían colgarse indefinidamente
4. **Sin reintentos en cliente**: Si la solicitud fallaba, el cliente no lo reinentaba

## Soluciones Implementadas

### 1. **Servidor Python (servidor.py)**

#### `api_tema_get_handler()` - Optimizado
```python
# ANTES: Bloqueante
async def api_tema_get_handler(request):
    tema = obtener_tema()  # ❌ Bloquea el event loop
    return web.json_response({'tema': tema})

# DESPUÉS: No bloqueante
async def api_tema_get_handler(request):
    loop = asyncio.get_event_loop()
    tema = await loop.run_in_executor(None, obtener_tema)  # ✅ En thread separado
    return web.json_response({'tema': tema})
```

#### `api_tema_post_handler()` - Con timeout y manejo de errores
```python
# ANTES: Bloqueante y sin timeout
async def api_tema_post_handler(request):
    exito = guardar_tema(tema_oscuro)  # ❌ Bloquea
    return web.json_response({'exito': True, 'tema': tema})

# DESPUÉS: Non-blocking con timeout de 5s
async def api_tema_post_handler(request):
    loop = asyncio.get_event_loop()
    exito = await asyncio.wait_for(
        loop.run_in_executor(None, guardar_tema, tema_oscuro),
        timeout=5.0  # ✅ Timeout de 5 segundos
    )
    return web.json_response({'exito': True, 'tema': tema})
```

#### `websocket_handler()` - Inicialización mejorada
- Cambiar `obtener_configuracion()` a `await loop.run_in_executor(None, obtener_configuracion)`
- Esto evita bloquear durante la conexión inicial del WebSocket

### 2. **Cliente JavaScript (paginas/tema.js)**

#### Flags de control y reintentos
```javascript
// ✅ Evitar múltiples cambios simultáneos
let guardandoTema = false;

async function cambiarTema() {
    if (guardandoTema) {
        console.warn('Cambio de tema ya en progreso');
        return;  // Ignorar si ya hay uno en curso
    }
    // ... resto del código
}
```

#### Timeout en fetch
```javascript
// ✅ Timeout de 5 segundos en el cliente
const signal = AbortSignal.timeout(5000);
const response = await fetch('/api/tema', { signal });
```

#### Reintentos automáticos (hasta 3 intentos)
```javascript
// ✅ Reintentar 3 veces si falla
async function guardarTemaConReintentos(tema, reintentos = 3) {
    for (let intento = 0; intento < reintentos; intento++) {
        try {
            const response = await fetch('/api/tema', { /* ... */ });
            if (response.ok && data.exito) {
                return;  // ✅ Éxito
            }
        } catch (error) {
            if (intento < reintentos - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000));  // Esperar 1s
            }
        }
    }
}
```

## Mejoras Específicas

| Aspecto | Antes | Después |
|--------|-------|---------|
| **Bloqueo de BD** | Síncrono (bloquea event loop) | `run_in_executor` (thread separado) |
| **Timeout** | Sin timeout (puede colgar) | 5 segundos máximo |
| **Reintentos** | Ninguno (falla = falla) | Hasta 3 intentos automáticos |
| **Timeout cliente** | Sin timeout | 5 segundos con `AbortSignal` |
| **Requests simultáneos** | Permitidos (riesgo de conflicto) | Flag `guardandoTema` previene duplicados |

## Beneficios Esperados

✅ **No más caídas SSH** - Las operaciones de BD no bloquean el event loop
✅ **Mejor rendimiento** - Las BD ops se ejecutan en thread pool del executor
✅ **Mayor confiabilidad** - Reintentos automáticos en caso de fallos temporales
✅ **Mejor experiencia** - Cambios más rápidos y menos timeouts
✅ **Debugging más fácil** - Mensajes de error detallados en logs

## Testing Recomendado

1. Cambiar de tema múltiples veces rápidamente
2. Cambiar tema mientras se ejecutan otras operaciones (WebSocket, GPS, etc.)
3. Desconectar y reconectar SSH mientras se cambia tema
4. Revisar logs: `tail -f /var/log/syslog | grep "Tema"`

## Comandos para Verificar

```bash
# Ver logs del servidor
tail -100 /var/log/syslog | grep "servidor\|tema"

# Revisar si el proceso del servidor está usando mucho CPU/memoria
ps aux | grep python3 | grep servidor

# Probar la API manualmente
curl -X POST http://localhost:8080/api/tema -H "Content-Type: application/json" -d '{"tema":"claro"}'
```

---

**Fecha**: 27 de Diciembre 2025
**Cambios realizados**: 
- `/home/admin/drone acuatico/servidor.py` (3 funciones optimizadas)
- `/home/admin/drone acuatico/paginas/tema.js` (reintentos + timeout + flags)
