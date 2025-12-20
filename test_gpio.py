import RPi.GPIO as GPIO
import time

# Configurar modo BCM
GPIO.setmode(GPIO.BCM)

# Lista de pines GPIO para los relés (según la descripción del proyecto)
relays = [4, 7, 8, 9, 11, 21, 22, 23, 24]

# Configurar pines como salida
for pin in relays:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)  # Asegurar que estén apagados inicialmente

# Secuencia: encender cada relé por 1 segundo en orden
print("Iniciando secuencia de activación de relés...")
for pin in relays:
    print(f"Activando relé en GPIO {pin}")
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(pin, GPIO.LOW)
    time.sleep(0.5)  # Pausa entre relés

print("Secuencia completada.")
GPIO.cleanup()