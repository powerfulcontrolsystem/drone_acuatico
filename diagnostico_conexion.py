#!/usr/bin/env python3
"""
DIAGNÓSTICO DE CONEXIÓN VICTRON
Script para probar la estabilidad de la conexión y velocidad de lectura
"""

import time
import sys
from funciones import detectar_puerto_victron, leer_victron

def test_conexion_continua(duracion_segundos=60):
    """
    Prueba la conexión Victron continuamente durante X segundos.
    Mide:
    - Tasa de éxito
    - Tiempo promedio de lectura
    - Errores
    """
    print("=" * 70)
    print("DIAGNÓSTICO DE CONEXIÓN VICTRON 75/15")
    print("=" * 70)
    
    # Detectar puerto
    print("\n[1/3] Detectando puerto serial...")
    puerto = detectar_puerto_victron()
    if not puerto:
        print("❌ ERROR: No se detectó el controlador Victron")
        print("Verifica:")
        print("  - Cable USB conectado")
        print("  - Es cable VE.Direct (no USB normal)")
        print("  - Ejecutar: ls /dev/ttyUSB* /dev/ttyACM*")
        return False
    
    print(f"✅ Puerto detectado: {puerto}")
    
    # Probar conexión continua
    print(f"\n[2/3] Probando conexión continua por {duracion_segundos}s...")
    print("Presiona Ctrl+C para detener\n")
    
    intentos = 0
    exitos = 0
    fallos = 0
    tiempos = []
    errores = {}
    
    inicio_test = time.time()
    
    try:
        while (time.time() - inicio_test) < duracion_segundos:
            intentos += 1
            inicio = time.time()
            
            # Leer datos
            datos = leer_victron(puerto=puerto, timeout=5)
            
            duracion = time.time() - inicio
            tiempos.append(duracion)
            
            if datos and datos.get('exito'):
                exitos += 1
                # Mostrar datos clave
                v_bat = datos.get('bateria_voltaje', 0)
                v_panel = datos.get('panel_voltaje', 0)
                potencia = datos.get('potencia', 0)
                estado = datos.get('estado', 'desconocido')
                
                print(f"✅ Lectura #{intentos}: {duracion:.2f}s | "
                      f"Bat: {v_bat}V | Panel: {v_panel}V | "
                      f"Potencia: {potencia}W | Estado: {estado}")
            else:
                fallos += 1
                error = datos.get('error', 'desconocido') if datos else 'sin respuesta'
                errores[error] = errores.get(error, 0) + 1
                print(f"❌ Lectura #{intentos}: FALLO ({error}) - {duracion:.2f}s")
            
            # Esperar un poco antes de siguiente lectura
            time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n⚠️  Test interrumpido por usuario")
    
    # Estadísticas finales
    print("\n" + "=" * 70)
    print("[3/3] RESULTADOS")
    print("=" * 70)
    
    if intentos == 0:
        print("❌ No se realizaron lecturas")
        return False
    
    tasa_exito = (exitos / intentos) * 100
    tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
    tiempo_min = min(tiempos) if tiempos else 0
    tiempo_max = max(tiempos) if tiempos else 0
    
    print(f"\nIntentos totales: {intentos}")
    print(f"Lecturas exitosas: {exitos} ({tasa_exito:.1f}%)")
    print(f"Lecturas fallidas: {fallos}")
    print(f"\nTiempos de lectura:")
    print(f"  - Promedio: {tiempo_promedio:.2f}s")
    print(f"  - Mínimo: {tiempo_min:.2f}s")
    print(f"  - Máximo: {tiempo_max:.2f}s")
    
    if errores:
        print(f"\nErrores encontrados:")
        for error, count in errores.items():
            print(f"  - {error}: {count} veces")
    
    print("\n" + "=" * 70)
    print("DIAGNÓSTICO")
    print("=" * 70)
    
    if tasa_exito >= 95:
        print("✅ EXCELENTE: Conexión muy estable")
    elif tasa_exito >= 80:
        print("⚠️  ACEPTABLE: Conexión estable pero con fallos ocasionales")
    elif tasa_exito >= 50:
        print("⚠️  PROBLEMAS: Conexión inestable")
        print("   Recomendaciones:")
        print("   - Revisar cable USB")
        print("   - Verificar alimentación del Victron")
        print("   - Revisar logs: journalctl -u servidor.service")
    else:
        print("❌ CRÍTICO: Conexión muy inestable")
        print("   Posibles causas:")
        print("   - Cable defectuoso o no compatible")
        print("   - Victron sin alimentación")
        print("   - Interferencias en puerto USB")
    
    if tiempo_promedio > 3:
        print(f"\n⚠️  ADVERTENCIA: Tiempo de lectura alto ({tiempo_promedio:.2f}s)")
        print("   Esto puede causar delays en el servidor")
        print("   Recomendación: Verificar carga del sistema")
    
    print("=" * 70)
    
    return tasa_exito >= 80


if __name__ == '__main__':
    duracion = 60  # Por defecto 60 segundos
    
    if len(sys.argv) > 1:
        try:
            duracion = int(sys.argv[1])
        except ValueError:
            print("Uso: python3 diagnostico_conexion.py [segundos]")
            sys.exit(1)
    
    exito = test_conexion_continua(duracion)
    sys.exit(0 if exito else 1)
