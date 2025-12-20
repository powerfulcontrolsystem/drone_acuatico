#!/bin/bash
# Script para limpiar archivos temporales de VSCode y liberar RAM

echo "🧹 Limpiando archivos temporales de VSCode..."

# Limpiar logs antiguos de VSCode
find ~/.vscode-server/data/logs -type f -mtime +3 -delete 2>/dev/null
echo "✓ Logs antiguos eliminados"

# Limpiar caché de extensiones
rm -rf ~/.vscode-server/data/CachedExtensionVSIXs/* 2>/dev/null
echo "✓ Caché de extensiones limpiado"

# Limpiar archivos temporales de Python
find ~/drone\ acuatico -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyc" -delete 2>/dev/null
find ~/drone\ acuatico -type f -name "*.pyo" -delete 2>/dev/null
echo "✓ Archivos .pyc eliminados"

# Limpiar caché del sistema
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null
echo "✓ Caché del sistema limpiado"

echo ""
echo "📊 Estado de memoria:"
free -h

echo ""
echo "✅ Limpieza completada"
