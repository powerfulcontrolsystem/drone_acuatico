## iniciar servidor
bash "/home/admin/drone acuatico/iniciar_servidor.sh"

## subir repositorio
bash "/home/admin/drone acuatico/subir_a_repositorio.sh"

ls -la "/home/admin/drone acuatico" && git -C "/home/admin/drone acuatico" status && git -C "/home/admin/drone acuatico" remote -v && git -C "/home/admin/drone acuatico" branch -vv

## SOLUCIONES WIFI INESTABLE - NUEVOS COMANDOS

### Diagnóstico rápido del sistema (sin scripts)
uname -r && uptime -p && free -h && ps aux --sort=-%mem | head -11 && iwconfig wlan0 || echo "wlan0 no encontrado"

### Desactivar PowerSave WiFi (TEMPORAL - inmediato)
sudo iw wlan0 set power_save off

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