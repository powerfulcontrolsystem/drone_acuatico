
# Módulo QMC5883L para Raspberry Pi - Lectura real
import math
import time
from smbus2 import SMBus

class QMC5883L:
    def __init__(self, bus=1, address=0x2C):
        self.bus = SMBus(bus)
        self.address = address
        # Configuración del sensor
        self.bus.write_byte_data(self.address, 0x0B, 0x01)  # Control 2: SOFT RESET
        time.sleep(0.01)
        self.bus.write_byte_data(self.address, 0x09, 0x1D)  # Control 1: 200Hz, 8G, OSR=512, modo continuo
        time.sleep(0.01)

    def read_raw(self):
        data = self.bus.read_i2c_block_data(self.address, 0x00, 6)
        x = self._twos_complement(data[1] << 8 | data[0], 16)
        y = self._twos_complement(data[3] << 8 | data[2], 16)
        z = self._twos_complement(data[5] << 8 | data[4], 16)
        return x, y, z

    def get_azimuth(self):
        x, y, z = self.read_raw()
        azimuth = math.atan2(y, x) * 180 / math.pi
        if azimuth < 0:
            azimuth += 360
        return round(azimuth, 1)

    def _twos_complement(self, val, bits):
        if val & (1 << (bits - 1)):
            val -= 1 << bits
        return val
