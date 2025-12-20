# Optimización de RAM y Servidor del Drone Acuático

## 📊 Análisis de VS Code en Raspberry Pi

### Estado Actual
- **Espacio ocupado**: 580 MB
- **Proceso principal**: 582 MB de RAM (62.7% del total)
- **Procesos activos**: 7 procesos de Node.js
- **Extensiones pesadas**:
  - ms-python.vscode-pylance: 98 MB
  - github.copilot: 74 MB
  - github.copilot-chat: 64 MB
  - ms-python.python: 51 MB

### Recomendaciones VS Code
1. **Logs**: Se limpian automáticamente logs > 2 días
2. **Caché**: Se eliminan cachés de extensiones no usadas
3. **Compresión**: Logs > 5 MB se comprimen automáticamente

---

## 🚀 Scripts de Optimización

### 1. **optimizar_inicio.sh**
Script que se ejecuta automáticamente al iniciar el servidor.

**Acciones**:
- Limpia cachés del sistema
- Elimina archivos temporales
- Limpia logs de VS Code antiguos
- Elimina caché de Python (`__pycache__`)
- Comprime logs grandes (>10 MB)
- Optimiza swap si es necesario
- Ajusta swappiness a 10 para mejor rendimiento

**Resultado típico**: Libera 5-15% de RAM

### 2. **iniciar_servidor.sh** ⭐ RECOMENDADO
Script principal para iniciar el servidor del drone.

**Uso**:
```bash
cd ~/drone\ acuatico
./iniciar_servidor.sh
```

**Proceso**:
1. Optimiza RAM automáticamente
2. Activa entorno virtual Python
3. Verifica dependencias
4. Muestra estado del sistema (RAM, temperatura)
5. Inicia servidor en puerto 8080
6. Limpia memoria al finalizar

---

## ⚙️ Servicio Systemd (Opcional)

### Instalación
Para que el servidor se inicie automáticamente al arrancar la Raspberry:

```bash
cd ~/drone\ acuatico/optimizacion
./instalar_servicio.sh
```

### Comandos de Control
```bash
# Iniciar servidor
sudo systemctl start drone-server

# Detener servidor
sudo systemctl stop drone-server

# Reiniciar servidor
sudo systemctl restart drone-server

# Ver estado
sudo systemctl status drone-server

# Ver logs en tiempo real
sudo journalctl -u drone-server -f

# Deshabilitar inicio automático
sudo systemctl disable drone-server
```

---

## 📁 Organización de Archivos

```
drone acuatico/
├── iniciar_servidor.sh          ← USAR ESTE PARA INICIAR
├── optimizacion/
│   ├── optimizar_inicio.sh       ← Se ejecuta automáticamente
│   ├── limpiar_memoria_optimizado.sh
│   ├── monitor_ram.sh
│   ├── verificar_ram_web.sh
│   ├── optimizar_todo.sh
│   ├── optimizar_vscode.sh
│   ├── drone-server.service      ← Archivo de servicio systemd
│   ├── instalar_servicio.sh      ← Instalar servicio systemd
│   ├── inicio.log                ← Log de optimizaciones
│   ├── OPTIMIZACION_SISTEMA.md
│   └── CAMBIOS_OPTIMIZACION.md
├── servidores/
│   ├── drone_server.py
│   ├── server.py
│   └── control remoto digital/
├── gps_navegacion/
├── hardware/
├── conectividad/
├── documentacion/
└── utilidades/
```

---

## 💡 Uso Rápido

### Opción 1: Manual (Recomendado para pruebas)
```bash
cd ~/drone\ acuatico
./iniciar_servidor.sh
```

### Opción 2: Servicio Automático (Recomendado para producción)
```bash
# Instalar una sola vez
cd ~/drone\ acuatico/optimizacion
./instalar_servicio.sh

# El servidor se iniciará automáticamente al arrancar
# Para control manual usar:
sudo systemctl start/stop/restart drone-server
```

---

## 📈 Monitoreo de RAM

### Ver estado actual
```bash
free -h
```

### Monitor continuo (cada 30 segundos)
```bash
cd ~/drone\ acuatico/optimizacion
nohup ./monitor_ram.sh &
```

### Ver procesos que más RAM usan
```bash
ps aux --sort=-%mem | head -10
```

---

## 🔧 Optimizaciones Aplicadas

### Sistema
- ✅ Swappiness ajustado a 10
- ✅ Drop caches al inicio
- ✅ Limpieza de temporales automática

### Python
- ✅ Garbage collection optimizado (700, 10, 10)
- ✅ `__pycache__` limpiado automáticamente
- ✅ Variables PYTHONUNBUFFERED=1

### VS Code
- ✅ Logs antiguos eliminados (> 2 días)
- ✅ Logs grandes comprimidos (> 5 MB)
- ✅ Cachés de extensiones limpiados
- ✅ Tamaño de letra aumentado a 14

---

## 📝 Logs

- **Optimización**: `~/drone acuatico/optimizacion/inicio.log`
- **Servidor**: `~/drone acuatico/optimizacion/servidor.log`
- **Errores**: `~/drone acuatico/optimizacion/servidor_error.log`
- **Monitor RAM**: `~/drone acuatico/ram_monitor.log`

---

## ⚠️ Notas Importantes

1. **Primera ejecución**: El script pedirá permisos sudo para optimizar el sistema
2. **VS Code consume ~63% de RAM**: Es normal, pero se optimiza con limpieza periódica
3. **Temperatura**: El script muestra la temperatura al inicio
4. **Swap**: Se reinicia automáticamente si supera los 100 MB de uso

---

## 🎯 Próximos Pasos

1. Ejecutar `./iniciar_servidor.sh` para probar el sistema
2. Monitorear RAM durante 24h con `monitor_ram.sh`
3. Si todo funciona bien, instalar como servicio systemd
4. Configurar limpieza automática semanal con cron (opcional)
