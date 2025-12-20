#!/bin/bash
# Script de optimización agresiva de RAM para Raspberry Pi
# Enfocado en reducir el consumo de VSCode Server

echo "=============================================="
echo "   OPTIMIZACIÓN AGRESIVA DE RAM"
echo "   Raspberry Pi - Drone Acuático"
echo "=============================================="
echo ""

# Función para mostrar uso de RAM
mostrar_ram() {
    RAM_INFO=$(free -m | grep Mem)
    TOTAL=$(echo $RAM_INFO | awk '{print $2}')
    USADO=$(echo $RAM_INFO | awk '{print $3}')
    LIBRE=$(echo $RAM_INFO | awk '{print $4}')
    PORCENTAJE=$((USADO * 100 / TOTAL))
    
    if [ $PORCENTAJE -lt 70 ]; then
        COLOR="\033[0;32m" # Verde
    elif [ $PORCENTAJE -lt 85 ]; then
        COLOR="\033[0;33m" # Amarillo
    else
        COLOR="\033[0;31m" # Rojo
    fi
    
    echo -e "${COLOR}RAM: ${USADO}/${TOTAL} MB (${PORCENTAJE}%)\033[0m"
}

echo "📊 Estado inicial:"
mostrar_ram
echo ""

# 1. Limpiar cachés del sistema
echo "🧹 1/7 Limpiando cachés del sistema..."
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
sleep 1
echo "   ✓ Completado"

# 2. Limpiar archivos temporales
echo "🧹 2/7 Limpiando archivos temporales..."
rm -rf /tmp/*.tmp 2>/dev/null
rm -rf /tmp/python-* 2>/dev/null
rm -rf /tmp/vscode-* 2>/dev/null
rm -rf /tmp/code-* 2>/dev/null
rm -rf ~/.cache/pip/* 2>/dev/null
rm -rf ~/.cache/matplotlib/* 2>/dev/null
echo "   ✓ Completado"

# 3. Optimizar VSCode Server (agresivo)
echo "🧹 3/7 Limpiando VSCode Server (agresivo)..."
# Limpiar logs antiguos (más de 1 día)
find ~/.vscode-server/data/logs -type f -mtime +1 -delete 2>/dev/null
# Limpiar todos los logs grandes
find ~/.vscode-server/data/logs -name "*.log" -size +5M -delete 2>/dev/null
# Limpiar caché de extensiones
rm -rf ~/.vscode-server/data/CachedExtensionVSIXs/* 2>/dev/null
# Limpiar workspace storage viejo
find ~/.vscode-server/data/User/workspaceStorage -type d -mtime +7 -exec rm -rf {} + 2>/dev/null
# Limpiar cache de código
rm -rf ~/.vscode-server/data/CachedData/* 2>/dev/null
# Comprimir logs que quedan
find ~/.vscode-server/data/logs -name "*.log" -size +1M -exec gzip {} \; 2>/dev/null
echo "   ✓ Completado"

# 4. Limpiar Python cache
echo "🧹 4/7 Limpiando caché de Python..."
find ~/drone\ acuatico -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyc" -delete 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyo" -delete 2>/dev/null
find ~/drone\ acuatico -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
echo "   ✓ Completado"

# 5. Comprimir logs del proyecto
echo "🧹 5/7 Comprimiendo logs del proyecto..."
find ~/drone\ acuatico -name "*.log" -size +3M -exec gzip {} \; 2>/dev/null
# Eliminar logs comprimidos muy antiguos (más de 30 días)
find ~/drone\ acuatico -name "*.log.gz" -mtime +30 -delete 2>/dev/null
echo "   ✓ Completado"

# 6. Optimizar swap si está lleno
echo "🧹 6/7 Optimizando swap..."
SWAP_USAGE=$(free -m | grep Swap | awk '{print $3}')
if [ "$SWAP_USAGE" -gt 100 ]; then
    echo "   Swap en uso: ${SWAP_USAGE} MB, reiniciando..."
    sudo swapoff -a 2>/dev/null && sudo swapon -a 2>/dev/null
    echo "   ✓ Swap reiniciado"
else
    echo "   ✓ Swap OK (${SWAP_USAGE} MB en uso)"
fi

# 7. Reiniciar procesos de VSCode si consumen mucho (opcional, comentado por seguridad)
echo "🧹 7/7 Verificando procesos pesados..."
VSCODE_MEM=$(ps aux | grep vscode-server | grep -v grep | awk '{sum+=$6} END {print int(sum/1024)}')
if [ ! -z "$VSCODE_MEM" ] && [ "$VSCODE_MEM" -gt 600 ]; then
    echo "   ⚠️  VSCode Server usando ${VSCODE_MEM} MB"
    echo "   💡 Consejo: Considera cerrar y reconectar VSCode para liberar memoria"
else
    echo "   ✓ Procesos normales"
fi

echo ""
echo "=============================================="
echo "📊 Estado final:"
mostrar_ram
echo ""

# Mostrar procesos que más consumen
echo "🔝 Top 5 procesos con más consumo de memoria:"
ps aux --sort=-%mem | head -n 6 | tail -n 5 | awk '{printf "   %s: %.1f MB (%s%%)\n", $11, $6/1024, $4}'
echo ""

echo "✅ Optimización completada"
echo "=============================================="
