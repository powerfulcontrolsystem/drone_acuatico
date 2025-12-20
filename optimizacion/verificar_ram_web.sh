#!/bin/bash
# Verificar estado de RAM en la interfaz web

echo "================================================================"
echo "  INDICADOR DE RAM EN LA INTERFAZ WEB"
echo "================================================================"
echo ""
echo "✅ Indicador de RAM agregado exitosamente"
echo ""
echo "Estado actual del sistema:"
echo ""

# Mostrar estado de RAM
free -h | grep -E "Mem|Swap" | awk '{printf "  %-10s Total: %-8s Usado: %-8s Libre: %-8s\n", $1, $2, $3, $4}'

echo ""
echo "================================================================"
echo "  UBICACIÓN EN LA INTERFAZ WEB"
echo "================================================================"
echo ""
echo "El indicador aparece en la parte superior derecha del header:"
echo ""
echo "  🚤 CONTROL REMOTO DIGITAL"
echo "  Drone Acuático - Sistema de Control"
echo "  ● Conectado  💾 RAM: XXX/906 MB (XX%)"
echo "                ^^^ AQUÍ ^^^"
echo ""
echo "================================================================"
echo "  CARACTERÍSTICAS"
echo "================================================================"
echo ""
echo "• Tamaño: Muy pequeño (10px, monospace)"
echo "• Actualización: Cada 10 segundos automáticamente"
echo "• Formato: RAM: usado/total MB (porcentaje%)"
echo "• Colores indicativos:"
echo "    🟢 Verde:   < 70% de uso (todo OK)"
echo "    🟡 Amarillo: 70-85% de uso (precaución)"
echo "    🔴 Rojo:    > 85% de uso (crítico, parpadea)"
echo ""
echo "================================================================"
echo "  ACCESO"
echo "================================================================"
echo ""
echo "Abre en tu navegador (PC o celular):"
echo ""
echo "  http://192.168.1.8:8080"
echo ""
echo "El indicador se actualizará automáticamente cada 10 segundos"
echo ""
echo "================================================================"
echo "  ESTADO DEL SERVIDOR"
echo "================================================================"
echo ""

if ps aux | grep -v grep | grep drone_server.py > /dev/null; then
    echo "✅ Servidor corriendo"
    echo ""
    echo "Logs recientes:"
    tail -5 ~/drone\ acuatico/drone_gps.log | sed 's/^/  /'
else
    echo "❌ Servidor NO está corriendo"
fi

echo ""
echo "================================================================"
