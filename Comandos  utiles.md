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

## Ver configuración de guardado GPS automático
```bash
sqlite3 ~/drone\ acuatico/drone-acuatico.db "SELECT CASE WHEN guardar_recorrido = 1 THEN 'Activado' ELSE 'Desactivado' END as guardado_auto, frecuencia_guardado as frecuencia_segundos FROM configuracion WHERE id = 1"
```

## Conexión SSH en VS Code (sin contraseña)

### Solución para SSH que se cae (keepalive)

Configura tu `~/.ssh/config` local (en tu PC, no en la Raspberry) para mantener conexiones activas:

```
Host raspberry
    HostName 192.168.1.15
    User admin
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
    # Mantener conexión activa (evita timeouts)
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
```

Esto envía un "ping" cada 60 segundos para mantener la conexión activa.

### Pasos mínimos
1) Genera una clave (si no existe):
```bash
ssh-keygen -t ed25519 -C "admin@raspberry" -f ~/.ssh/id_ed25519 -N ""
```

2) Copia la clave pública a la Raspberry (IP 192.168.1.15):
```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub admin@192.168.1.15
```

3) Configura tu `~/.ssh/config` para VS Code (CON KEEPALIVE):
```
Host raspberry
    HostName 192.168.1.15
    User admin
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    PreferredAuthentications publickey
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
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

### Diagnosticar desconexiones SSH

#### En la Raspberry (verificar configuración del servidor SSH):
```bash
# Ver configuración de keepalive del servidor
sudo grep -E "ClientAliveInterval|ClientAliveCountMax|TCPKeepAlive" /etc/ssh/sshd_config | grep -v "^#"

# Verificar que interfaz de red se está usando
ip route

# Test de estabilidad de red
ping -c 20 8.8.8.8
```

#### En tu PC local (configurar keepalive del cliente):
Edita `~/.ssh/config` y agrega:
```
ServerAliveInterval 60
ServerAliveCountMax 3
TCPKeepAlive yes
```

#### Monitorear conexión SSH en tiempo real:
```bash
# Desde tu PC, en otra terminal mientras trabajas
watch -n 5 'ssh admin@192.168.1.15 "uptime && echo "" && ip -s link show eth0 | grep -A 2 \"RX:\""'
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

## Diagnóstico de reinicios/desconexiones

### Diagnóstico rápido (ejecutar primero)
```bash
echo "=== UPTIME ===" && uptime && echo "" && echo "=== RAM ===" && free -h && echo "" && echo "=== VOLTAJE (0x0=OK) ===" && vcgencmd get_throttled && echo "" && echo "=== TEMPERATURA ===" && vcgencmd measure_temp
```

### Ver uso de RAM
```bash
free -h
```

### Ver uptime (tiempo encendida)
```bash
uptime
```

### Ver historial de reinicios
```bash
last reboot | head -10
```

### Verificar bajo voltaje (causa común de reinicios)
```bash
# 0x0 = OK
# 0x50000 o 0x80000 = tuvo bajo voltaje en el pasado
# 0x50005 = bajo voltaje AHORA
vcgencmd get_throttled
```

### Ver temperatura actual
```bash
vcgencmd measure_temp
```

### Buscar reinicios y problemas en kernel
```bash
sudo dmesg | grep -i "undervoltage\|reboot\|restart\|shutdown"
```

### Ver logs del sistema (últimas 100 líneas)
```bash
sudo journalctl -n 100 --no-pager
```

### Ver todos los boots registrados
```bash
sudo journalctl --list-boots
```

### Ver qué pasó antes del último reinicio
```bash
sudo journalctl -b -1 -n 100 --no-pager
```

### Verificar servicios que fallan constantemente
```bash
sudo systemctl --failed
sudo journalctl -u drone.service -n 50 --no-pager
```

### Detener/deshabilitar servicio problemático
```bash
sudo systemctl stop drone.service
sudo systemctl disable drone.service
```

### Verificar watchdog (puede causar reinicios automáticos)
```bash
systemctl status watchdog
```

### Monitorear en tiempo real (temperatura + voltaje + uptime)
```bash
watch -n 5 'echo "=== UPTIME ==="; uptime; echo ""; echo "=== TEMPERATURA ==="; vcgencmd measure_temp; echo ""; echo "=== VOLTAJE (0x0=OK) ==="; vcgencmd get_throttled; echo ""; echo "=== RAM ==="; free -h'
```

### Ver procesos que consumen más CPU/memoria
```bash
# Ordenar por memoria
ps aux --sort=-%mem | head -10

# Ordenar por CPU
ps aux --sort=-%cpu | head -10

# Top interactivo
htop
```

## actualizacion del repositorio
# Opción 1: Sin mensaje (usa timestamp automático)
./subir_cambios_a_repositorio.sh

# Opción 2: Con mensaje personalizado
./subir_cambios_a_repositorio.sh "Arreglo de bugs en control de motores"