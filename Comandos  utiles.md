## iniciar servidor
pkill -f "servidor.py" 2>/dev/null || true; bash "/home/admin/drone acuatico/iniciar_servidor.sh"



### Desactivar PowerSave WiFi (PERMANENTE - después de reiniciar)
echo "options brcmfmac power_save=0" | sudo tee /etc/modprobe.d/brcmfmac.conf
sudo reboot

### Ver estado de PowerSave WiFi
iw wlan0 get power_save

### Ver conexión WiFi detallada
iw wlan0 link

### Monitorear conexión en tiempo real
watch -n 1 "iw wlan0 link"

## actualizacion del repositorio
# Opción 1: Sin mensaje (usa timestamp automático)
./subir_cambios_a_repositorio.sh

# Opción 2: Con mensaje personalizado
./subir_cambios_a_repositorio.sh "Arreglo de bugs en control de motores"