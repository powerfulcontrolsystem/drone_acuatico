#!/bin/bash
# Script para subir automáticamente cambios a GitHub
# Uso: bash subir_github.sh [mensaje opcional]

cd "/home/admin/drone acuatico"

echo "🔍 Verificando cambios en el repositorio..."
echo ""

# Verificar si hay cambios
if [[ -z $(git status -s) ]]; then
    echo "✅ No hay cambios para subir. Todo está actualizado."
    exit 0
fi

echo "📝 Archivos modificados:"
git status -s
echo ""

# Agregar todos los archivos (excepto los del .gitignore)
echo "➕ Agregando archivos al staging..."
git add .

# Crear mensaje de commit
if [ -z "$1" ]; then
    # Si no se proporciona mensaje, usar fecha y hora
    MENSAJE="Backup automático - $(date '+%Y-%m-%d %H:%M:%S')"
else
    # Usar el mensaje proporcionado
    MENSAJE="$1"
fi

echo "💾 Haciendo commit: $MENSAJE"
git commit -m "$MENSAJE"

# Verificar si hay remote configurado
if ! git remote get-url origin &> /dev/null; then
    echo ""
    echo "❌ ERROR: No hay repositorio remoto configurado."
    echo "Configúralo con:"
    echo "   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git"
    echo "   git branch -M main"
    exit 1
fi

# Subir a GitHub
echo "☁️  Subiendo a GitHub..."
if git push; then
    echo ""
    echo "✅ ¡Cambios subidos exitosamente a GitHub!"
    echo "📊 Resumen del commit:"
    git log -1 --oneline
else
    echo ""
    echo "❌ ERROR: No se pudo subir a GitHub."
    echo "Verifica tu conexión a internet y credenciales."
    exit 1
fi

echo ""
echo "🎉 Proceso completado"
