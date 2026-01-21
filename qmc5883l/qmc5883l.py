# Módulo QMC5883L para Raspberry Pi
# Implementación mínima para restaurar la carpeta

class QMC5883L:
    def __init__(self, bus=1, address=0x2C):
        self.bus = bus
        self.address = address
    def get_azimuth(self):
        # Simulación de lectura
        return 0.0
