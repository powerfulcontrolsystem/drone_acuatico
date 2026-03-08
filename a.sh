#!/bin/bash
set -euo pipefail

# Script para subir cambios del proyecto drone acuático al repositorio GitHub
# Uso:
#   ./subir_cambios_a_repositorio.sh [mensaje opcional]
# Si no se proporciona mensaje, se usará un timestamp.

ROOT="/home/admin/drone_acuatico"
cd "$ROOT"

echo "╔════════════════════════════════════════════╗"
echo "║    📤 SUBIR CAMBIOS A REPOSITORIO         ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Obtener información de git
BRANCH=$(git branch --show-current)
REMOTE=$(git remote get-url origin 2>/dev/null || echo "No configurado")

echo "📍 Ubicación: $ROOT"
echo "🌿 Rama: $BRANCH"
echo "📦 Repositorio: $REMOTE"
echo ""

# Verificar si hay cambios
STATUS=$(git status --porcelain)

if [[ -z "$STATUS" ]]; then
    echo "✅ No hay cambios para subir."
    echo ""
    exit 0
fi

echo "📝 Cambios detectados:"
echo "$STATUS" | head -n 20
TOTAL_FILES=$(echo "$STATUS" | wc -l)
if [ $TOTAL_FILES -gt 20 ]; then
    echo "   ... y $((TOTAL_FILES - 20)) archivos más"
fi
echo ""

# Agregar archivos
echo "➕ Agregando archivos..."
git add .

# Crear mensaje de commit
if [ -z "${1:-}" ]; then
    MENSAJE="Actualización automática - $(date '+%Y-%m-%d %H:%M:%S')"
else
    MENSAJE="$1"
fi

echo "💬 Mensaje de commit: $MENSAJE"
echo ""

# Crear commit
echo "💾 Creando commit..."
if git commit -m "$MENSAJE"; then
    echo "   ✅ Commit creado exitosamente"
else
    echo "   ⚠️  No se pudo crear commit"
    exit 1
fi
echo ""

# Verificar conexión con repositorio remoto
echo "🔗 Verificando conexión con repositorio remoto..."
if ! git remote get-url origin &>/dev/null; then
    echo "❌ ERROR: No hay repositorio remoto configurado."
    exit 1
fi

# Hacer pull antes de push (por si hay cambios remotos)
echo "⬇️  Sincronizando cambios remotos..."
git fetch --all --prune
if ! git pull --rebase origin "$BRANCH" 2>/dev/null; then
    echo "   ⚠️  No se pudieron sincronizar cambios remotos (puede ser normal)"
fi
echo ""

# Hacer push
echo "☁️  Subiendo cambios a GitHub..."
if git push origin "$BRANCH"; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✅ ¡Cambios subidos exitosamente!"
    echo ""
    echo "📊 Resumen:"
    echo "   • Archivos: $TOTAL_FILES modificados"
    echo "   • Commit: $MENSAJE"
    echo "   • Rama: $BRANCH"
    echo "   • Repositorio: $REMOTE"
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║          ✅ PROCESO COMPLETADO            ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
    exit 0
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "❌ Error al subir cambios a GitHub"
    echo "   Posibles causas:"
    echo "   • Problemas de conexión de internet"
    echo "   • Credenciales de GitHub inválidas"
    echo "   • Permisos insuficientes en el repositorio"
    echo ""
    echo "💡 Intenta:"
    echo "   git push origin $BRANCH"
    echo ""
    exit 1
fi
