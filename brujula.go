package main

// ==================== BRÚJULA QMC5883L (I2C) ====================
// Driver puro Go para sensor magnético QMC5883L
// Accede a /dev/i2c-1 directamente via syscall

import (
	"log"
	"math"
	"os"
	"sync"
	"syscall"
	"time"
	"unsafe"
)

const (
	i2cSlave     = 0x0703 // ioctl I2C_SLAVE
	qmc5883lAddr = 0x2C   // Dirección I2C del QMC5883L
)

// Brujula representa el sensor QMC5883L
type Brujula struct {
	mu          sync.Mutex
	archivo     *os.File
	disponible  bool
}

var brujula *Brujula

func inicializarBrujula() {
	brujula = &Brujula{}
	
	archivo, err := os.OpenFile("/dev/i2c-1", os.O_RDWR, 0)
	if err != nil {
		log.Printf("Brújula no disponible (no se pudo abrir /dev/i2c-1): %v", err)
		return
	}

	// Establecer dirección del esclavo I2C
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, archivo.Fd(), i2cSlave, uintptr(qmc5883lAddr))
	if errno != 0 {
		log.Printf("Error configurando dirección I2C: %v", errno)
		archivo.Close()
		return
	}

	brujula.archivo = archivo

	// Configurar el sensor
	// Control 2: SOFT RESET
	if err := i2cWriteByte(archivo, 0x0B, 0x01); err != nil {
		log.Printf("Error resetendo brújula: %v", err)
		archivo.Close()
		return
	}
	time.Sleep(10 * time.Millisecond)

	// Control 1: 200Hz, 8G, OSR=512, modo continuo
	if err := i2cWriteByte(archivo, 0x09, 0x1D); err != nil {
		log.Printf("Error configurando brújula: %v", err)
		archivo.Close()
		return
	}
	time.Sleep(10 * time.Millisecond)

	brujula.disponible = true
	log.Println("Brújula QMC5883L inicializada correctamente")
}

func i2cWriteByte(f *os.File, registro, valor byte) error {
	_, err := f.Write([]byte{registro, valor})
	return err
}

func i2cReadBlock(f *os.File, registro byte, longitud int) ([]byte, error) {
	// Enviar dirección del registro
	_, err := f.Write([]byte{registro})
	if err != nil {
		return nil, err
	}
	// Leer datos
	buf := make([]byte, longitud)
	_, err = f.Read(buf)
	return buf, err
}

// twosComplement convierte un valor unsigned a signed (complemento a 2)
func twosComplement(val uint16, bits int) int16 {
	if val&(1<<(bits-1)) != 0 {
		return int16(val) - int16(1<<bits)
	}
	return int16(val)
}

// obtenerDatosBrujula lee el azimuth de la brújula QMC5883L
func obtenerDatosBrujula() map[string]interface{} {
	if brujula == nil || !brujula.disponible {
		return map[string]interface{}{
			"valido":  false,
			"azimuth": nil,
		}
	}

	brujula.mu.Lock()
	defer brujula.mu.Unlock()

	// Leer 6 bytes de datos crudos desde registro 0x00
	datos, err := i2cReadBlock(brujula.archivo, 0x00, 6)
	if err != nil {
		log.Printf("Error leyendo brújula: %v", err)
		return map[string]interface{}{
			"valido":  false,
			"azimuth": nil,
		}
	}

	// Convertir datos crudos (little-endian)
	xRaw := uint16(datos[1])<<8 | uint16(datos[0])
	yRaw := uint16(datos[3])<<8 | uint16(datos[2])

	x := float64(twosComplement(xRaw, 16))
	y := float64(twosComplement(yRaw, 16))

	// Calcular azimuth
	azimuth := math.Atan2(y, x) * 180 / math.Pi
	if azimuth < 0 {
		azimuth += 360
	}

	// Redondear a 1 decimal
	azimuth = math.Round(azimuth*10) / 10

	return map[string]interface{}{
		"valido":  true,
		"azimuth": azimuth,
	}
}

func cerrarBrujula() {
	if brujula != nil && brujula.archivo != nil {
		brujula.archivo.Close()
		log.Println("Brújula cerrada")
	}
}

// Forzar uso de unsafe para que compile (necesario para syscall.Syscall con punteros)
var _ = unsafe.Sizeof(0)
