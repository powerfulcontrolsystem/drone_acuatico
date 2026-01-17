#!/bin/bash

echo "═══════════════════════════════════════════════════════════════"
echo "REINICIAR SERVIDOR Y PROBAR VICTRON"
echo "═══════════════════════════════════════════════════════════════"

# Detener servidor anterior
echo ""
echo "[1/4] Deteniendo servidor anterior..."
pkill -9 -f 'servidor.py' 2>/dev/null || true
sleep 2

# Probar obtener_solar() directamente
echo ""
echo "[2/4] Probando lectura de Victron..."
cd /home/admin/drone_acuatico

# Crear script de prueba
python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '/home/admin/drone_acuatico')
from funciones import obtener_solar
import json

print("Llamando obtener_solar()...")
datos = obtener_solar()
print("\nResultado:")
print(json.dumps(datos, indent=2, default=str))

if datos.get('conectado'):
    print("\n✅ Victron CONECTADO")
else:
    print("\n❌ Victron DESCONECTADO")
PYTHON_SCRIPT

# Reiniciar servidor
echo ""
echo "[3/4] Iniciando servidor..."
source venv_pi/bin/activate
nohup python3 servidor.py > /tmp/servidor.log 2>&1 &
SERVIDOR_PID=$!

sleep 3

# Verificar que está corriendo
echo ""
echo "[4/4] Verificando servidor..."
if ps -p $SERVIDOR_PID > /dev/null; then
    echo "✅ Servidor iniciado (PID: $SERVIDOR_PID)"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "✅ SERVIDOR LISTO"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "🌐 Abre en navegador:"
    echo "   http://192.168.1.7:8080"
    echo ""
    echo "📊 Página de Energía Solar:"
    echo "   http://192.168.1.7:8080/energia_solar.html"
    echo ""
    echo "📋 Ver logs:"
    echo "   tail -f /tmp/servidor.log"
    echo ""
else
    echo "❌ Error al iniciar servidor"
    echo "Ver logs: cat /tmp/servidor.log"
    exit 1
fi
