#!/bin/bash
# ===================================================================
# Script ÚNICO para iniciar el servidor del Drone Acuático
# Archivo: iniciar_servidor.sh
# Servidor: servidor.py
# ===================================================================

# Cambiar al directorio del proyecto
cd "$(dirname "$(readlink -f "$0")")" || exit 1

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sin color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   SERVIDOR DRONE ACUÁTICO - CONTROL REMOTO WEB${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""



# 1. Limpiar procesos previos y liberar puerto
echo -e "${YELLOW}[1/6] Limpiando procesos previos...${NC}"
pkill -9 -f "servidor.py" 2>/dev/null || true
pkill -9 -f "python3" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Procesos limpiados${NC}"
echo ""

# 2. Verificar/crear entorno virtual
echo -e "${YELLOW}[2/6] Verificando entorno virtual...${NC}"
if [ ! -d "venv_pi" ]; then
    echo -e "${YELLOW}⚠ Entorno virtual no encontrado. Creando...${NC}"
    python3 -m venv venv_pi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Entorno virtual creado${NC}"
    else
        echo -e "${RED}✗ Error: No se pudo crear el entorno virtual${NC}"
        echo -e "${YELLOW}Instala python3-venv: sudo apt install python3-venv${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Entorno virtual encontrado${NC}"
fi
echo ""

# 3. Activar entorno virtual
echo -e "${YELLOW}[3/6] Activando entorno virtual...${NC}"
if [ -f "venv_pi/bin/activate" ]; then
    source venv_pi/bin/activate
    echo -e "${GREEN}✓ Entorno virtual activado ($(which python3))${NC}"
else
    echo -e "${RED}✗ Error: No se encontró venv_pi/bin/activate${NC}"
    exit 1
fi
echo ""

# 4. Instalar/actualizar dependencias
echo -e "${YELLOW}[4/6] Instalando dependencias...${NC}"

# 4a. Instalar dependencias del sistema necesarias
echo -e "${YELLOW}   4a) Verificando dependencias del sistema...${NC}"
DEPS_SISTEMA="python3-dev libcap-dev"
FALTA_INSTALAR=0

for dep in $DEPS_SISTEMA; do
    if ! dpkg -l | grep -q "^ii  $dep"; then
        FALTA_INSTALAR=1
        break
    fi
done

if [ $FALTA_INSTALAR -eq 1 ]; then
    echo -e "${YELLOW}   ⚠ Instalando dependencias del sistema (puede requerir sudo)...${NC}"
    if command -v sudo &> /dev/null; then
        sudo apt-get update -qq 2>/dev/null
        sudo apt-get install -y -qq $DEPS_SISTEMA 2>/dev/null
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}   ✓ Dependencias del sistema instaladas${NC}"
        else
            echo -e "${YELLOW}   ⚠ No se pudieron instalar algunas dependencias del sistema (picamera2 podría no funcionar)${NC}"
        fi
    else
        echo -e "${YELLOW}   ⚠ Se requiere sudo para instalar dependencias del sistema${NC}"
    fi
else
    echo -e "${GREEN}   ✓ Dependencias del sistema ya instaladas${NC}"
fi

# 4b. Actualizar pip y instalar dependencias Python
echo -e "${YELLOW}   4b) Instalando paquetes Python...${NC}"
pip install --upgrade pip setuptools wheel -q 2>/dev/null

# Instalación de dependencias críticas
echo -e "${YELLOW}   4c) Instalando dependencias críticas...${NC}"
if [ -f "requirements.txt" ]; then
    # Intentar instalar desde requirements.txt con fallback
    pip install -r requirements.txt --prefer-binary -q 2>/dev/null
    
    # Si falla, instalar dependencias core (sin picamera2 que es opcional)
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}   ⚠ Algunas dependencias fallaron. Instalando versión core (sin picamera2)...${NC}"
        if [ -f "requirements_core.txt" ]; then
            pip install -r requirements_core.txt --prefer-binary -q
        else
            pip install aiohttp>=3.8.0 pyserial>=3.5 pynmea2>=1.18.0 RPi.GPIO>=0.7.1 --prefer-binary -q
        fi
    fi
else
    pip install aiohttp pyserial pynmea2 RPi.GPIO --prefer-binary -q
fi

# 4d. Verificar dependencias críticas
echo -e "${YELLOW}   4d) Verificando dependencias instaladas...${NC}"
python3 - <<'PY'
import sys
deps_ok = True
missing = []

try:
    import aiohttp
except:
    deps_ok = False
    missing.append("aiohttp")

try:
    import serial
except:
    deps_ok = False
    missing.append("pyserial")

try:
    import pynmea2
except:
    deps_ok = False
    missing.append("pynmea2")

try:
    import RPi.GPIO
except:
    deps_ok = False
    missing.append("RPi.GPIO")

if deps_ok:
    print(f"✓ Todas las dependencias críticas instaladas")
else:
    print(f"✗ Faltan dependencias: {', '.join(missing)}")
    sys.exit(1)
PY

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencias verificadas y funcionales${NC}"
else
    echo -e "${RED}✗ Error: No se pudieron instalar todas las dependencias${NC}"
    echo -e "${YELLOW}Intenta instalar manualmente en el venv:${NC}"
    echo -e "${YELLOW}  source venv_pi/bin/activate${NC}"
    echo -e "${YELLOW}  pip install --upgrade pip${NC}"
    echo -e "${YELLOW}  pip install aiohttp pyserial pynmea2 RPi.GPIO --prefer-binary${NC}"
    exit 1
fi
echo ""
# Asegurar carpetas HLS para streams
mkdir -p hls/cam1 hls/cam2

# 5. Iniciar el servidor
echo -e "${YELLOW}[5/6] Iniciando servidor...${NC}"
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}✓ Servidor en: http://localhost:8080${NC}"
echo -e "${GREEN}✓ Archivo: servidor.py${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
echo -e "${YELLOW}[6/6] Esperando conexiones...${NC}"
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
echo ""

# Ejecutar el servidor (logs en archivo, solo startup en pantalla)
echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   LOGS DEL SERVIDOR: /tmp/servidor_drone.log${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
python3 servidor.py > /tmp/servidor_drone.log 2>&1 &
SERVER_PID=$!

# Esperar a que el servidor esté listo
sleep 2

# Mostrar estado GPS
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo -e "${YELLOW}   ESTADO DEL SISTEMA${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo ""

# Obtener estado GPS
python3 -c "
import time
from funciones import GPS_DATOS, iniciar_gps
iniciar_gps()
time.sleep(2)
if GPS_DATOS['valido']:
    print(f'✓ GPS: Conectado')
    print(f'  Latitud:  {GPS_DATOS[\"latitud\"]}')
    print(f'  Longitud: {GPS_DATOS[\"longitud\"]}')
    print(f'  Altitud:  {GPS_DATOS[\"altitud\"]}m')
    print(f'  Satélites: {GPS_DATOS[\"satelites\"]}')
else:
    print(f'⚠ GPS: Sin señal (mueve a una ubicación con vista al cielo)')
    if GPS_DATOS['satelites'] > 0:
        print(f'  Satélites en vista: {GPS_DATOS[\"satelites\"]}')
" 2>/dev/null || echo "⚠ GPS: No disponible"

echo ""
echo -e "${GREEN}✓ Servidor listo en http://localhost:8080${NC}"
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
echo ""

# Mantener el script vivo
wait $SERVER_PID

# Si el servidor se detiene
echo ""
echo -e "${YELLOW}Servidor detenido${NC}"
