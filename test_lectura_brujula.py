
import time
import traceback
from qmc5883l import QMC5883L

def log(msg):
    with open("brujula_error.log", "a") as f:
        f.write(msg + "\n")
    print(msg)

try:
    sensor = QMC5883L()
    log("Sensor QMC5883L inicializado correctamente.")
except Exception as e:
    log("Error al inicializar el sensor: " + str(e))
    log(traceback.format_exc())
    exit(1)

while True:
    try:
        azimuth = sensor.get_azimuth()
        log(f"Azimuth: {azimuth}")
        time.sleep(1)
    except Exception as e:
        log("Error en lectura: " + str(e))
        log(traceback.format_exc())
        time.sleep(2)
