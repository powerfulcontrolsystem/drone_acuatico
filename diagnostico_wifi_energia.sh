#!/bin/bash

# ===================================================================
# SCRIPT DE DIAGNÓSTICO PARA CONEXIÓN WiFi Y AHORRO DE ENERGÍA
# Detecta problemas de inestabilidad y configuración de energía
# ===================================================================

echo "======================================================================"
echo "  DIAGNÓSTICO DE WiFi Y AHORRO DE ENERGÍA - RASPBERRY PI"
echo "======================================================================"
echo ""

# 1. INFORMACIÓN DEL SISTEMA
echo "═══════════════════════════════════════════════════════════════════════"
echo "[1] INFORMACIÓN GENERAL DEL SISTEMA"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "📋 Modelo y versión:"
cat /proc/device-tree/model 2>/dev/null || echo "No disponible"
echo "Versión kernel: $(uname -r)"
echo "Uptime: $(uptime -p)"
echo ""

# 2. ESTADO DE RAM
echo "═══════════════════════════════════════════════════════════════════════"
echo "[2] USO DE MEMORIA RAM"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

free -h
echo ""

# Procesos que más RAM consumen
echo "🔴 Top 10 procesos por uso de RAM:"
ps aux --sort=-%mem | head -11
echo ""

# 3. TEMPERATURA Y THROTTLING
echo "═══════════════════════════════════════════════════════════════════════"
echo "[3] TEMPERATURA Y THROTTLING"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "🌡️ Temperatura actual:"
if command -v vcgencmd &> /dev/null; then
    vcgencmd measure_temp
else
    cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null && echo " °C"
fi
echo ""

echo "⚡ Estado de throttling:"
if command -v vcgencmd &> /dev/null; then
    echo "Throttle status: $(vcgencmd get_throttled)"
else
    echo "vcgencmd no disponible"
fi
echo ""

# 4. ESTADO DE WiFi
echo "═══════════════════════════════════════════════════════════════════════"
echo "[4] ESTADO DE LA CONEXIÓN WiFi"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "📡 Interfaces de red:"
ip link show
echo ""

echo "📊 Estado de WiFi (wlan0):"
iwconfig wlan0 2>/dev/null || echo "wlan0 no encontrado"
echo ""

echo "🔗 Conexión actual:"
nmcli dev wifi list | head -5
echo ""

echo "📈 Estadísticas de WiFi:"
iw wlan0 link 2>/dev/null || echo "No se puede obtener info"
echo ""

# 5. CONFIGURACIÓN DE AHORRO DE ENERGÍA
echo "═══════════════════════════════════════════════════════════════════════"
echo "[5] CONFIGURACIÓN DE AHORRO DE ENERGÍA"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "⏱️ Powersave WiFi (wlan0):"
iw wlan0 get power_save 2>/dev/null || echo "No disponible"
echo ""

echo "🔌 Configuración del módulo WiFi:"
modinfo brcmfmac 2>/dev/null | grep -i "power\|sleep" || echo "No disponible"
echo ""

echo "🖥️ Estados de CPU:"
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || echo "No disponible"
echo ""

echo "📋 Frecuencia actual de CPU:"
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq 2>/dev/null | head -4
echo ""

# 6. CONFIGURACIÓN DE CONEXIÓN
echo "═══════════════════════════════════════════════════════════════════════"
echo "[6] CONFIGURACIÓN DE RED"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "🌐 IP actual:"
hostname -I
echo ""

echo "📡 Gateway y DNS:"
route -n | grep "^0.0.0.0\|^default"
echo ""

echo "🔗 Conexiones activas:"
netstat -tuln 2>/dev/null | grep LISTEN || ss -tuln | grep LISTEN
echo ""

# 7. PROCESOS RELACIONADOS CON SERVIDOR
echo "═══════════════════════════════════════════════════════════════════════"
echo "[7] PROCESOS DEL SERVIDOR"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "🐍 Procesos Python (servidor.py):"
ps aux | grep -E "servidor|python" | grep -v grep
echo ""

# 8. LOGS DEL SISTEMA
echo "═══════════════════════════════════════════════════════════════════════"
echo "[8] ERRORES RECIENTES (dmesg)"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

echo "⚠️ Últimos errores de WiFi/network:"
dmesg | grep -i "wifi\|wlan\|mmc\|connection\|timeout" | tail -20
echo ""

# 9. RECOMENDACIONES
echo "═══════════════════════════════════════════════════════════════════════"
echo "[9] RECOMENDACIONES BASADAS EN EL DIAGNÓSTICO"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Verificar RAM
RAM_DISPONIBLE=$(free | awk '/^Mem:/ {print $7}')
RAM_THRESHOLD=102400  # 100MB

if [ "$RAM_DISPONIBLE" -lt "$RAM_THRESHOLD" ]; then
    echo "⚠️  PROBLEMA CRÍTICO: RAM disponible < 100MB"
    echo "    → Hay fugas de memoria o procesos no terminados"
    echo "    → Solución: Revisar procesos Python que no liberan memoria"
else
    echo "✅ RAM: Disponible suficiente ($(($RAM_DISPONIBLE / 1024))MB)"
fi
echo ""

# Verificar WiFi PowerSave
POWERSAVE=$(iw wlan0 get power_save 2>/dev/null | grep "on")
if [ ! -z "$POWERSAVE" ]; then
    echo "⚠️  WiFi PowerSave ACTIVADO - Puede causar desconexiones"
    echo "    → Solución: Desactivar con: sudo iw wlan0 set power_save off"
else
    echo "✅ WiFi PowerSave: DESACTIVADO (correcto)"
fi
echo ""

# Verificar Throttling
THROTTLE=$(vcgencmd get_throttled 2>/dev/null | grep -v "0x0$")
if [ ! -z "$THROTTLE" ]; then
    echo "⚠️  THROTTLING DETECTADO - CPU ralentizada por temperatura/voltaje"
    echo "    → Solución: Mejorar ventilación o revisar fuente de poder"
else
    echo "✅ Throttling: No activo"
fi
echo ""

# Verificar temperatura
if command -v vcgencmd &> /dev/null; then
    TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
    if (( $(echo "$TEMP > 80" | bc -l) )); then
        echo "⚠️  TEMPERATURA ALTA (>80°C) - Puede causar inestabilidad"
        echo "    → Solución: Mejorar refrigeración"
    else
        echo "✅ Temperatura: Normal (${TEMP}°C)"
    fi
fi
echo ""

echo "======================================================================"
echo "FIN DEL DIAGNÓSTICO"
echo "======================================================================"
