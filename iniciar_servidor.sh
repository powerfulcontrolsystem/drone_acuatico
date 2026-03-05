#!/bin/bash
# ===================================================================
# Script de inicio del Servidor Drone Acuático (Go)
# Detecta e instala automáticamente todo lo necesario:
#   - Go (compilador)
#   - ffmpeg (cámaras RTSP→HLS)
#   - pigpio (motores PWM)
#   - curl, nmcli, stty
# Luego compila y ejecuta el servidor
# ===================================================================

set -e

cd "$(dirname "$(readlink -f "$0")")" || exit 1
DIRECTORIO="$(pwd)"
NOMBRE="drone_acuatico"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}   SERVIDOR DRONE ACUÁTICO - CONTROL REMOTO WEB    ${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""

# ==================== FUNCIONES ====================

verificar_comando() {
    command -v "$1" &>/dev/null
}

instalar_paquete() {
    local paquete="$1"
    if dpkg -l "$paquete" 2>/dev/null | grep -q "^ii"; then
        return 0
    fi

    echo -e "${YELLOW}   Instalando $paquete...${NC}"

    if [ "$paquete" = "pigpio" ]; then
        if sudo apt-get install -y pigpio; then
            return 0
        fi
        echo -e "${YELLOW}   'pigpio' no disponible, probando 'pigpio-tools'...${NC}"
        sudo apt-get install -y pigpio-tools
        return $?
    fi

    sudo apt-get install -y "$paquete"
    return $?
}

# ==================== 1. DEPENDENCIAS DEL SISTEMA ====================

echo -e "${YELLOW}[1/5] Verificando dependencias del sistema...${NC}"

NECESITA_APT_UPDATE=false
PAQUETES_FALTANTES=""

# ffmpeg: necesario para cámaras RTSP→HLS
if ! verificar_comando ffmpeg; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES ffmpeg"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ ffmpeg${NC}"
fi

# pigpio: necesario para motores PWM brushless
if ! verificar_comando pigpiod; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES pigpio"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ pigpio${NC}"
fi

# curl: fallback para test de velocidad de red
if ! verificar_comando curl; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES curl"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ curl${NC}"
fi

# nmcli: para información WiFi
if ! verificar_comando nmcli; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES network-manager"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ nmcli${NC}"
fi

# stty: para configurar puertos serial (GPS, Victron)
if ! verificar_comando stty; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES coreutils"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ stty${NC}"
fi

# i2c-tools: para la brújula QMC5883L
if ! verificar_comando i2cdetect; then
    PAQUETES_FALTANTES="$PAQUETES_FALTANTES i2c-tools"
    NECESITA_APT_UPDATE=true
else
    echo -e "${GREEN}   ✓ i2c-tools${NC}"
fi

if [ -n "$PAQUETES_FALTANTES" ]; then
    echo -e "${YELLOW}   Paquetes faltantes:${RED}$PAQUETES_FALTANTES${NC}"

    echo -e "${YELLOW}   Verificando permisos sudo...${NC}"
    if ! sudo -n true 2>/dev/null; then
        echo -e "${YELLOW}   Se requiere contraseña sudo para instalar dependencias.${NC}"
        sudo -v
    fi

    if $NECESITA_APT_UPDATE; then
        echo -e "${YELLOW}   Actualizando repositorios...${NC}"
        sudo apt-get update
    fi
    for paq in $PAQUETES_FALTANTES; do
        if ! instalar_paquete "$paq"; then
            echo -e "${RED}   ✗ Error instalando '$paq'${NC}"
            echo -e "${YELLOW}   Instálalo manualmente y vuelve a ejecutar:${NC}"
            echo -e "${YELLOW}     sudo apt-get install -y $paq${NC}"
            exit 1
        fi
    done
    echo -e "${GREEN}   ✓ Paquetes del sistema instalados${NC}"
else
    echo -e "${GREEN}   ✓ Todas las dependencias del sistema presentes${NC}"
fi

# Asegurar que pigpiod esté corriendo (necesario para motores PWM)
if verificar_comando pigpiod; then
    if ! pgrep -x pigpiod &>/dev/null; then
        echo -e "${YELLOW}   Iniciando pigpiod...${NC}"
        sudo pigpiod 2>/dev/null || true
    fi
    echo -e "${GREEN}   ✓ pigpiod activo${NC}"
fi

# Habilitar I2C si no está habilitado (para brújula)
if [ ! -e /dev/i2c-1 ]; then
    echo -e "${YELLOW}   ⚠ I2C no habilitado. Habilitando...${NC}"
    sudo raspi-config nonint do_i2c 0 2>/dev/null || true
    if [ -e /dev/i2c-1 ]; then
        echo -e "${GREEN}   ✓ I2C habilitado${NC}"
    else
        echo -e "${YELLOW}   ⚠ I2C no disponible (brújula no funcionará)${NC}"
    fi
fi
echo ""

# ==================== 2. INSTALAR GO ====================

echo -e "${YELLOW}[2/5] Verificando Go...${NC}"

# Asegurar que /usr/local/go/bin esté en PATH
if [ -d "/usr/local/go/bin" ]; then
    export PATH=$PATH:/usr/local/go/bin
fi

if verificar_comando go; then
    GO_VERSION=$(go version 2>/dev/null | grep -oP 'go\K[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
    echo -e "${GREEN}   ✓ Go $GO_VERSION instalado${NC}"
else
    echo -e "${YELLOW}   Go no encontrado. Instalando...${NC}"

    # Detectar arquitectura
    ARCH=$(uname -m)
    case "$ARCH" in
        armv7l|armv6l)
            GO_ARCH="armv6l"
            ;;
        aarch64)
            GO_ARCH="arm64"
            ;;
        x86_64)
            GO_ARCH="amd64"
            ;;
        *)
            echo -e "${RED}   ✗ Arquitectura no soportada: $ARCH${NC}"
            echo -e "${YELLOW}   Instala Go manualmente: https://go.dev/dl/${NC}"
            exit 1
            ;;
    esac

    GO_LATEST="1.22.5"
    GO_TARBALL="go${GO_LATEST}.linux-${GO_ARCH}.tar.gz"
    GO_URL="https://go.dev/dl/${GO_TARBALL}"

    echo -e "${YELLOW}   Descargando Go $GO_LATEST para $ARCH...${NC}"
    cd /tmp

    # Descargar
    if verificar_comando wget; then
        wget -q --show-progress "$GO_URL" -O "$GO_TARBALL"
    elif verificar_comando curl; then
        curl -Lo "$GO_TARBALL" "$GO_URL"
    else
        # Instalar wget primero
        sudo apt-get install -y -qq wget 2>/dev/null
        wget -q --show-progress "$GO_URL" -O "$GO_TARBALL"
    fi

    if [ ! -f "$GO_TARBALL" ] || [ ! -s "$GO_TARBALL" ]; then
        echo -e "${YELLOW}   Descarga directa falló. Intentando desde apt...${NC}"
        sudo apt-get update -qq 2>/dev/null
        sudo apt-get install -y -qq golang 2>/dev/null
        if verificar_comando go; then
            echo -e "${GREEN}   ✓ Go instalado desde apt${NC}"
        else
            echo -e "${RED}   ✗ No se pudo instalar Go${NC}"
            echo -e "${YELLOW}   Instálalo manualmente: https://go.dev/dl/${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}   Instalando Go en /usr/local/go...${NC}"
        sudo rm -rf /usr/local/go
        sudo tar -C /usr/local -xzf "$GO_TARBALL"
        rm -f "$GO_TARBALL"

        # Configurar PATH permanentemente
        if ! grep -q '/usr/local/go/bin' ~/.profile 2>/dev/null; then
            echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.profile
        fi
        if ! grep -q '/usr/local/go/bin' ~/.bashrc 2>/dev/null; then
            echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
        fi
        export PATH=$PATH:/usr/local/go/bin

        if verificar_comando go; then
            GO_VERSION=$(go version | grep -oP 'go\K[0-9]+\.[0-9]+(\.[0-9]+)?' | head -1)
            echo -e "${GREEN}   ✓ Go $GO_VERSION instalado correctamente${NC}"
        else
            echo -e "${RED}   ✗ Error: Go instalado pero no accesible${NC}"
            echo -e "${YELLOW}   Ejecuta: source ~/.profile && ./iniciar_servidor.sh${NC}"
            exit 1
        fi
    fi

    cd "$DIRECTORIO"
fi
echo ""

# ==================== 3. ESTRUCTURA DEL PROYECTO ====================

echo -e "${YELLOW}[3/5] Verificando estructura del proyecto...${NC}"

# Carpetas necesarias
mkdir -p hls/cam1 hls/cam2
mkdir -p base_de_datos
mkdir -p paginas

# Verificar todos los archivos Go fuente necesarios
ARCHIVOS_GO="main.go servidor.go websocket.go base_datos.go hardware.go camera_stream.go gps.go brujula.go victron.go"
FALTANTES=""
for archivo in $ARCHIVOS_GO; do
    if [ ! -f "$archivo" ]; then
        FALTANTES="$FALTANTES $archivo"
    fi
done

if [ -n "$FALTANTES" ]; then
    echo -e "${RED}   ✗ Archivos Go faltantes:${FALTANTES}${NC}"
    echo -e "${RED}   El código fuente está incompleto${NC}"
    exit 1
fi
echo -e "${GREEN}   ✓ Archivos fuente Go completos ($(echo $ARCHIVOS_GO | wc -w) archivos)${NC}"

# Verificar go.mod
if [ ! -f "go.mod" ]; then
    echo -e "${YELLOW}   Creando go.mod...${NC}"
    go mod init drone_acuatico
fi
echo -e "${GREEN}   ✓ go.mod presente${NC}"

# Verificar páginas HTML
PAGINAS_ENCONTRADAS=$(find paginas -name "*.html" 2>/dev/null | wc -l)
echo -e "${GREEN}   ✓ $PAGINAS_ENCONTRADAS páginas HTML en paginas/${NC}"

echo -e "${GREEN}   ✓ Estructura del proyecto correcta${NC}"
echo ""

# ==================== 4. COMPILAR ====================

echo -e "${YELLOW}[4/5] Compilando servidor...${NC}"

# Solo recompilar si el binario no existe o los fuentes son más nuevos
NECESITA_COMPILAR=false
if [ ! -f "$NOMBRE" ]; then
    NECESITA_COMPILAR=true
else
    # Verificar si algún .go es más nuevo que el binario
    for archivo in *.go; do
        if [ "$archivo" -nt "$NOMBRE" ]; then
            NECESITA_COMPILAR=true
            break
        fi
    done
fi

if $NECESITA_COMPILAR; then
    echo -e "${YELLOW}   Compilando...${NC}"
    go build -o "$NOMBRE" . 2>&1
    if [ $? -ne 0 ]; then
        echo -e "${RED}   ✗ Error de compilación${NC}"
        exit 1
    fi
    chmod +x "$NOMBRE"
    TAMANO=$(du -h "$NOMBRE" | cut -f1)
    echo -e "${GREEN}   ✓ Compilado exitosamente ($TAMANO)${NC}"
else
    TAMANO=$(du -h "$NOMBRE" | cut -f1)
    echo -e "${GREEN}   ✓ Binario actualizado ($TAMANO), no necesita recompilar${NC}"
fi
echo ""

# ==================== 5. EJECUTAR ====================

echo -e "${YELLOW}[5/5] Iniciando servidor...${NC}"

# Matar procesos previos del servidor
pkill -f "./$NOMBRE" 2>/dev/null || true
pkill -f "servidor.py" 2>/dev/null || true
sleep 1

# Obtener IP local para mostrar URL correcta
IP_LOCAL=$(hostname -I 2>/dev/null | awk '{print $1}')
if [ -z "$IP_LOCAL" ]; then
    IP_LOCAL="0.0.0.0"
fi

echo ""
echo -e "${GREEN}===================================================${NC}"
echo -e "${GREEN}   ✓ Servidor: http://${IP_LOCAL}:8080${NC}"
echo -e "${GREEN}   ✓ Binario:  ./$NOMBRE${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
echo -e "${YELLOW}Presiona Ctrl+C para detener${NC}"
echo ""

# Ejecutar el servidor
./"$NOMBRE"
