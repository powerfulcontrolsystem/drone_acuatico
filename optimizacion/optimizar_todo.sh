#!/bin/bash
# Script maestro de optimización de RAM para Raspberry Pi
# Ejecuta todas las optimizaciones en el orden correcto

SCRIPT_DIR="$HOME/drone acuatico"

echo "================================================"
echo "  OPTIMIZACIÓN COMPLETA DE RAM - RASPBERRY PI"
echo "================================================"
echo ""
echo "Este script ejecutará todas las optimizaciones:"
echo "  1. Configuración de VSCode Server"
echo "  2. Desactivación de hardware innecesario (requiere sudo)"
echo "  3. Limpieza inmediata de memoria"
echo "  4. Inicio del monitor de RAM"
echo ""

# Verificar que estemos en el directorio correcto
if [ ! -f "$SCRIPT_DIR/drone_server.py" ]; then
    echo "ERROR: No se encuentra drone_server.py"
    echo "Ejecuta este script desde: $SCRIPT_DIR"
    exit 1
fi

# 1. Optimizar VSCode Server
echo "=== PASO 1: Optimizando VSCode Server ==="
bash "$SCRIPT_DIR/optimizar_vscode.sh"
echo ""

# 2. Desactivar hardware (requiere sudo)
echo "=== PASO 2: Desactivando hardware innecesario ==="
echo "NOTA: Este paso requiere permisos de root (sudo)"
read -p "¿Deseas desactivar WiFi, Bluetooth y Audio? (s/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    sudo bash "$SCRIPT_DIR/desactivar_hardware.sh"
else
    echo "   Hardware no modificado (puedes ejecutarlo después con sudo)"
fi
echo ""

# 3. Limpieza inmediata de memoria
echo "=== PASO 3: Limpiando memoria ==="
bash "$SCRIPT_DIR/limpiar_memoria.sh"
echo ""

# 4. Configurar inicio automático del monitor
echo "=== PASO 4: Configurando monitor de RAM ==="
# Agregar al crontab si no existe
CRON_CMD="@reboot $SCRIPT_DIR/monitor_ram.sh"
if ! crontab -l 2>/dev/null | grep -q "monitor_ram.sh"; then
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "   Monitor configurado para inicio automático"
else
    echo "   Monitor ya está en crontab"
fi

# Iniciar monitor ahora
if ! pgrep -f "monitor_ram.sh" > /dev/null; then
    nohup "$SCRIPT_DIR/monitor_ram.sh" > /dev/null 2>&1 &
    echo "   Monitor de RAM iniciado (PID: $!)"
else
    echo "   Monitor ya está corriendo"
fi
echo ""

# 5. Actualizar script de limpieza existente
echo "=== PASO 5: Actualizando script de limpieza ==="
bash "$SCRIPT_DIR/limpiar_memoria.sh"
echo ""

# Mostrar estado actual
echo "================================================"
echo "  ESTADO ACTUAL DEL SISTEMA"
echo "================================================"
free -h
echo ""
echo "Procesos más pesados:"
ps aux --sort=-%mem | head -6
echo ""

# Instrucciones finales
echo "================================================"
echo "  OPTIMIZACIÓN COMPLETADA"
echo "================================================"
echo ""
echo "SIGUIENTE PASO RECOMENDADO:"
echo "  1. Cierra todas las conexiones de VSCode"
echo "  2. Ejecuta: source ~/.bashrc"
echo "  3. Reinicia la Raspberry Pi: sudo reboot"
echo ""
echo "DESPUÉS DEL REINICIO:"
echo "  - Verifica la RAM: free -h"
echo "  - Monitor de RAM estará activo automáticamente"
echo "  - Inicia solo el servidor del drone:"
echo "    python3 ~/drone\\ acuatico/drone_server.py"
echo ""
echo "NOTAS IMPORTANTES:"
echo "  - server.py (rpyc) ha sido DESACTIVADO (consumía RAM innecesariamente)"
echo "  - WiFi/Bluetooth/Audio desactivados (si elegiste 's')"
echo "  - VSCode Server ahora tiene límite de 256MB"
echo "  - Monitoreo automático limpiará RAM cuando supere 90%"
echo ""
