#!/bin/bash

# ===================================================================
# SCRIPT DE CORRECCIONES PARA ESTABILIDAD DE WiFi
# Ejecutar en la Raspberry Pi
# ===================================================================

echo "======================================================================"
echo "  APLICANDO CORRECCIONES DE ESTABILIDAD WiFi"
echo "======================================================================"
echo ""

# 1. DESACTIVAR POWERSAVE WiFi (TEMPORAL)
echo "[1/3] Desactivando PowerSave WiFi (temporal)..."
sudo iw wlan0 set power_save off
if [ $? -eq 0 ]; then
    echo "✓ PowerSave desactivado"
else
    echo "✗ Error desactivando PowerSave (requiere sudo)"
fi
echo ""

# 2. CREAR CONFIGURACIÓN PERMANENTE DE POWERSAVE
echo "[2/3] Creando configuración permanente..."
sudo bash -c 'cat > /etc/modprobe.d/brcmfmac.conf << EOF
# Desactivar ahorro de energía en WiFi para evitar desconexiones
options brcmfmac power_save=0
EOF'

if [ -f /etc/modprobe.d/brcmfmac.conf ]; then
    echo "✓ Archivo /etc/modprobe.d/brcmfmac.conf creado"
    echo "  (Se aplicará en el próximo reinicio)"
else
    echo "✗ Error creando archivo de configuración"
fi
echo ""

# 3. VERIFICAR ESTADO ACTUAL
echo "[3/3] Verificando estado actual..."
echo ""
echo "Estado de PowerSave WiFi:"
iw wlan0 get power_save
echo ""
echo "Configuración en /etc/modprobe.d/brcmfmac.conf:"
cat /etc/modprobe.d/brcmfmac.conf 2>/dev/null || echo "No configurado aún"
echo ""

echo "======================================================================"
echo "✓ CORRECCIONES APLICADAS"
echo "======================================================================"
echo ""
echo "⚠️  PRÓXIMO PASO: Reinicia la Raspberry para aplicar cambios permanentes"
echo "    comando: sudo reboot"
echo ""
