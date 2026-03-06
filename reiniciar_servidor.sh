#!/bin/bash

echo "Deteniendo servidores anteriores (Go/Python)..."
pkill -9 -f 'drone_acuatico' 2>/dev/null || true
pkill -9 -f 'servidor.py' 2>/dev/null || true
sleep 2

echo "Iniciando servidor Go..."
cd /home/admin/drone_acuatico || exit 1

nohup ./iniciar_servidor.sh > /tmp/drone_go.log 2>&1 &

sleep 4
echo "✅ Verificando procesos activos..."
pgrep -af 'drone_acuatico|iniciar_servidor.sh' || true

echo ""
echo "Servidor disponible en:"
echo "http://192.168.1.7:8080"
echo ""
echo "Logs:"
echo "tail -f /tmp/drone_go.log"
