#!/bin/bash
# Script para actualizar el repositorio de GitHub
# Uso: bash "Actualizar repositorio.sh" [mensaje opcional]

cd "/home/admin/drone acuatico"

echo "╔════════════════════════════════════════════╗"
echo "║    📦 ACTUALIZAR REPOSITORIO GITHUB       ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Verificar estado de RAM
RAM_INFO=$(free -m | grep Mem)
RAM_TOTAL=$(echo $RAM_INFO | awk '{print $2}')
RAM_USADO=$(echo $RAM_INFO | awk '{print $3}')
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

# Optimizar si RAM está muy alta
if [ $RAM_PORCENTAJE -ge 80 ]; then
    echo "⚠️  RAM alta detectada - Ejecutando optimización rápida..."
    echo ""
    
    # Limpiar cachés
    sync
    echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null 2>&1
    
    # Limpiar temporales
    rm -rf /tmp/*.tmp /tmp/vscode-* /tmp/code-* 2>/dev/null
    
    # Limpiar logs de VSCode
    find ~/.vscode-server/data/logs -name "*.log" -size +5M -delete 2>/dev/null
    
    # Verificar mejora
    RAM_USADO_NEW=$(free -m | grep Mem | awk '{print $3}')
    RAM_PORCENTAJE_NEW=$((RAM_USADO_NEW * 100 / RAM_TOTAL))
    LIBERADO=$((RAM_USADO - RAM_USADO_NEW))
    
    if [ $LIBERADO -gt 0 ]; then
        echo "✅ Liberados: ${LIBERADO} MB"
    fi
    echo "📊 RAM actual: ${RAM_USADO_NEW}/${RAM_TOTAL} MB (${RAM_PORCENTAJE_NEW}%)"
    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Verificar si hay cambios
if [[ -z $(git status -s) ]]; then
    echo "✅ No hay cambios para subir."
    echo "   El repositorio está actualizado."
    echo ""
    exit 0
fi

# Mostrar cambios
echo "📝 Archivos modificados:"
git status -s | head -n 20
TOTAL_FILES=$(git status -s | wc -l)
if [ $TOTAL_FILES -gt 20 ]; then
    echo "   ... y $((TOTAL_FILES - 20)) archivos más"
fi
echo ""

# Agregar archivos
echo "➕ Agregando archivos..."
git add .

# Crear mensaje de commit
if [ -z "$1" ]; then
    MENSAJE="Actualización - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "💬 Mensaje: $MENSAJE"
else
    MENSAJE="$1"
    echo "💬 Mensaje: $MENSAJE"
fi
echo ""

# Hacer commit
echo "💾 Creando commit..."
if git commit -m "$MENSAJE"; then
    echo "   ✅ Commit creado"
else
    echo "   ⚠️  Error al crear commit"
    exit 1
fi
echo ""

# Verificar remote
if ! git remote get-url origin &> /dev/null; then
    echo "❌ ERROR: No hay repositorio remoto configurado."
    echo ""
    echo "Configúralo con:"
    echo "   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git"
    echo "   git branch -M main"
    echo ""
    exit 1
fi

# Subir a GitHub
echo "☁️  Subiendo a GitHub..."
if git push; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "✅ ¡Repositorio actualizado exitosamente!"
    echo ""
    echo "📊 Resumen:"
    echo "   • Archivos: $TOTAL_FILES modificados"
    echo "   • Commit: $MENSAJE"
    echo "   • Rama: $(git branch --show-current)"
    RAM_FINAL=$(free -m | grep Mem | awk '{printf "%d/%d MB", $3, $2}')
    echo "   • RAM: $RAM_FINAL"
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "❌ Error al subir cambios a GitHub"
    echo ""
    echo "Verifica:"
    echo "   • Conexión a internet"
    echo "   • Autenticación de GitHub"
    echo "   • Permisos del repositorio"
    echo ""
    exit 1
fi

echo "╔════════════════════════════════════════════╗"
echo "║          ✅ PROCESO COMPLETADO            ║"
echo "╚════════════════════════════════════════════╝"
