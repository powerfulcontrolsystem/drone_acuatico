#!/bin/bash
# Script maestro: Optimizar RAM + Actualizar GitHub
# Verifica la RAM, optimiza si es necesario, y sube cambios a GitHub

cd "/home/admin/drone acuatico"

echo "╔════════════════════════════════════════════╗"
echo "║   SISTEMA DE ACTUALIZACIÓN INTELIGENTE    ║"
echo "║   Drone Acuático - GitHub Sync            ║"
echo "╔════════════════════════════════════════════╗"
echo ""

# ============================================
# PASO 1: VERIFICAR ESTADO DE RAM
# ============================================
echo "📊 PASO 1/4: Verificando RAM..."
echo ""

RAM_INFO=$(free -m | grep Mem)
RAM_TOTAL=$(echo $RAM_INFO | awk '{print $2}')
RAM_USADO=$(echo $RAM_INFO | awk '{print $3}')
RAM_LIBRE=$(echo $RAM_INFO | awk '{print $4}')
RAM_PORCENTAJE=$((RAM_USADO * 100 / RAM_TOTAL))

# Colorear según el estado
if [ $RAM_PORCENTAJE -lt 70 ]; then
    COLOR="\033[0;32m" # Verde
    ESTADO="ÓPTIMO"
elif [ $RAM_PORCENTAJE -lt 85 ]; then
    COLOR="\033[0;33m" # Amarillo
    ESTADO="ACEPTABLE"
else
    COLOR="\033[0;31m" # Rojo
    ESTADO="CRÍTICO"
fi

echo -e "${COLOR}RAM: ${RAM_USADO}/${RAM_TOTAL} MB (${RAM_PORCENTAJE}%) - ${ESTADO}\033[0m"
echo ""

# ============================================
# PASO 2: OPTIMIZAR SI ES NECESARIO
# ============================================
OPTIMIZAR=false

if [ $RAM_PORCENTAJE -ge 85 ]; then
    echo "⚠️  RAM CRÍTICA (>85%) - Optimización REQUERIDA"
    OPTIMIZAR=true
elif [ $RAM_PORCENTAJE -ge 70 ]; then
    echo "⚠️  RAM ALTA (>70%) - Optimización RECOMENDADA"
    read -p "¿Optimizar antes de continuar? (S/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        OPTIMIZAR=true
    fi
else
    echo "✅ RAM en buen estado - No requiere optimización"
fi

if [ "$OPTIMIZAR" = true ]; then
    echo ""
    echo "🔧 PASO 2/4: Optimizando sistema..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Ejecutar limpieza de VSCode Server
    echo "→ Limpiando VSCode Server..."
    bash "/home/admin/drone acuatico/optimizacion/limpiar_vscode_server.sh"
    echo ""
    
    # Ejecutar optimización agresiva de RAM
    echo "→ Ejecutando optimización agresiva..."
    bash "/home/admin/drone acuatico/optimizacion/optimizar_ram_agresivo.sh"
    echo ""
    
    # Verificar mejora
    RAM_INFO_NEW=$(free -m | grep Mem)
    RAM_USADO_NEW=$(echo $RAM_INFO_NEW | awk '{print $3}')
    RAM_PORCENTAJE_NEW=$((RAM_USADO_NEW * 100 / RAM_TOTAL))
    RAM_LIBERADA=$((RAM_USADO - RAM_USADO_NEW))
    
    if [ $RAM_LIBERADA -gt 0 ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo -e "\033[0;32m✅ Optimización exitosa: ${RAM_LIBERADA} MB liberados\033[0m"
        echo -e "   Nueva RAM: ${RAM_USADO_NEW}/${RAM_TOTAL} MB (${RAM_PORCENTAJE_NEW}%)"
    else
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "⚠️  Optimización aplicada (cambios menores)"
    fi
    
    # Pausa para revisar
    sleep 2
else
    echo ""
    echo "⏭️  PASO 2/4: Omitiendo optimización"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================
# PASO 3: VERIFICAR CAMBIOS EN GIT
# ============================================
echo "📝 PASO 3/4: Verificando cambios en Git..."
echo ""

# Verificar si hay cambios
if [[ -z $(git status -s) ]]; then
    echo "✅ No hay cambios para subir. Todo está actualizado."
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║            PROCESO COMPLETADO             ║"
    echo "╚════════════════════════════════════════════╝"
    exit 0
fi

echo "📂 Archivos modificados:"
git status -s
echo ""

# ============================================
# PASO 4: SUBIR A GITHUB
# ============================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "☁️  PASO 4/4: Subiendo cambios a GitHub..."
echo ""

# Agregar todos los archivos
echo "→ Agregando archivos al staging..."
git add .

# Crear mensaje de commit
if [ -z "$1" ]; then
    # Si no se proporciona mensaje, usar fecha y hora
    MENSAJE="Actualización automática - $(date '+%Y-%m-%d %H:%M:%S')"
else
    # Usar el mensaje proporcionado
    MENSAJE="$1"
fi

echo "→ Creando commit: $MENSAJE"
git commit -m "$MENSAJE"

# Verificar si hay remote configurado
if ! git remote get-url origin &> /dev/null; then
    echo ""
    echo "❌ ERROR: No hay repositorio remoto configurado."
    echo ""
    echo "Configúralo con:"
    echo "   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git"
    echo "   git branch -M main"
    echo ""
    exit 1
fi

# Subir a GitHub
echo "→ Sincronizando con GitHub..."
if git push; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "\033[0;32m✅ ¡Cambios subidos exitosamente a GitHub!\033[0m"
    echo ""
    
    # Mostrar estadísticas finales
    echo "📊 RESUMEN FINAL:"
    RAM_FINAL=$(free -m | grep Mem | awk '{printf "%d/%d MB (%d%%)", $3, $2, int($3/$2*100)}')
    echo "   • RAM: $RAM_FINAL"
    echo "   • Commit: $MENSAJE"
    echo "   • Rama: $(git branch --show-current)"
    echo ""
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "\033[0;31m❌ Error al subir cambios a GitHub\033[0m"
    echo ""
    echo "Verifica:"
    echo "   • Conexión a internet"
    echo "   • Autenticación de GitHub"
    echo "   • Permisos del repositorio"
    echo ""
    exit 1
fi

echo "╔════════════════════════════════════════════╗"
echo "║            PROCESO COMPLETADO             ║"
echo "╚════════════════════════════════════════════╝"
