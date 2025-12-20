#!/bin/bash
# Script para instalar el servicio systemd del servidor del drone

SERVICE_FILE="/home/admin/drone acuatico/optimizacion/drone-server.service"
SYSTEMD_PATH="/etc/systemd/system/drone-server.service"

echo "==================================================="
echo "   INSTALACIÓN DE SERVICIO SYSTEMD"
echo "==================================================="
echo ""

# Verificar que el archivo de servicio existe
if [ ! -f "$SERVICE_FILE" ]; then
    echo "✗ Error: No se encontró el archivo drone-server.service"
    exit 1
fi

# Copiar el archivo de servicio
echo "1. Copiando archivo de servicio..."
sudo cp "$SERVICE_FILE" "$SYSTEMD_PATH"
echo "   ✓ Archivo copiado a $SYSTEMD_PATH"

# Recargar systemd
echo "2. Recargando systemd..."
sudo systemctl daemon-reload
echo "   ✓ Systemd recargado"

# Habilitar el servicio (inicio automático)
echo "3. Habilitando servicio para inicio automático..."
sudo systemctl enable drone-server.service
echo "   ✓ Servicio habilitado"

echo ""
echo "==================================================="
echo "✓ INSTALACIÓN COMPLETADA"
echo "==================================================="
echo ""
echo "Comandos útiles:"
echo "  Iniciar:    sudo systemctl start drone-server"
echo "  Detener:    sudo systemctl stop drone-server"
echo "  Reiniciar:  sudo systemctl restart drone-server"
echo "  Estado:     sudo systemctl status drone-server"
echo "  Logs:       sudo journalctl -u drone-server -f"
echo "  Deshabilitar: sudo systemctl disable drone-server"
echo ""
