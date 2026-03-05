package main

// ==================== GPS SERIAL (NMEA) ====================
// Lectura del módulo GPS por puerto serial
// Parseo de sentencias NMEA GGA y RMC en Go puro

import (
	"bufio"
	"log"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// DatosGPS almacena la posición GPS actual
type DatosGPS struct {
	mu        sync.RWMutex
	Latitud   float64
	Longitud  float64
	Altitud   float64
	Velocidad float64
	Rumbo     float64
	Satelites int
	Precision float64
	Timestamp string
	Valido    bool
}

var (
	datosGPS   = &DatosGPS{}
	gpsRunning bool
	gpsMu      sync.Mutex
	gpsStop    chan struct{}
)

// detectarPuertoGPS busca automáticamente el puerto del módulo GPS
func detectarPuertoGPS() string {
	patrones := []string{"/dev/ttyACM*", "/dev/ttyUSB*"}
	for _, patron := range patrones {
		matches, _ := filepath.Glob(patron)
		if len(matches) > 0 {
			return matches[0]
		}
	}
	return "/dev/ttyACM0"
}

// configurarPuertoSerial configura el puerto serial usando stty
func configurarPuertoSerial(puerto string, baudrate int) error {
	cmd := exec.Command("stty", "-F", puerto,
		strconv.Itoa(baudrate),
		"raw", "-echo", "-echoe", "-echok",
		"cs8", "-parenb", "-cstopb",
		"min", "0", "time", "10")
	return cmd.Run()
}

// iniciarGPS inicia la lectura GPS en segundo plano
func iniciarGPS() bool {
	gpsMu.Lock()
	defer gpsMu.Unlock()

	if gpsRunning {
		return true
	}

	gpsStop = make(chan struct{})
	gpsRunning = true
	go leerGPSSerial()
	log.Println("Hilo GPS iniciado")
	return true
}

// detenerGPS detiene la lectura GPS
func detenerGPS() {
	gpsMu.Lock()
	defer gpsMu.Unlock()

	if gpsRunning {
		gpsRunning = false
		close(gpsStop)
		log.Println("GPS detenido")
	}
}

// leerGPSSerial lee datos GPS continuamente del puerto serial
func leerGPSSerial() {
	puerto := detectarPuertoGPS()
	log.Printf("Iniciando lectura GPS en %s @ 9600", puerto)

	for gpsRunning {
		// Configurar puerto serial
		if err := configurarPuertoSerial(puerto, 9600); err != nil {
			log.Printf("Error configurando puerto GPS: %v", err)
			select {
			case <-gpsStop:
				return
			case <-time.After(5 * time.Second):
			}
			continue
		}

		// Abrir puerto
		archivo, err := os.Open(puerto)
		if err != nil {
			log.Printf("Error abriendo puerto GPS %s: %v", puerto, err)
			select {
			case <-gpsStop:
				return
			case <-time.After(5 * time.Second):
			}
			continue
		}

		log.Printf("GPS conectado en %s", puerto)
		scanner := bufio.NewScanner(archivo)

		for scanner.Scan() {
			select {
			case <-gpsStop:
				archivo.Close()
				return
			default:
			}

			linea := strings.TrimSpace(scanner.Text())
			if len(linea) == 0 {
				continue
			}

			// Sentencia GGA: posición, altitud, satélites
			if strings.HasPrefix(linea, "$GPGGA") || strings.HasPrefix(linea, "$GNGGA") {
				parsearGGA(linea)
			}
			// Sentencia RMC: velocidad, rumbo
			if strings.HasPrefix(linea, "$GPRMC") || strings.HasPrefix(linea, "$GNRMC") {
				parsearRMC(linea)
			}
		}

		archivo.Close()

		if gpsRunning {
			log.Println("Conexión GPS perdida, reintentando en 5 segundos...")
			select {
			case <-gpsStop:
				return
			case <-time.After(5 * time.Second):
			}
		}
	}
}

// parsearGGA parsea una sentencia NMEA GGA
func parsearGGA(linea string) {
	campos := strings.Split(linea, ",")
	if len(campos) < 10 {
		return
	}

	// Verificar calidad GPS (campo 6)
	calidad, _ := strconv.Atoi(campos[6])
	if calidad == 0 {
		return
	}

	// Latitud (campo 2-3)
	lat := parsearCoordenada(campos[2], campos[3])
	// Longitud (campo 4-5)
	lon := parsearCoordenada(campos[4], campos[5])

	if lat == 0 && lon == 0 {
		return
	}

	// Altitud (campo 9)
	altitud, _ := strconv.ParseFloat(campos[9], 64)
	// Satélites (campo 7)
	satelites, _ := strconv.Atoi(campos[7])
	// HDOP / Precisión (campo 8)
	precision, _ := strconv.ParseFloat(campos[8], 64)
	// Timestamp (campo 1)
	timestamp := campos[1]

	datosGPS.mu.Lock()
	datosGPS.Latitud = lat
	datosGPS.Longitud = lon
	datosGPS.Altitud = altitud
	datosGPS.Satelites = satelites
	datosGPS.Precision = precision
	datosGPS.Timestamp = timestamp
	datosGPS.Valido = true
	datosGPS.mu.Unlock()
}

// parsearRMC parsea una sentencia NMEA RMC
func parsearRMC(linea string) {
	campos := strings.Split(linea, ",")
	if len(campos) < 8 {
		return
	}

	// Estado (campo 2): A=activo, V=vacío
	if campos[2] != "A" {
		return
	}

	// Velocidad en nudos (campo 7) → km/h
	if campos[7] != "" {
		nudos, err := strconv.ParseFloat(campos[7], 64)
		if err == nil {
			datosGPS.mu.Lock()
			datosGPS.Velocidad = nudos * 1.852 // nudos a km/h
			datosGPS.mu.Unlock()
		}
	}

	// Rumbo (campo 8)
	if len(campos) > 8 && campos[8] != "" {
		rumbo, err := strconv.ParseFloat(campos[8], 64)
		if err == nil {
			datosGPS.mu.Lock()
			datosGPS.Rumbo = rumbo
			datosGPS.mu.Unlock()
		}
	}
}

// parsearCoordenada convierte coordenada NMEA (DDMM.MMMM) a grados decimales
func parsearCoordenada(valor, direccion string) float64 {
	if valor == "" {
		return 0
	}

	v, err := strconv.ParseFloat(valor, 64)
	if err != nil {
		return 0
	}

	// Separar grados y minutos
	grados := math.Floor(v / 100)
	minutos := v - (grados * 100)
	decimal := grados + minutos/60.0

	// Aplicar dirección
	if direccion == "S" || direccion == "W" {
		decimal = -decimal
	}

	return decimal
}

// obtenerPosicionGPS devuelve la posición GPS actual
func obtenerPosicionGPS() map[string]interface{} {
	datosGPS.mu.RLock()
	defer datosGPS.mu.RUnlock()

	if !datosGPS.Valido {
		return nil
	}

	return map[string]interface{}{
		"latitud":   datosGPS.Latitud,
		"longitud":  datosGPS.Longitud,
		"altitud":   datosGPS.Altitud,
		"velocidad": datosGPS.Velocidad,
		"rumbo":     datosGPS.Rumbo,
		"satelites": datosGPS.Satelites,
		"precision": datosGPS.Precision,
		"timestamp": datosGPS.Timestamp,
		"valido":    true,
	}
}

// obtenerPayloadGPS devuelve datos GPS o marcador de ausencia
func obtenerPayloadGPS() map[string]interface{} {
	gps := obtenerPosicionGPS()
	if gps != nil {
		return gps
	}
	return map[string]interface{}{"valido": false}
}

// guardarPosicionGPSActual guarda la posición GPS actual en la base de datos
func guardarPosicionGPSActual(recorridoID *int) (bool, string) {
	datosGPS.mu.RLock()
	valido := datosGPS.Valido
	lat := datosGPS.Latitud
	lon := datosGPS.Longitud
	alt := datosGPS.Altitud
	vel := datosGPS.Velocidad
	sat := datosGPS.Satelites
	datosGPS.mu.RUnlock()

	if !valido {
		return false, "Sin señal GPS válida"
	}

	var recID int
	if recorridoID != nil {
		recID = *recorridoID
	} else {
		recID = iniciarRecorrido("Recorrido manual")
		if recID == 0 {
			return false, "No se pudo crear recorrido manual"
		}
	}

	posID := guardarPosicionGPSEnBD(recID, lat, lon, alt, vel, sat)
	if posID == 0 {
		return false, "No se pudo guardar la posición"
	}

	log.Printf("Posición guardada en recorrido %d: lat=%f, lon=%f", recID, lat, lon)
	return true, "Ubicación guardada (recorrido " + strconv.Itoa(recID) + ")"
}
