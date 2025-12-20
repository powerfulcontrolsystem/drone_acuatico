#!/bin/bash
# Script de monitoreo y optimización continua de RAM
# Ejecutar en segundo plano: nohup ./monitor_ram.sh &

LOG_FILE="$HOME/drone acuatico/ram_monitor.log"
RAM_LIMIT=90  # % de uso de RAM antes de limpiar
CHECK_INTERVAL=30  # Segundos entre verificaciones

echo "=== Monitor de RAM iniciado ===" >> "$LOG_FILE"
date >> "$LOG_FILE"

while true; do
    # Obtener uso de RAM en %
    RAM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    
    # Log del estado actual (cada 5 minutos)
    if [ $(($(date +%s) % 300)) -lt $CHECK_INTERVAL ]; then
        echo "[$(date '+%H:%M:%S')] RAM: ${RAM_USAGE}%" >> "$LOG_FILE"
    fi
    
    # Si la RAM supera el límite, limpiar
    if [ $RAM_USAGE -gt $RAM_LIMIT ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ALERTA: RAM al ${RAM_USAGE}%" >> "$LOG_FILE"
        
        # Liberar caches del sistema
        sync
        echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || sudo sysctl -w vm.drop_caches=3
        
        # Forzar garbage collection en Python si el servidor está corriendo
        if pgrep -f "drone_server.py" > /dev/null; then
            # El servidor ya tiene gc.collect() interno
            echo "   Servidor drone activo" >> "$LOG_FILE"
        fi
        
        # Eliminar archivos temporales
        rm -rf /tmp/*.tmp 2>/dev/null
        rm -rf /tmp/python-* 2>/dev/null
        
        # Comprimir logs antiguos
        find "$HOME/drone acuatico" -name "*.log" -size +10M -exec gzip {} \; 2>/dev/null
        
        NEW_RAM=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
        echo "   RAM después de limpieza: ${NEW_RAM}%" >> "$LOG_FILE"
    fi
    
    sleep $CHECK_INTERVAL
done
