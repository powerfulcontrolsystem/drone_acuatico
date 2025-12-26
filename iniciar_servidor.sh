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

# 0. Limpiar procesos previos y liberar puerto
echo -e "${YELLOW}[0/4] Limpiando procesos previos...${NC}"
pkill -9 -f "servidor.py" 2>/dev/null || true
pkill -9 -f "python3" 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓ Procesos limpiados${NC}"
echo ""

# 1. Activar entorno virtual
echo -e "${YELLOW}[1/4] Activando entorno virtual...${NC}"
if [ -f "venv_pi/bin/activate" ]; then
    source venv_pi/bin/activate
    echo -e "${GREEN}✓ Entorno virtual activado${NC}"
else
    echo -e "${RED}✗ Error: No se encontró venv_pi/bin/activate${NC}"
    exit 1
fi
echo ""

# 2. Verificar dependencias
echo -e "${YELLOW}[2/4] Verificando dependencias...${NC}"
python3 -c "import aiohttp, serial, pynmea2" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencias OK${NC}"
else
    echo -e "${YELLOW}⚠ Instalando dependencias...${NC}"
    pip install -q aiohttp pyserial pynmea2
    if [ $? -ne 0 ]; then
        echo -e "${YELLOW}⚠ Algunas dependencias pueden no estar disponibles${NC}"
    fi
fi
echo ""

# 3. Iniciar el servidor
echo -e "${YELLOW}[3/4] Iniciando servidor...${NC}"
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}✓ Servidor en: http://localhost:8080${NC}"
echo -e "${GREEN}✓ Archivo: servidor.py${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
echo -e "${YELLOW}[4/4] Esperando conexiones...${NC}"
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
echo ""

# Ejecutar el servidor
python3 servidor.py

# Si el servidor se detiene
echo ""
echo -e "${YELLOW}Servidor detenido${NC}"
