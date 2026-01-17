#!/bin/bash

echo "═══════════════════════════════════════════════════════════════"
echo "REINICIAR SERVIDOR - PÁGINA NUEVA VICTRON"
echo "═══════════════════════════════════════════════════════════════"

# Detener servidor anterior
echo ""
echo "Deteniendo servidor anterior..."
pkill -9 -f 'servidor.py' 2>/dev/null || true
sleep 2

# Reiniciar servidor
echo "Iniciando servidor..."
cd /home/admin/drone_acuatico

# Activar entorno virtual
source venv_pi/bin/activate

# Iniciar en background con logs
nohup python3 servidor.py > /tmp/servidor_victron.log 2>&1 &

sleep 3

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ SERVIDOR INICIADO"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "📱 Abre en navegador:"
echo "   http://192.168.1.7:8080/energia_solar.html"
echo ""
echo "📋 Ver logs en tiempo real:"
echo "   tail -f /tmp/servidor_victron.log"
echo ""
echo "Presiona Ctrl+C para salir de los logs"
