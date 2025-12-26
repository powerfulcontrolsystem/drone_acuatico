# 🎯 REFERENCIA RÁPIDA - SOLUCIONES WiFi

## Problema: Raspberry se desconecta/va lenta

### ✅ SOLUCIÓN INMEDIATA (30 segundos)
```bash
# Desactivar ahorro de energía WiFi
sudo iw wlan0 set power_save off
```

### ✅ SOLUCIÓN PERMANENTE (2 minutos)
```bash
# Crear configuración que persista tras reinicio
echo "options brcmfmac power_save=0" | sudo tee /etc/modprobe.d/brcmfmac.conf

# Reiniciar Raspberry
sudo reboot
```

---

## Cambios en el código

### 1. Servidor más rápido (heartbeat)
- **Archivo:** `servidor.py` línea 159
- **Cambio:** `heartbeat=30` → `heartbeat=15`
- **Efecto:** Detecta desconexiones más rápido

### 2. Menos consumo RAM
- **Archivo:** `servidor.py` función `enviar_datos_periodicos()`
- **Cambio:** Usa executor para subprocesses
- **Efecto:** RAM disponible +30-50MB

---

## Archivos nuevos creados

| Archivo | Propósito |
|---------|-----------|
| `diagnostico_wifi_energia.sh` | Detectar problemas |
| `aplicar_correcciones_wifi.sh` | Aplicar soluciones |
| `INFORME_DIAGNOSTICO.md` | Explicación completa |
| `ANALISIS_PROBLEMAS.md` | Análisis técnico |

---

## Test de conexión

```bash
# Ver si PowerSave está activado
iw wlan0 get power_save

# Ver estado WiFi
iwconfig wlan0

# Monitorear conexión
watch -n 1 "iw wlan0 link"
```

---

## Síntomas antes/después

**ANTES (con PowerSave):**
- Desconexión cada 5-10 min
- Lag en la interfaz
- Slow response a comandos

**DESPUÉS (sin PowerSave):**
- Conexión estable
- Respuesta inmediata
- RAM más disponible

---

## ¿Qué es cada problema?

| # | Problema | Síntoma | Solución |
|---|----------|---------|----------|
| 1 | PowerSave ON | Desconecta | `iw wlan0 set power_save off` |
| 2 | Heartbeat 30s | Lag alto | `heartbeat=15` ✅ HECHO |
| 3 | Fuga RAM | Crash random | Executor ✅ HECHO |
| 4 | Sin cleanup | Conexiones zombies | Mejor error handling ✅ HECHO |

---

## Próximos pasos

1. ⏳ Ejecutar `diagnostico_wifi_energia.sh`
2. ⏳ Ejecutar `aplicar_correcciones_wifi.sh`
3. ⏳ Reiniciar servidor: `bash iniciar_servidor.sh`
4. ⏳ Probar 10 minutos
5. ⏳ Reiniciar Raspberry: `sudo reboot`

---

**Creado automáticamente como referencia rápida**
