#!/usr/bin/env python3
"""
DIAGNÓSTICO RÁPIDO - Verificar datos Victron en tiempo real
"""
import sys
sys.path.insert(0, '/home/admin/drone_acuatico')

from funciones import obtener_solar, detectar_puerto_victron, leer_victron
import json

print("=" * 70)
print("DIAGNÓSTICO RÁPIDO - VICTRON 75/15")
print("=" * 70)

# 1. Detectar puerto
print("\n[1/3] Detectando puerto serial...")
puerto = detectar_puerto_victron()
if puerto:
    print(f"✅ Puerto encontrado: {puerto}")
else:
    print("❌ Puerto NO encontrado")
    print("Verifica:")
    print("  - Cable USB conectado")
    print("  - Es cable VE.Direct oficial")
    sys.exit(1)

# 2. Leer datos directamente
print("\n[2/3] Leyendo datos del Victron...")
datos_raw = leer_victron(puerto=puerto, timeout=5)

if datos_raw:
    print("\n📊 DATOS RAW (sin procesar):")
    print(json.dumps(datos_raw, indent=2))
else:
    print("❌ No se recibieron datos")

# 3. Leer a través de obtener_solar()
print("\n[3/3] Llamando obtener_solar() (como hace el servidor)...")
datos_solar = obtener_solar()

print("\n📊 DATOS SOLAR (procesados):")
print(json.dumps(datos_solar, indent=2, default=str))

# Verificar
print("\n" + "=" * 70)
print("DIAGNÓSTICO")
print("=" * 70)

if datos_solar.get('conectado'):
    print("✅ CONECTADO")
    print(f"   Voltaje batería: {datos_solar.get('bateria_voltaje')}V")
    print(f"   Voltaje panel: {datos_solar.get('panel_voltaje')}V")
    print(f"   Potencia: {datos_solar.get('potencia')}W")
    print(f"   Estado: {datos_solar.get('estado')}")
else:
    print("❌ DESCONECTADO")
    print(f"   Error: {datos_solar.get('error')}")

print("=" * 70)
