#!/bin/bash
# Script para optimizar VSCode Server y liberar RAM
# NOTA: Este script ha sido reemplazado por versiones mejoradas
# Ejecutar como usuario admin

echo "════════════════════════════════════════════════════"
echo "⚠️  SCRIPT DEPRECADO - Usar nueva versión mejorada"
echo "════════════════════════════════════════════════════"
echo ""
echo "Este script ha sido reemplazado por:"
echo "  📂 limpiar_vscode_server.sh (más completo)"
echo ""
echo "Ubicación:"
echo "  /home/admin/drone acuatico/optimizacion/limpiar_vscode_server.sh"
echo ""
echo "Uso recomendado:"
echo "  bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh"
echo ""
read -p "¿Ejecutar la nueva versión ahora? (S/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo "Ejecutando nueva versión..."
    echo ""
    bash "/home/admin/drone acuatico/optimizacion/limpiar_vscode_server.sh"
else
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "Ejecutando versión antigua (no recomendado)..."
    echo "════════════════════════════════════════════════════"
    echo ""
    
    # 1. Configurar VSCode Server para usar menos memoria
    echo "1. Configurando límites de memoria para VSCode Server..."
    
    VSCODE_SETTINGS="$HOME/.vscode-server/data/Machine/settings.json"
    mkdir -p "$(dirname "$VSCODE_SETTINGS")"
    
    # Crear configuración optimizada
    cat > "$VSCODE_SETTINGS" << 'EOF'
{
    "files.watcherExclude": {
        "**/.git/objects/**": true,
        "**/.git/subtree-cache/**": true,
        "**/node_modules/**": true,
        "**/venv_pi/**": true,
        "**/__pycache__/**": true,
        "**/.cache/**": true
    },
    "search.followSymlinks": false,
    "search.exclude": {
        "**/node_modules": true,
        "**/bower_components": true,
        "**/*.code-search": true,
        "**/venv_pi/**": true,
        "**/__pycache__/**": true
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
    "git.enabled": false,
    "git.autorefresh": false,
    "workbench.enableExperiments": false,
    "python.languageServer": "None",
    "files.autoSave": "off",
    "editor.quickSuggestions": false,
    "editor.parameterHints.enabled": false,
    "editor.suggest.showWords": false,
    "editor.wordBasedSuggestions": "off"
}
EOF
    
    echo "   settings.json creado en $VSCODE_SETTINGS"
    
    # 2. Desactivar extensiones innecesarias
    echo ""
    echo "2. Desactivando extensiones de VSCode Server..."
    code-server --disable-extension ms-python.python 2>/dev/null || true
    code-server --disable-extension ms-toolsai.jupyter 2>/dev/null || true
    echo "   Extensiones pesadas desactivadas"
    
    # 3. Limpiar caché de VSCode
    echo ""
    echo "3. Limpiando caché de VSCode Server..."
    rm -rf "$HOME/.vscode-server/data/CachedData/*"
    rm -rf "$HOME/.vscode-server/data/logs/*"
    rm -rf "$HOME/.vscode-server/extensions/.obsolete"
    rm -rf "$HOME/.vscode-server/data/User/workspaceStorage/*"
    echo "   Caché limpiado"
    
    # 4. Configurar límites de Node.js (VSCode usa Node)
    echo ""
    echo "4. Configurando límites de memoria de Node.js..."
    if ! grep -q "NODE_OPTIONS.*max-old-space-size" ~/.bashrc; then
        echo "export NODE_OPTIONS='--max-old-space-size=200'" >> "$HOME/.bashrc"
        echo "   Límite de Node.js configurado a 200MB"
    else
        echo "   Ya configurado previamente"
    fi
    
    echo ""
    echo "=== OPTIMIZACIÓN COMPLETADA ==="
    echo ""
    echo "IMPORTANTE: Para aplicar los cambios de Node.js:"
    echo "  source ~/.bashrc"
    echo "  Luego reconecta VSCode"
    echo ""
fi
