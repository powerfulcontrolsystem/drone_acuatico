# 🔧 Reparación de Instalación de Dependencias

## 📋 Resumen de Cambios

Se reparó el script `iniciar_servidor.sh` para garantizar que **TODAS las dependencias se instalen correctamente**, incluyendo las que requieren compilación.

---

## 🎯 Problemas Solucionados

### 1. **Dependencias del Sistema No Instaladas**
   - **Problema**: Paquetes como `libcap-dev` (requerido por `python-prctl`) no se instalaban
   - **Solución**: Agregada detección automática e instalación de dependencias del sistema

### 2. **Fallos Silenciosos en la Instalación de pip**
   - **Problema**: Si `pip install -r requirements.txt` fallaba, el script continuaba sin verificar
   - **Solución**: Agregada verificación explícita de cada dependencia tras la instalación

### 3. **Falta de Fallback para Dependencias Opcionales**
   - **Problema**: `picamera2` fallaba en compilación y bloqueaba todo
   - **Solución**: Creado `requirements_core.txt` con solo dependencias críticas como fallback

---

## 📦 Archivos Modificados

### 1. **`iniciar_servidor.sh`** (PRINCIPAL)
Paso 4 completamente reescrito con:
- ✅ Instalación automática de dependencias del sistema (`libcap-dev`, `python3-dev`)
- ✅ Actualización de pip, setuptools y wheel
- ✅ Instalación con fallback inteligente
- ✅ Verificación explícita de cada dependencia crítica
- ✅ Mensajes de error claros si algo falla

### 2. **`requirements.txt`** (MEJORADO)
- ✅ Comentarios explicativos
- ✅ `picamera2` comentado por defecto (opcional, con problemas de compilación)
- ✅ Clarificación de dependencias críticas vs opcionales

### 3. **`requirements_core.txt`** (NUEVO)
- ✅ Contiene solo las 4 dependencias críticas
- ✅ Usado como fallback si `requirements.txt` falla
- ✅ Garantiza que el servidor SIEMPRE funcione

---

## 🚀 Dependencias Instaladas

### Críticas (Obligatorias)
| Paquete | Versión | Función |
|---------|---------|---------|
| `aiohttp` | ≥3.8.0 | Servidor web asincrónico (CORE) |
| `pyserial` | ≥3.5 | Comunicación con módulo GPS |
| `pynmea2` | ≥1.18.0 | Análisis de datos NMEA GPS |
| `RPi.GPIO` | ≥0.7.1 | Control GPIO (relés, sensores) |

### Opcionales
| Paquete | Versión | Función |
|---------|---------|---------|
| `picamera2` | ≥0.3.0 | Control cámaras Raspberry Pi (puede fallar compilación) |

---

## 🛠️ Dependencias del Sistema Instaladas

```bash
# Estas se instalan automáticamente en el Paso 4a:
- python3-dev      # Headers Python para compilación
- libcap-dev       # Libcap para python-prctl (picamera2)
```

---

## ✅ Verificación

Ejecutar después de iniciar el servidor:

```bash
source venv_pi/bin/activate
python3 -c "import aiohttp, serial, pynmea2, RPi; print('✓ Todas las dependencias funcionan')"
```

---

## 📊 Flujo de Instalación (Mejorado)

```
[4/6] Instalando dependencias...
   ├─ [4a] Dependencias del sistema
   │       └─ Detecta e instala: libcap-dev, python3-dev
   ├─ [4b] Actualizar pip/setuptools/wheel
   ├─ [4c] Instalar paquetes Python
   │       ├─ Intenta: requirements.txt (con picamera2)
   │       └─ Si falla: requirements_core.txt (sin picamera2)
   └─ [4d] Verificar cada dependencia crítica
           └─ Error claro si algo falta
```

---

## 🔍 Notas Importantes

1. **Acceso `sudo` requerido** para instalar dependencias del sistema
2. **`picamera2` es opcional** - El servidor funciona sin él
3. **Instalación idempotente** - Se puede ejecutar múltiples veces sin problemas
4. **Logs detallados** en `/tmp/servidor_drone.log`

---

## 📝 Cambios en `iniciar_servidor.sh`

**Antes**: Verificación simple que fallaba silenciosamente
**Ahora**: Proceso robusto de 4 pasos con falbacks inteligentes

---
