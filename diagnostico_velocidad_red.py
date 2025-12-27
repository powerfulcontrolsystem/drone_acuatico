#!/usr/bin/env python3
"""
Diagnóstico de Velocidad de Red
Prueba los métodos disponibles para medir velocidad
"""
import subprocess
import sys

print("═══════════════════════════════════════════════════════════════")
print("   DIAGNÓSTICO VELOCIDAD DE RED")
print("═══════════════════════════════════════════════════════════════\n")

# Verificar conexión a internet
print("[1/3] Verificando conexión a internet...")
try:
    subprocess.run(['ping', '-c', '1', '8.8.8.8'], capture_output=True, timeout=5)
    print("✓ Conexión activa\n")
except:
    print("✗ Sin conexión a internet\n")
    sys.exit(1)

# Método 1: speedtest-cli
print("[2/3] Probando speedtest-cli...")
try:
    resultado = subprocess.run(
        ['speedtest-cli', '--simple'],
        capture_output=True,
        text=True,
        timeout=60
    )
    if resultado.returncode == 0:
        lineas = resultado.stdout.strip().split('\n')
        if len(lineas) >= 2:
            download = float(lineas[1])
            print(f"✓ speedtest-cli: {download:.2f} Mbps")
        else:
            print("⚠ speedtest-cli: Formato de respuesta incorrecto")
    else:
        print("✗ speedtest-cli: No instalado o error")
except subprocess.TimeoutExpired:
    print("⚠ speedtest-cli: Timeout (>60s)")
except FileNotFoundError:
    print("✗ speedtest-cli: No encontrado (instala: pip install speedtest-cli)")
except Exception as e:
    print(f"✗ speedtest-cli: Error - {e}")

print()

# Método 2: curl
print("[3/3] Probando curl...")
try:
    resultado = subprocess.run(
        ['curl', '-o', '/dev/null', '-s', '-w', '%{speed_download}', 'http://speedtest.ftp.otenet.gr/files/test10Mb.db'],
        capture_output=True,
        text=True,
        timeout=30
    )
    if resultado.returncode == 0:
        velocidad_bytes = float(resultado.stdout.strip())
        velocidad_kbps = velocidad_bytes * 8 / 1000
        print(f"✓ curl: {velocidad_kbps:.2f} Kbps ({velocidad_kbps/1000:.2f} Mbps)")
    else:
        print("✗ curl: Error en descarga")
except subprocess.TimeoutExpired:
    print("⚠ curl: Timeout (>30s)")
except FileNotFoundError:
    print("✗ curl: No encontrado")
except Exception as e:
    print(f"✗ curl: Error - {e}")

print("\n" + "═" * 63)
print("RECOMENDACIÓN:")
print("  Si ambos métodos fallan, instala speedtest-cli:")
print("  pip install speedtest-cli")
print("═" * 63)
