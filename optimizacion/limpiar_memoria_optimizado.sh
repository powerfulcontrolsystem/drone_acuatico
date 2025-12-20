#!/bin/bash
# Script optimizado para limpiar memoria en Raspberry Pi

echo "=== LIMPIEZA DE MEMORIA RASPBERRY PI ==="
echo ""

# Estado inicial
echo "Memoria ANTES:"
free -h
echo ""

# 1. Sincronizar y limpiar cachés del sistema
echo "1. Limpiando cachés del sistema..."
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
sleep 1
echo "   ✓ Cachés del sistema limpiados"

# 2. Limpiar archivos temporales
echo "2. Limpiando archivos temporales..."
rm -rf /tmp/*.tmp 2>/dev/null
rm -rf /tmp/python-* 2>/dev/null
rm -rf /tmp/vscode-* 2>/dev/null
rm -rf ~/.cache/pip/* 2>/dev/null
echo "   ✓ Temporales eliminados"

# 3. Limpiar logs de VSCode
echo "3. Limpiando VSCode..."
find ~/.vscode-server/data/logs -type f -mtime +1 -delete 2>/dev/null
rm -rf ~/.vscode-server/data/CachedExtensionVSIXs/* 2>/dev/null
find ~/.vscode-server/data/logs -name "*.log" -size +10M -exec gzip {} \; 2>/dev/null
echo "   ✓ VSCode limpiado"

# 4. Limpiar caché de Python
echo "4. Limpiando caché de Python..."
find ~/drone\ acuatico -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyc" -delete 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyo" -delete 2>/dev/null
echo "   ✓ Caché de Python limpiado"

# 5. Comprimir logs del proyecto
echo "5. Comprimiendo logs grandes del proyecto..."
find ~/drone\ acuatico -name "*.log" -size +5M -exec gzip {} \; 2>/dev/null
echo "   ✓ Logs comprimidos"

# 6. Optimizar swap
echo "6. Optimizando swap..."
SWAP_USAGE=$(free | grep Swap | awk '{print $3}')
if [ "$SWAP_USAGE" -gt 102400 ]; then
    sudo swapoff -a 2>/dev/null && sudo swapon -a 2>/dev/null
    echo "   ✓ Swap reiniciado"
else
    echo "   ✓ Swap OK (uso bajo)"
fi

echo ""
echo "Memoria DESPUÉS:"
free -h
echo ""
echo "=== LIMPIEZA COMPLETADA ==="
