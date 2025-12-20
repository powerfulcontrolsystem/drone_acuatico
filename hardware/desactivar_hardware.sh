#!/bin/bash
# Script para desactivar hardware innecesario y liberar RAM
# Ejecutar como root: sudo bash desactivar_hardware.sh

echo "=== OPTIMIZACIÓN DE HARDWARE RASPBERRY PI ==="
echo "Este script desactivará hardware no utilizado para liberar RAM"
echo ""

# Desactivar WiFi (solo si no lo necesitas)
echo "1. Desactivando WiFi..."
rfkill block wifi
iwconfig wlan0 txpower off 2>/dev/null
echo "   WiFi desactivado"

# Desactivar Bluetooth
echo "2. Desactivando Bluetooth..."
systemctl stop bluetooth
systemctl disable bluetooth
rfkill block bluetooth
echo "   Bluetooth desactivado"

# Desactivar audio (ALSA/PulseAudio)
echo "3. Desactivando servicios de audio..."
systemctl stop alsa-restore
systemctl disable alsa-restore
systemctl stop alsa-state
systemctl disable alsa-state
killall pulseaudio 2>/dev/null
echo "   Audio desactivado"

# Desactivar servicios innecesarios
echo "4. Desactivando servicios innecesarios..."
services=(
    "avahi-daemon"          # mDNS
    "triggerhappy"          # Hotkey daemon
    "cups"                  # Impresión
    "cups-browsed"          # Navegación de impresoras
    "ModemManager"          # Modem
    "wpa_supplicant"        # WiFi (si no lo usas)
)

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        systemctl stop "$service"
        systemctl disable "$service"
        echo "   - $service desactivado"
    fi
done

# Configurar swappiness para reducir uso de swap
echo "5. Optimizando uso de swap..."
sysctl vm.swappiness=10
echo "vm.swappiness=10" >> /etc/sysctl.conf
echo "   Swappiness configurado a 10"

# Limpiar caché de paquetes
echo "6. Limpiando caché del sistema..."
apt-get clean
apt-get autoclean
echo "   Caché limpiado"

# Desactivar módulos del kernel no utilizados
echo "7. Agregando módulos a blacklist..."
cat >> /etc/modprobe.d/raspi-blacklist.conf << EOF
# Módulos desactivados para ahorrar RAM
blacklist snd_bcm2835
blacklist brcmfmac
blacklist brcmutil
blacklist btbcm
blacklist hci_uart
EOF
echo "   Módulos agregados a blacklist"

# Configurar config.txt para desactivar hardware
echo "8. Configurando /boot/firmware/config.txt..."
CONFIG_FILE="/boot/firmware/config.txt"
if [ -f "$CONFIG_FILE" ]; then
    # Backup
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
    
    # Agregar configuraciones si no existen
    grep -q "dtoverlay=disable-wifi" "$CONFIG_FILE" || echo "dtoverlay=disable-wifi" >> "$CONFIG_FILE"
    grep -q "dtoverlay=disable-bt" "$CONFIG_FILE" || echo "dtoverlay=disable-bt" >> "$CONFIG_FILE"
    grep -q "dtparam=audio=off" "$CONFIG_FILE" || echo "dtparam=audio=off" >> "$CONFIG_FILE"
    
    echo "   config.txt actualizado (backup en ${CONFIG_FILE}.backup)"
else
    echo "   ADVERTENCIA: No se encontró $CONFIG_FILE"
fi

echo ""
echo "=== OPTIMIZACIÓN COMPLETADA ==="
echo "Se recomienda reiniciar el sistema para aplicar todos los cambios:"
echo "  sudo reboot"
echo ""
echo "Para revertir los cambios:"
echo "  - WiFi: rfkill unblock wifi"
echo "  - Bluetooth: systemctl start bluetooth && systemctl enable bluetooth"
echo "  - Restaurar config.txt desde el backup"
