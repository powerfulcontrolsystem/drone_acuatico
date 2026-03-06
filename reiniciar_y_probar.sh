#!/bin/bash

echo "═══════════════════════════════════════════════════════════════"
echo "REINICIAR SERVIDOR Y PROBAR VICTRON"
echo "═══════════════════════════════════════════════════════════════"

# Detener servidor anterior
echo ""
echo "[1/4] Deteniendo servidor anterior..."
pkill -9 -f 'drone_acuatico' 2>/dev/null || true
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

# Reiniciar servidor Go
echo ""
echo "[3/4] Iniciando servidor..."
nohup ./iniciar_servidor.sh > /tmp/servidor.log 2>&1 &

sleep 3

# Verificar que está corriendo
echo ""
echo "[4/4] Verificando servidor..."
if pgrep -f 'drone_acuatico' > /dev/null; then
    SERVIDOR_PID=$(pgrep -f 'drone_acuatico' | head -1)
    echo "✅ Servidor Go iniciado (PID: $SERVIDOR_PID)"
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
