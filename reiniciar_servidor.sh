#!/bin/bash

echo "Deteniendo servidor anterior..."
pkill -9 -f 'servidor.py' 2>/dev/null || true
sleep 2

echo "Iniciando servidor..."
cd /home/admin/drone_acuatico
source venv_pi/bin/activate

echo "✅ Servidor iniciándose..."
python3 servidor.py &

sleep 3
echo "✅ Verificando si está corriendo..."
ps aux | grep servidor.py | grep -v grep

echo ""
echo "Servidor disponible en:"
echo "http://192.168.1.7:8080"
