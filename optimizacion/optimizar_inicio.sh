#!/bin/bash
# Script de optimización automática al iniciar el servidor del drone
# Este script se ejecuta antes de iniciar el servidor para liberar RAM

LOG_FILE="$HOME/drone acuatico/optimizacion/inicio.log"
echo "==================================================" >> "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Optimización al inicio" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

# 1. Mostrar estado inicial
echo "" >> "$LOG_FILE"
echo "=== ESTADO INICIAL DE RAM ===" >> "$LOG_FILE"
free -h >> "$LOG_FILE"
RAM_INICIAL=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
echo "RAM en uso: ${RAM_INICIAL}%" >> "$LOG_FILE"

# 2. Sincronizar y limpiar cachés del sistema
echo "" >> "$LOG_FILE"
echo "1. Limpiando cachés del sistema..." >> "$LOG_FILE"
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
sleep 1
echo "   ✓ Cachés del sistema limpiados" >> "$LOG_FILE"

# 3. Limpiar archivos temporales
echo "2. Limpiando archivos temporales..." >> "$LOG_FILE"
rm -rf /tmp/*.tmp 2>/dev/null
rm -rf /tmp/python-* 2>/dev/null
rm -rf /tmp/vscode-* 2>/dev/null
rm -rf /tmp/code-* 2>/dev/null
rm -rf ~/.cache/pip/* 2>/dev/null
echo "   ✓ Temporales eliminados" >> "$LOG_FILE"

# 4. Limpiar logs antiguos de VSCode
echo "3. Limpiando VSCode..." >> "$LOG_FILE"
find ~/.vscode-server/data/logs -type f -mtime +2 -delete 2>/dev/null
find ~/.vscode-server/data/logs -name "*.log" -size +5M -exec gzip {} \; 2>/dev/null
rm -rf ~/.vscode-server/data/CachedExtensionVSIXs/* 2>/dev/null
echo "   ✓ VSCode optimizado" >> "$LOG_FILE"

# 5. Limpiar caché de Python
echo "4. Limpiando caché de Python..." >> "$LOG_FILE"
find "$HOME/drone acuatico" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$HOME/drone acuatico" -type f -name "*.pyc" -delete 2>/dev/null
find "$HOME/drone acuatico" -type f -name "*.pyo" -delete 2>/dev/null
echo "   ✓ Caché de Python limpiado" >> "$LOG_FILE"

# 6. Comprimir logs grandes del proyecto
echo "5. Comprimiendo logs grandes..." >> "$LOG_FILE"
find "$HOME/drone acuatico" -name "*.log" -size +10M ! -name "inicio.log" -exec gzip {} \; 2>/dev/null
echo "   ✓ Logs comprimidos" >> "$LOG_FILE"

# 7. Optimizar swap si está muy usado
echo "6. Optimizando swap..." >> "$LOG_FILE"
SWAP_USAGE=$(free | grep Swap | awk '{print $3}')
if [ "$SWAP_USAGE" -gt 102400 ]; then
    sudo swapoff -a 2>/dev/null && sudo swapon -a 2>/dev/null
    echo "   ✓ Swap reiniciado" >> "$LOG_FILE"
else
    echo "   ✓ Swap en buen estado" >> "$LOG_FILE"
fi

# 8. Ajustar swappiness para mejor rendimiento
echo "7. Ajustando swappiness..." >> "$LOG_FILE"
echo 10 | sudo tee /proc/sys/vm/swappiness > /dev/null 2>&1
echo "   ✓ Swappiness establecido a 10" >> "$LOG_FILE"

# 9. Estado final
echo "" >> "$LOG_FILE"
echo "=== ESTADO FINAL DE RAM ===" >> "$LOG_FILE"
free -h >> "$LOG_FILE"
RAM_FINAL=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
echo "RAM en uso: ${RAM_FINAL}%" >> "$LOG_FILE"

# Calcular RAM liberada
RAM_LIBERADA=$((RAM_INICIAL - RAM_FINAL))
echo "" >> "$LOG_FILE"
echo "✓ RAM liberada: ${RAM_LIBERADA}%" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

# Mostrar también en pantalla
echo "✓ Optimización completada - RAM liberada: ${RAM_LIBERADA}%"
echo "  RAM antes: ${RAM_INICIAL}% | RAM ahora: ${RAM_FINAL}%"
