#!/bin/bash
# Menú de acceso rápido a herramientas de optimización y GitHub

RUTA_BASE="/home/admin/drone acuatico"

clear
echo "╔═══════════════════════════════════════════════════════╗"
echo "║         🚤 DRONE ACUÁTICO - HERRAMIENTAS             ║"
echo "║       Sistema de Optimización y Actualización        ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo ""

# Mostrar estado actual de RAM
RAM_INFO=$(free -m | grep Mem)
RAM_TOTAL=$(echo $RAM_INFO | awk '{print $2}')
RAM_USADO=$(echo $RAM_INFO | awk '{print $3}')
RAM_PORCENTAJE=$((RAM_USADO * 100 / RAM_TOTAL))

if [ $RAM_PORCENTAJE -lt 70 ]; then
    COLOR="\033[0;32m" # Verde
    ICONO="🟢"
elif [ $RAM_PORCENTAJE -lt 85 ]; then
    COLOR="\033[0;33m" # Amarillo
    ICONO="🟡"
else
    COLOR="\033[0;31m" # Rojo
    ICONO="🔴"
fi

echo -e "📊 RAM: ${COLOR}${RAM_USADO}/${RAM_TOTAL} MB (${RAM_PORCENTAJE}%)\033[0m ${ICONO}"
echo ""
echo "───────────────────────────────────────────────────────"
echo ""
echo "Selecciona una opción:"
echo ""
echo "  1. 🎯 Actualizar GitHub (con optimización inteligente)"
echo "  2. 🧹 Optimizar RAM completo (agresivo)"
echo "  3. 🔧 Limpiar VSCode Server"
echo "  4. 📊 Ver estado del sistema"
echo "  5. 📖 Ver guía de uso"
echo "  6. ❌ Salir"
echo ""
echo "───────────────────────────────────────────────────────"
read -p "Opción [1-6]: " opcion

case $opcion in
    1)
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "   ACTUALIZACIÓN INTELIGENTE DE GITHUB"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        read -p "Mensaje del commit (Enter para automático): " mensaje
        echo ""
        if [ -z "$mensaje" ]; then
            bash "$RUTA_BASE/utilidades/actualizar_github_inteligente.sh"
        else
            bash "$RUTA_BASE/utilidades/actualizar_github_inteligente.sh" "$mensaje"
        fi
        ;;
    2)
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "   OPTIMIZACIÓN AGRESIVA DE RAM"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        bash "$RUTA_BASE/optimizacion/optimizar_ram_agresivo.sh"
        ;;
    3)
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "   LIMPIEZA DE VSCODE SERVER"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        bash "$RUTA_BASE/optimizacion/limpiar_vscode_server.sh"
        ;;
    4)
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "   ESTADO DEL SISTEMA"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        echo "💾 MEMORIA:"
        free -h
        echo ""
        echo "🔝 PROCESOS QUE MÁS CONSUMEN RAM:"
        ps aux --sort=-%mem | head -n 6 | tail -n 5
        echo ""
        echo "📂 ESPACIO EN DISCO:"
        df -h / | tail -n 1
        echo ""
        echo "🌡️  TEMPERATURA CPU:"
        vcgencmd measure_temp 2>/dev/null || echo "   No disponible"
        echo ""
        ;;
    5)
        echo ""
        echo "═══════════════════════════════════════════════════════"
        echo "   GUÍA DE USO"
        echo "═══════════════════════════════════════════════════════"
        echo ""
        if [ -f "$RUTA_BASE/optimizacion/GUIA_ACTUALIZACION_GITHUB.md" ]; then
            less "$RUTA_BASE/optimizacion/GUIA_ACTUALIZACION_GITHUB.md"
        else
            echo "⚠️  Guía no encontrada"
        fi
        ;;
    6)
        echo ""
        echo "👋 ¡Hasta luego!"
        exit 0
        ;;
    *)
        echo ""
        echo "❌ Opción inválida"
        ;;
esac

echo ""
echo "───────────────────────────────────────────────────────"
read -p "Presiona Enter para continuar..."
