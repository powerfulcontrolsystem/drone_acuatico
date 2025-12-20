#!/bin/bash
set -euo pipefail

# Script para actualizar (backup) el repositorio desde la Raspberry hacia GitHub
# Uso:
#   ./"Actualizar repositorio.sh" [mensaje opcional]
# Si no se proporciona mensaje, se usará un timestamp.

ROOT="/home/admin/drone acuatico"
cd "$ROOT"

echo "╔════════════════════════════════════════════╗"
echo "║    📦 ACTUALIZAR REPOSITORIO GITHUB       ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Verificar estado de RAM
RAM_INFO=$(free -m | grep Mem)
RAM_TOTAL=$(echo "$RAM_INFO" | awk '{print $2}')
RAM_USADO=$(echo "$RAM_INFO" | awk '{print $3}')
RAM_PORCENTAJE=$((RAM_USADO * 100 / RAM_TOTAL))

if [ $RAM_PORCENTAJE -lt 70 ]; then
    COLOR="\033[0;32m"
    ESTADO="🟢 Óptimo"
elif [ $RAM_PORCENTAJE -lt 85 ]; then
    COLOR="\033[0;33m"
    ESTADO="🟡 Aceptable"
else
    COLOR="\033[0;31m"
    ESTADO="🔴 Crítico"
fi

echo -e "📊 RAM: ${COLOR}${RAM_USADO}/${RAM_TOTAL} MB (${RAM_PORCENTAJE}%)${COLOR}\033[0m ${ESTADO}"
echo ""

# Si RAM alta, limpiar un poco
if [ $RAM_PORCENTAJE -ge 80 ]; then
    echo "⚠️  RAM alta detectada - Ejecutando limpieza rápida..."
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1
    rm -rf /tmp/*.tmp /tmp/vscode-* /tmp/code-* 2>/dev/null
    find ~/.vscode-server/data/logs -name "*.log" -size +5M -delete 2>/dev/null
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

STATUS=$(git status -s)
WORKING_CLEAN=0
TOTAL_FILES=0
MENSAJE=""
BRANCH=$(git branch --show-current)

if [[ -z "$BRANCH" ]]; then
    BRANCH="main"
fi

if [[ -z "$STATUS" ]]; then
    WORKING_CLEAN=1
    echo "✅ No hay cambios en el working tree."
else
    echo "📝 Archivos modificados:"
    echo "$STATUS" | head -n 20
    TOTAL_FILES=$(echo "$STATUS" | wc -l)
    if [ $TOTAL_FILES -gt 20 ]; then
        echo "   ... y $((TOTAL_FILES - 20)) archivos más"
    fi
    echo ""

    echo "➕ Agregando archivos..."
    git add .

    if [ -z "${1:-}" ]; then
        MENSAJE="Actualización - $(date '+%Y-%m-%d %H:%M:%S')"
    else
        MENSAJE="$1"
    fi
    echo "💬 Mensaje: $MENSAJE"
    echo ""

    echo "💾 Creando commit..."
    if git commit -m "$MENSAJE"; then
        echo "   ✅ Commit creado"
    else
        echo "   ⚠️  No se pudo crear commit"
        exit 1
    fi
    echo ""
fi

if ! git remote get-url origin &>/dev/null; then
    echo "❌ ERROR: No hay repositorio remoto configurado (origin)."
    exit 1
fi

UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || true)

if [[ -n "$UPSTREAM" ]]; then
    echo "[INFO] Sincronizando con remoto (pull --rebase)"
    git fetch --all --prune
    git pull --rebase origin "$BRANCH" || git pull --rebase || true
fi

echo "☁️  Subiendo a GitHub..."
if [[ -z "$UPSTREAM" ]]; then
    echo "   (Configurando upstream origin/$BRANCH)"
    PUSH_CMD=(git push --set-upstream origin "$BRANCH")
else
    PUSH_CMD=(git push)
fi

if "${PUSH_CMD[@]}"; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✅ ¡Repositorio actualizado exitosamente!"
    echo ""
    echo "📊 Resumen:"
    if [[ $WORKING_CLEAN -eq 1 ]]; then
        echo "   • Archivos: 0 (sin cambios en working tree)"
    else
        echo "   • Archivos: $TOTAL_FILES modificados"
        echo "   • Commit: $MENSAJE"
    fi
    echo "   • Rama: $BRANCH"
    RAM_FINAL=$(free -m | grep Mem | awk '{printf "%d/%d MB", $3, $2}')
    echo "   • RAM: $RAM_FINAL"
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "❌ Error al subir cambios a GitHub"
    echo "   Revisa conexión, autenticación o permisos."
    echo ""
    exit 1
fi

echo "╔════════════════════════════════════════════╗"
echo "║          ✅ PROCESO COMPLETADO            ║"
echo "╚════════════════════════════════════════════╝"

echo ""
exit 0
