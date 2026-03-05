#!/bin/bash
# ==================== COMPILAR DRONE ACUÁTICO ====================
# Compila el servidor Go para Raspberry Pi (ARM)
#
# Uso:
#   ./compilar.sh          # Compila para la máquina actual
#   ./compilar.sh run      # Compila y ejecuta directamente
#   ./compilar.sh cross    # Cross-compile para ARM desde otra máquina

set -e

NOMBRE="drone_acuatico"
DIRECTORIO=$(dirname "$(readlink -f "$0")")
cd "$DIRECTORIO"

# Asegurar Go en PATH
if [ -d "/usr/local/go/bin" ]; then
    export PATH=$PATH:/usr/local/go/bin
fi

# Verificar que Go está instalado
if ! command -v go &>/dev/null; then
    echo "Go no está instalado. Ejecuta ./iniciar_servidor.sh para instalarlo automáticamente."
    exit 1
fi

echo "============================================"
echo "  Compilando Drone Acuático (Go)"
echo "  $(go version)"
echo "============================================"

if [ "$1" = "cross" ]; then
    echo "Cross-compilando para ARM (Raspberry Pi)..."
    GOOS=linux GOARCH=arm GOARM=7 go build -o "$NOMBRE" .
    echo "Compilado: $NOMBRE (ARM)"

elif [ "$1" = "run" ]; then
    echo "Compilando..."
    go build -o "$NOMBRE" .
    echo "Compilado: $NOMBRE"
    echo ""
    echo "Ejecutando..."
    chmod +x "$NOMBRE"
    ./"$NOMBRE"

else
    echo "Compilando para máquina actual..."
    go build -o "$NOMBRE" .
    echo ""
    echo "Compilado exitosamente: $NOMBRE"
    echo ""
    echo "Para ejecutar:"
    echo "  ./$NOMBRE"
fi

echo "============================================"
