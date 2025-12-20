#!/bin/bash
# Script especializado para limpiar y optimizar VSCode Server
# Reduce significativamente el consumo de memoria sin desconectar

echo "=============================================="
echo "   LIMPIEZA DE VSCODE SERVER"
echo "   Optimización sin desconexión"
echo "=============================================="
echo ""

# Verificar si VSCode está corriendo
if ! pgrep -f "vscode-server" > /dev/null; then
    echo "⚠️  VSCode Server no está corriendo"
    exit 0
fi

# Mostrar consumo actual
VSCODE_MEM=$(ps aux | grep vscode-server | grep -v grep | awk '{sum+=$6} END {print int(sum/1024)}')
echo "📊 Memoria actual de VSCode: ${VSCODE_MEM} MB"
echo ""

# 1. Configurar límites de memoria de Node.js
echo "⚙️  1/6 Configurando límites de Node.js..."
if ! grep -q "NODE_OPTIONS.*max-old-space-size" ~/.bashrc; then
    echo "export NODE_OPTIONS='--max-old-space-size=200'" >> ~/.bashrc
    echo "   ✓ Límite añadido a ~/.bashrc (requiere reconexión)"
else
    echo "   ✓ Ya configurado"
fi

# 2. Configurar settings de VSCode Server
echo "⚙️  2/6 Configurando settings optimizados..."
VSCODE_SETTINGS="$HOME/.vscode-server/data/Machine/settings.json"
mkdir -p "$(dirname "$VSCODE_SETTINGS")"

cat > "$VSCODE_SETTINGS" << 'EOF'
{
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/**": true,
        "**/venv_pi/**": true,
        "**/__pycache__/**": true,
        "**/.cache/**": true,
        "**/tmp/**": true
    },
    "search.followSymlinks": false,
    "search.exclude": {
        "**/node_modules": true,
        "**/venv_pi/**": true,
        "**/__pycache__/**": true,
        "**/*.log.gz": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/.cache": true
    },
    "extensions.autoUpdate": false,
    "extensions.autoCheckUpdates": false,
    "telemetry.telemetryLevel": "off",
    "update.mode": "none",
    "git.autorefresh": false,
    "git.autofetch": false,
    "workbench.enableExperiments": false,
    "files.autoSave": "afterDelay",
    "files.autoSaveDelay": 5000,
    "editor.quickSuggestions": {
        "other": false,
        "comments": false,
        "strings": false
    },
    "editor.parameterHints.enabled": false,
    "editor.suggest.showWords": false,
    "editor.wordBasedSuggestions": "off",
    "editor.formatOnSave": false,
    "editor.formatOnType": false
}
EOF
echo "   ✓ Settings optimizados creados"

# 3. Limpiar logs de VSCode
echo "🧹 3/6 Limpiando logs..."
# Eliminar logs antiguos
find ~/.vscode-server/data/logs -type f -mtime +1 -delete 2>/dev/null
# Comprimir logs grandes
find ~/.vscode-server/data/logs -name "*.log" -size +2M -exec gzip {} \; 2>/dev/null
# Eliminar logs vacíos
find ~/.vscode-server/data/logs -type f -empty -delete 2>/dev/null
SIZE_FREED=$(du -sh ~/.vscode-server/data/logs 2>/dev/null | awk '{print $1}')
echo "   ✓ Logs: ${SIZE_FREED} restantes"

# 4. Limpiar caché de extensiones
echo "🧹 4/6 Limpiando caché de extensiones..."
rm -rf ~/.vscode-server/data/CachedExtensionVSIXs/* 2>/dev/null
rm -rf ~/.vscode-server/data/CachedData/* 2>/dev/null
rm -rf ~/.vscode-server/extensions/.obsolete 2>/dev/null
echo "   ✓ Caché de extensiones limpiado"

# 5. Limpiar workspace storage antiguo
echo "🧹 5/6 Limpiando workspace storage..."
# Eliminar workspaces no usados hace más de 7 días
find ~/.vscode-server/data/User/workspaceStorage -type d -mtime +7 -exec rm -rf {} + 2>/dev/null
# Limpiar historiales grandes
find ~/.vscode-server/data/User/workspaceStorage -name "state.vscdb*" -size +5M -delete 2>/dev/null
echo "   ✓ Workspace storage limpiado"

# 6. Liberar memoria del sistema
echo "🧹 6/6 Liberando caché del sistema..."
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
echo "   ✓ Caché del sistema liberado"

echo ""
echo "=============================================="

# Mostrar resultado
sleep 2
VSCODE_MEM_NEW=$(ps aux | grep vscode-server | grep -v grep | awk '{sum+=$6} END {print int(sum/1024)}')
LIBERADO=$((VSCODE_MEM - VSCODE_MEM_NEW))

if [ $LIBERADO -gt 0 ]; then
    echo "✅ Liberados: ${LIBERADO} MB"
else
    echo "✅ Memoria optimizada"
fi
echo "📊 Memoria actual de VSCode: ${VSCODE_MEM_NEW} MB"
echo ""
echo "💡 TIPS para mayor optimización:"
echo "   • Cierra tabs/archivos no usados"
echo "   • Desactiva extensiones pesadas"
echo "   • Reconecta VSCode para aplicar límites de Node.js"
echo "=============================================="
