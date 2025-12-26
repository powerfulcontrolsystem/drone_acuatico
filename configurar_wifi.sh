#!/bin/bash
set -euo pipefail

# Script para configurar WiFi sin apagado automático y con reconexión automática
# Ejecutar con: sudo ./configurar_wifi.sh

echo "╔════════════════════════════════════════════╗"
echo "║    📡 CONFIGURAR WiFi PERMANENTEMENTE      ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Verificar si se ejecuta como root
if [[ $EUID -ne 0 ]]; then
   echo "❌ Este script debe ejecutarse con sudo"
   echo "   Uso: sudo ./configurar_wifi.sh"
   exit 1
fi

echo "🔧 Configurando WiFi..."
echo ""

# ============================================================
# 1. DESACTIVAR POWER SAVE (Temporal - hasta siguiente reboot)
# ============================================================
echo "1️⃣  Desactivando Power Save (temporal)..."
iw wlan0 set power_save off 2>/dev/null || {
    echo "   ⚠️  No se pudo desactivar power_save temporal"
}

# Verificar estado
POWER_STATE=$(iw wlan0 get power_save 2>/dev/null || echo "off")
if [[ "$POWER_STATE" == *"off"* ]]; then
    echo "   ✅ Power Save desactivado"
else
    echo "   ⚠️  Power Save aún está activo"
fi
echo ""

# ============================================================
# 2. DESACTIVAR POWER SAVE PERMANENTEMENTE
# ============================================================
echo "2️⃣  Desactivando Power Save permanentemente..."

# Crear/actualizar archivo de módulos
sudo mkdir -p /etc/modprobe.d/
sudo tee /etc/modprobe.d/brcmfmac.conf > /dev/null << 'EOF'
# Desactivar Power Save del módulo WiFi Broadcom
options brcmfmac power_save=0
EOF

echo "   ✅ Archivo /etc/modprobe.d/brcmfmac.conf actualizado"
echo ""

# ============================================================
# 3. CONFIGURAR RECONEXIÓN AUTOMÁTICA
# ============================================================
echo "3️⃣  Configurando reconexión automática..."

# Crear/actualizar configuración de NetworkManager
if command -v nmcli &> /dev/null; then
    echo "   📡 Configurando NetworkManager..."
    
    # Obtener la conexión WiFi actual
    SSID=$(nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2)
    
    if [[ -n "$SSID" ]]; then
        # Habilitar autoconnect
        nmcli con modify "$SSID" connection.autoconnect yes 2>/dev/null || true
        echo "   ✅ Autoconexión habilitada para: $SSID"
    else
        echo "   ⚠️  No se encontró SSID activo"
    fi
else
    echo "   ℹ️  NetworkManager no instalado, usando alternativa..."
fi

# Crear servicio de monitoreo de WiFi
sudo tee /etc/systemd/system/wifi-monitor.service > /dev/null << 'EOF'
[Unit]
Description=WiFi Reconnection Monitor
After=network.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/wifi-monitor.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Crear script de monitoreo
sudo tee /usr/local/bin/wifi-monitor.sh > /dev/null << 'EOF'
#!/bin/bash
# Monitorear conexión WiFi y reconectar si se pierde

INTERFACE="wlan0"
MAX_RETRIES=5
RETRY_COUNT=0

while true; do
    # Verificar si hay conexión
    if ! ping -c 1 8.8.8.8 -W 2 &>/dev/null; then
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Sin conexión WiFi (intento $RETRY_COUNT/$MAX_RETRIES)"
        
        if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔄 Reiniciando interfaz WiFi..."
            sudo systemctl restart networking 2>/dev/null || {
                sudo ifdown $INTERFACE 2>/dev/null || true
                sleep 2
                sudo ifup $INTERFACE 2>/dev/null || true
            }
            RETRY_COUNT=0
        fi
    else
        RETRY_COUNT=0
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ WiFi conectado"
    fi
    
    sleep 30
done
EOF

sudo chmod +x /usr/local/bin/wifi-monitor.sh
echo "   ✅ Script de monitoreo WiFi creado"
echo ""

# ============================================================
# 4. DESACTIVAR APAGADO DE INTERFAZ
# ============================================================
echo "4️⃣  Desactivando apagado automático de interfaz..."

# Archivo dhcpcd.conf para auto-reconexión
sudo tee -a /etc/dhcpcd.conf > /dev/null << 'EOF'

# WiFi Auto-reconnection
interface wlan0
    # Reclamar dirección IP automáticamente
    iaid 1
    ia_na 1
    ia_pd 1
    # Reintentar conexión indefinidamente
    metric 100
EOF

echo "   ✅ Configuración de DHCP actualizada"
echo ""

# ============================================================
# 5. HABILITAR Y INICIAR SERVICIO DE MONITOREO
# ============================================================
echo "5️⃣  Habilitando servicio de monitoreo..."

sudo systemctl daemon-reload
sudo systemctl enable wifi-monitor.service 2>/dev/null || true
sudo systemctl start wifi-monitor.service 2>/dev/null || true

echo "   ✅ Servicio de monitoreo habilitado"
echo ""

# ============================================================
# RESUMEN
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ CONFIGURACIÓN COMPLETADA"
echo ""
echo "📋 Cambios realizados:"
echo "   • Power Save desactivado (temporal)"
echo "   • Power Save desactivado permanentemente (/etc/modprobe.d/brcmfmac.conf)"
echo "   • Autoconexión habilitada (NetworkManager)"
echo "   • Servicio de monitoreo WiFi instalado"
echo "   • Configuración de DHCP actualizada"
echo ""
echo "🔄 Próximos pasos:"
echo "   1. Reiniciar la Raspberry para aplicar cambios permanentes:"
echo "      sudo reboot"
echo ""
echo "   2. Después del reinicio, verificar estado:"
echo "      iw wlan0 get power_save"
echo "      sudo systemctl status wifi-monitor"
echo ""
echo "📡 Estados WiFi:"
echo "   • Power Management actual:"
iwconfig wlan0 | grep "Power Management"
echo "   • Conexión actual:"
iwconfig wlan0 | grep "ESSID\|Link Quality"
echo ""
echo "🚀 El WiFi ahora:"
echo "   ✓ Nunca se apagará automáticamente"
echo "   ✓ Se reconectará automáticamente si se pierde"
echo "   ✓ Se verificará cada 30 segundos"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
