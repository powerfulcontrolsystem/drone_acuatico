#!/bin/bash
# Script para iniciar el servidor del drone con optimización de RAM
# Uso: ./iniciar_servidor.sh

cd "$HOME/drone acuatico"

# Colores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color

echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}    INICIANDO SERVIDOR DEL DRONE ACUÁTICO${NC}"
echo -e "${BLUE}==================================================${NC}"
echo ""

# 1. Optimizar RAM antes de iniciar
echo -e "${YELLOW}[1/5] Optimizando RAM...${NC}"
bash optimizacion/optimizar_inicio.sh
echo ""

# 2. Activar entorno virtual
echo -e "${YELLOW}[2/5] Activando entorno virtual...${NC}"
if [ -f "venv_pi/bin/activate" ]; then
    source venv_pi/bin/activate
    echo -e "${GREEN}✓ Entorno virtual activado${NC}"
else
    echo -e "${RED}✗ Error: No se encontró el entorno virtual${NC}"
    exit 1
fi
echo ""

# 3. Verificar dependencias
echo -e "${YELLOW}[3/5] Verificando dependencias...${NC}"
python3 -c "import aiohttp, serial, pynmea2, RPi.GPIO as GPIO" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencias OK${NC}"
else
    echo -e "${YELLOW}⚠ Instalando dependencias faltantes...${NC}"
    pip install -q aiohttp pyserial pynmea2 RPi.GPIO
fi
echo ""

# 4. Verificar estado del sistema
echo -e "${YELLOW}[4/5] Estado del sistema:${NC}"
RAM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2 | cut -d"'" -f1 || echo "N/A")
echo "  RAM en uso: ${RAM_USAGE}%"
echo "  Temperatura: ${TEMP}°C"
echo ""

# 5. Iniciar el servidor
echo -e "${YELLOW}[5/5] Iniciando servidor en puerto 8080...${NC}"
echo -e "${GREEN}==================================================${NC}"
echo ""

# Ejecutar el servidor con manejo de errores
cd servidores
python3 drone_server.py

# Si el servidor termina inesperadamente
EXIT_CODE=$?
echo ""
echo -e "${YELLOW}Servidor detenido con código: ${EXIT_CODE}${NC}"

# Limpiar memoria al finalizar
echo -e "${YELLOW}Limpiando memoria...${NC}"
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
echo -e "${GREEN}✓ Limpieza completada${NC}"
