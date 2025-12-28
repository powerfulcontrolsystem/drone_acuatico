## iniciar servidor
pkill -f "servidor.py" 2>/dev/null || true; bash "/home/admin/drone acuatico/iniciar_servidor.sh"

bash iniciar_servidor.sh

## Ver estados de relés guardados en BD
```bash
sqlite3 ~/drone\ acuatico/drone-acuatico.db "SELECT numero, estado, datetime(fecha_actualizacion, 'localtime') as fecha FROM estado_reles ORDER BY numero"
```

## Ver tema guardado en BD
```bash
sqlite3 ~/drone\ acuatico/drone-acuatico.db "SELECT CASE WHEN tema_oscuro = 1 THEN 'Oscuro' ELSE 'Claro' END as tema, datetime(fecha_actualizacion, 'localtime') as ultima_actualizacion FROM configuracion WHERE id = 1"
```

## Conexión SSH en VS Code (sin contraseña)

### Pasos mínimos
1) Genera una clave (si no existe):
```bash
ssh-keygen -t ed25519 -C "admin@raspberry" -f ~/.ssh/id_ed25519 -N ""
```

2) Copia la clave pública a la Raspberry (IP 192.168.1.15):
```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@192.168.1.15
```

3) Configura tu `~/.ssh/config` para VS Code:
```
Host raspberry
    HostName 192.168.1.15
    User admin
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
```

4) Conecta sin pedir contraseña:
```bash
ssh raspberry
```

Nota: OpenSSH no guarda contraseñas en `~/.ssh/config`. El método de claves es el necesario para no pedir contraseña.

#### Alternativa (menos segura): usar `sshpass` con contraseña "admin"
No es posible guardar la contraseña en `~/.ssh/config`. Si necesitas usar la contraseña "admin" sin interacción, puedes instalar `sshpass` y usar:
```bash
sudo apt-get update && sudo apt-get install -y sshpass
sshpass -p "admin" ssh admin@<IP_DE_TU_RASPBERRY>

# Con alias conveniente
alias sshr="sshpass -p 'admin' ssh admin@<IP_DE_TU_RASPBERRY>"
```
Nota: `sshpass` transmite la contraseña en texto claro y es menos seguro. Preferir claves SSH.

### Verificar estado de conexión Ethernet
```bash
# Ver estado de la interfaz
ip link show eth0

# Ver estadísticas de red
ip -s link show eth0

# Ping continuo para monitorear
ping 8.8.8.8
```

## WiFi

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