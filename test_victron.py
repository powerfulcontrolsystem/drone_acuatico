#!/usr/bin/env python3
"""
Script de prueba para Victron 75/15
Detecta el puerto y lee datos del controlador solar
"""

import sys
import os

# Agregar el directorio del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from funciones import detectar_puerto_victron, leer_victron
import time

def test_victron():
    """Prueba la conexión y lectura del Victron 75/15."""
    print("=" * 70)
    print("  TEST VICTRON 75/15 - CONTROLADOR SOLAR")
    print("=" * 70)
    print()
    
    # Paso 1: Listar puertos disponibles
    print("[1] Buscando puertos seriales USB...")
    import glob
    puertos_usb = glob.glob('/dev/ttyUSB*')
    puertos_acm = glob.glob('/dev/ttyACM*')
    puertos_by_id = glob.glob('/dev/serial/by-id/*')
    
    print(f"    Puertos ttyUSB: {puertos_usb if puertos_usb else '(ninguno)'}")
    print(f"    Puertos ttyACM: {puertos_acm if puertos_acm else '(ninguno)'}")
    print(f"    Puertos by-id:  {puertos_by_id if puertos_by_id else '(ninguno)'}")
    print()
    
    # Paso 2: Detectar Victron
    print("[2] Detectando Victron 75/15...")
    puerto = detectar_puerto_victron()
    
    if puerto:
        print(f"    ✓ Victron encontrado en: {puerto}")
    else:
        print("    ✗ Victron NO detectado")
        print()
        print("Verifica:")
        print("  1. Cable USB conectado a la Raspberry Pi")
        print("  2. Controlador Victron encendido")
        print("  3. Cable VE.Direct correcto (no es un cable USB normal)")
        return False
    
    print()
    
    # Paso 3: Leer datos
    print("[3] Leyendo datos del Victron...")
    datos = leer_victron(puerto)
    
    if not datos or not datos.get('exito'):
        print(f"    ✗ Error leyendo datos: {datos.get('error', 'Desconocido')}")
        return False
    
    print("    ✓ Datos recibidos correctamente")
    print()
    
    # Paso 4: Mostrar datos
    print("=" * 70)
    print("  DATOS DEL CONTROLADOR SOLAR")
    print("=" * 70)
    print()
    
    print(f"  Panel Solar:")
    print(f"    Voltaje:    {datos['panel_voltaje']:.2f} V")
    print(f"    Corriente:  {datos['panel_corriente']:.2f} A")
    print(f"    Potencia:   {datos['potencia']} W")
    print()
    
    print(f"  Batería:")
    print(f"    Voltaje:    {datos['bateria_voltaje']:.2f} V")
    print(f"    Corriente:  {datos['bateria_corriente']:.2f} A")
    print()
    
    print(f"  Estado:")
    print(f"    Modo:       {datos['estado']}")
    print(f"    Cargando:   {'Sí' if datos.get('cargando') else 'No'}")
    print()
    
    if 'yield_today' in datos:
        print(f"  Producción:")
        print(f"    Hoy:        {datos['yield_today']} Wh")
        print(f"    Total:      {datos.get('yield_total', 0):.1f} kWh")
        print(f"    Pico hoy:   {datos.get('max_power_today', 0)} W")
        print()
    
    # Interpretación del estado
    print("=" * 70)
    print("  INTERPRETACIÓN")
    print("=" * 70)
    print()
    
    estado = datos['estado']
    if estado == 'bulk':
        print("  📈 BULK: Carga rápida (voltaje subiendo)")
    elif estado == 'absorption':
        print("  🔋 ABSORPTION: Carga final (voltaje constante)")
    elif estado == 'float':
        print("  ✅ FLOAT: Batería llena (mantenimiento)")
    elif estado == 'apagado':
        print("  ⚫ APAGADO: Sin luz solar suficiente")
    elif estado == 'falla':
        print("  ❌ FALLA: Error en el controlador")
    else:
        print(f"  ❓ Estado: {estado}")
    
    print()
    
    # Verificar producción
    if datos['potencia'] > 0:
        print(f"  ☀️ Generando {datos['potencia']}W desde el panel solar")
    else:
        print("  🌙 Sin producción solar (noche o panel sombreado)")
    
    print()
    print("=" * 70)
    print("  TEST COMPLETADO CON ÉXITO")
    print("=" * 70)
    
    return True


def monitoreo_continuo(intervalo=3):
    """Monitoreo continuo del Victron."""
    print("\nMONITOREO CONTINUO (Ctrl+C para detener)")
    print("=" * 70)
    
    puerto = detectar_puerto_victron()
    if not puerto:
        print("Victron no detectado")
        return
    
    try:
        while True:
            datos = leer_victron(puerto)
            if datos and datos.get('exito'):
                print(f"\r{time.strftime('%H:%M:%S')} | "
                      f"Panel: {datos['panel_voltaje']:5.1f}V {datos['panel_corriente']:5.2f}A {datos['potencia']:3d}W | "
                      f"Bat: {datos['bateria_voltaje']:5.1f}V {datos['bateria_corriente']:6.2f}A | "
                      f"Estado: {datos['estado']:12s}", end='', flush=True)
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test del Victron 75/15')
    parser.add_argument('--monitor', action='store_true', help='Monitoreo continuo')
    parser.add_argument('--intervalo', type=int, default=3, help='Intervalo de monitoreo (segundos)')
    
    args = parser.parse_args()
    
    if args.monitor:
        monitoreo_continuo(args.intervalo)
    else:
        exito = test_victron()
        sys.exit(0 if exito else 1)
