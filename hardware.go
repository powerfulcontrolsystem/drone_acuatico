package main

// ==================== FUNCIONES DE HARDWARE Y SISTEMA ====================
// Control de GPIO (relés y motores), monitoreo del sistema
// Go puro con acceso a sysfs GPIO y comandos del sistema

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

// ==================== CONFIGURACIÓN GPIO ====================

// Pines GPIO (BCM) para relés
var relesPines = map[int]int{
	1: 4, 2: 7, 3: 8, 4: 9, 5: 11, 6: 21, 7: 22, 8: 23, 9: 24,
}

// Pines GPIO (BCM) para motores PWM
var motoresPWM = map[int]int{
	1: 18, 2: 13, 3: 19, 4: 12,
}

// Estado de los relés
var (
	estadoReles   = map[int]bool{}
	estadoRelesMu sync.RWMutex
)

// Estado GPIO/pigpio
var (
	gpioDisponible   bool
	pigpioDisponible bool
	umbralPesoKg     = 5.0
)

// ==================== GESTIÓN DE PROCESOS ====================

// matarProcesosServidorPrevios termina servidores anteriores
func matarProcesosServidorPrevios() int {
	pidActual := os.Getpid()
	procesosTerminados := 0

	cmd := exec.Command("pgrep", "-f", "drone_acuatico")
	salida, err := cmd.Output()
	if err != nil {
		log.Println("No se encontraron procesos del servidor previos")
		return 0
	}

	pids := strings.Split(strings.TrimSpace(string(salida)), "\n")
	for _, pidStr := range pids {
		pid, err := strconv.Atoi(strings.TrimSpace(pidStr))
		if err != nil || pid == pidActual {
			continue
		}

		proc, err := os.FindProcess(pid)
		if err != nil {
			continue
		}

		if err := proc.Signal(syscall.SIGTERM); err == nil {
			log.Printf("Proceso servidor previo terminado (PID: %d)", pid)
			procesosTerminados++
		}
	}

	if procesosTerminados > 0 {
		log.Printf("Se terminaron %d proceso(s) del servidor previo(s)", procesosTerminados)
	}
	return procesosTerminados
}

// ==================== GPIO VIA SYSFS ====================

func exportarGPIO(pin int) error {
	ruta := "/sys/class/gpio/export"
	return os.WriteFile(ruta, []byte(strconv.Itoa(pin)), 0644)
}

func configurarDireccionGPIO(pin int, direccion string) error {
	ruta := fmt.Sprintf("/sys/class/gpio/gpio%d/direction", pin)
	return os.WriteFile(ruta, []byte(direccion), 0644)
}

func escribirGPIO(pin int, valor int) error {
	ruta := fmt.Sprintf("/sys/class/gpio/gpio%d/value", pin)
	return os.WriteFile(ruta, []byte(strconv.Itoa(valor)), 0644)
}

// inicializarGPIO configura los pines GPIO para relés y motores
func inicializarGPIO() bool {
	// Verificar si pigpiod está disponible
	if err := exec.Command("pigs", "t").Run(); err == nil {
		pigpioDisponible = true
		log.Println("pigpio disponible (daemon corriendo)")
	}

	exito := true
	for numero, pin := range relesPines {
		exportarGPIO(pin)
		time.Sleep(50 * time.Millisecond)

		if err := configurarDireccionGPIO(pin, "out"); err != nil {
			log.Printf("Error configurando relé %d (GPIO %d): %v", numero, pin, err)
			exito = false
			continue
		}

		// Estado inicial: HIGH = apagado (relé activo-bajo)
		escribirGPIO(pin, 1)
		log.Printf("Relé %d → GPIO %d", numero, pin)
	}

	if !pigpioDisponible {
		for numero, pin := range motoresPWM {
			exportarGPIO(pin)
			time.Sleep(50 * time.Millisecond)
			configurarDireccionGPIO(pin, "out")
			log.Printf("Motor %d → GPIO %d", numero, pin)
		}
	}

	if exito || pigpioDisponible {
		gpioDisponible = true
		log.Println("GPIO inicializado correctamente")
		return true
	}

	log.Println("GPIO no disponible - Modo simulación")
	return false
}

// ==================== CONTROL DE RELÉS ====================

func controlarRele(numero int, encender bool) (bool, string) {
	if _, existe := relesPines[numero]; !existe {
		return false, fmt.Sprintf("Relé %d no válido (1-9)", numero)
	}

	guardarEstadoRele(numero, encender)

	if !gpioDisponible {
		estadoRelesMu.Lock()
		estadoReles[numero] = encender
		estadoRelesMu.Unlock()
		estado := "OFF"
		if encender {
			estado = "ON"
		}
		log.Printf("[SIM] Relé %d: %s", numero, estado)
		return true, ""
	}

	pin := relesPines[numero]
	valor := 1 // HIGH = apagado
	if encender {
		valor = 0 // LOW = encendido
	}

	if err := escribirGPIO(pin, valor); err != nil {
		log.Printf("Error controlando relé %d: %v", numero, err)
		return false, err.Error()
	}

	estadoRelesMu.Lock()
	estadoReles[numero] = encender
	estadoRelesMu.Unlock()

	estado := "APAGADO"
	if encender {
		estado = "ENCENDIDO"
	}
	log.Printf("Relé %d: %s", numero, estado)
	return true, ""
}

// ==================== CONTROL DE MOTORES ====================

func controlarMotor(direccion string, velocidad int) (bool, string) {
	pinIzq := motoresPWM[1]
	pinDer := motoresPWM[2]

	if pigpioDisponible {
		return controlarMotorPigpio(direccion, velocidad, pinIzq, pinDer)
	}

	if !gpioDisponible {
		log.Printf("[SIM] Motor %s al %d%% (tanque)", direccion, velocidad)
		return true, ""
	}

	log.Printf("[SIM] Motor %s al %d%% (sin PWM hardware)", direccion, velocidad)
	return true, ""
}

func controlarMotorPigpio(direccion string, velocidad, pinIzq, pinDer int) (bool, string) {
	porcentajeAPulso := func(p int) int {
		return 1000 + (2000-1000)*p/100
	}

	var errIzq, errDer error

	switch direccion {
	case "adelante":
		pulso := porcentajeAPulso(velocidad)
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), strconv.Itoa(pulso)).Run()
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), strconv.Itoa(pulso)).Run()
		log.Printf("Motores adelante (pigpio): izq=%d%%, der=%d%%", velocidad, velocidad)

	case "atras":
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), "0").Run()
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), "0").Run()
		log.Println("Motores atrás (pigpio, detenidos)")

	case "izquierda":
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), "0").Run()
		pulso := porcentajeAPulso(velocidad)
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), strconv.Itoa(pulso)).Run()
		log.Printf("Giro izquierda (pigpio): izq=0%%, der=%d%%", velocidad)

	case "derecha":
		pulso := porcentajeAPulso(velocidad)
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), strconv.Itoa(pulso)).Run()
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), "0").Run()
		log.Printf("Giro derecha (pigpio): izq=%d%%, der=0%%", velocidad)

	case "parar":
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), "0").Run()
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), "0").Run()
		log.Println("Motores detenidos (pigpio)")

	default:
		errIzq = exec.Command("pigs", "SERVO", strconv.Itoa(pinIzq), "0").Run()
		errDer = exec.Command("pigs", "SERVO", strconv.Itoa(pinDer), "0").Run()
		log.Printf("Dirección desconocida: %s", direccion)
	}

	if errIzq != nil || errDer != nil {
		msg := ""
		if errIzq != nil {
			msg += errIzq.Error()
		}
		if errDer != nil {
			msg += " " + errDer.Error()
		}
		return false, msg
	}
	return true, ""
}

// liberarGPIO libera los recursos GPIO
func liberarGPIO() {
	if pigpioDisponible {
		for _, pin := range motoresPWM {
			exec.Command("pigs", "SERVO", strconv.Itoa(pin), "0").Run()
		}
		log.Println("Motores detenidos (pigpio)")
	}

	for _, pin := range relesPines {
		os.WriteFile("/sys/class/gpio/unexport", []byte(strconv.Itoa(pin)), 0644)
	}
	if !pigpioDisponible {
		for _, pin := range motoresPWM {
			os.WriteFile("/sys/class/gpio/unexport", []byte(strconv.Itoa(pin)), 0644)
		}
	}
	log.Println("GPIO liberado")
}

// ==================== FUNCIONES DE MONITOREO ====================

func obtenerVoltajeRaspberry() map[string]interface{} {
	cmd := exec.Command("vcgencmd", "get_throttled")
	salida, err := cmd.Output()
	if err != nil {
		return map[string]interface{}{"voltaje": 0.0, "alerta": false, "estado_raw": "error"}
	}

	valor := strings.TrimSpace(string(salida))
	if strings.Contains(valor, "=") {
		partes := strings.SplitN(valor, "=", 2)
		valor = partes[1]
	}

	alerta := strings.HasSuffix(valor, "5") || strings.HasSuffix(valor, "05") ||
		strings.HasSuffix(valor, "50005") || strings.HasSuffix(valor, "80005")

	voltaje := 5.0
	if alerta {
		voltaje = 4.5
	}

	return map[string]interface{}{"voltaje": voltaje, "alerta": alerta, "estado_raw": valor}
}

func obtenerRAM() map[string]interface{} {
	datos, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return map[string]interface{}{"total": 0, "used": 0, "available": 0, "percent": 0}
	}

	lineas := strings.Split(string(datos), "\n")
	var total, available int

	for _, linea := range lineas {
		if strings.HasPrefix(linea, "MemTotal:") {
			total = parsearMemInfo(linea) / 1024
		}
		if strings.HasPrefix(linea, "MemAvailable:") {
			available = parsearMemInfo(linea) / 1024
		}
	}

	used := total - available
	percent := 0
	if total > 0 {
		percent = used * 100 / total
	}

	return map[string]interface{}{"total": total, "used": used, "available": available, "percent": percent}
}

func obtenerTemperatura() map[string]interface{} {
	cmd := exec.Command("vcgencmd", "measure_temp")
	salida, err := cmd.Output()
	if err != nil {
		return map[string]interface{}{"temperatura": 0, "unidad": "C"}
	}

	texto := strings.TrimSpace(string(salida))
	texto = strings.Replace(texto, "temp=", "", 1)
	texto = strings.Replace(texto, "'C", "", 1)
	temp, _ := strconv.ParseFloat(texto, 64)

	return map[string]interface{}{"temperatura": temp, "unidad": "C"}
}

func obtenerCPU() map[string]interface{} {
	datos, err := os.ReadFile("/proc/stat")
	if err != nil {
		return map[string]interface{}{"porcentaje": 0, "cores": 1}
	}

	lineas := strings.Split(string(datos), "\n")
	if len(lineas) == 0 {
		return map[string]interface{}{"porcentaje": 0, "cores": 1}
	}

	campos := strings.Fields(lineas[0])
	if len(campos) < 6 || campos[0] != "cpu" {
		return map[string]interface{}{"porcentaje": 0, "cores": 1}
	}

	user, _ := strconv.Atoi(campos[1])
	nice, _ := strconv.Atoi(campos[2])
	system, _ := strconv.Atoi(campos[3])
	idle, _ := strconv.Atoi(campos[4])
	iowait, _ := strconv.Atoi(campos[5])

	total := user + nice + system + idle + iowait
	usoCPU := 0
	if total > 0 {
		usoCPU = (total - idle) * 100 / total
	}

	numCores := 0
	for _, l := range lineas {
		if strings.HasPrefix(l, "cpu") && !strings.HasPrefix(l, "cpu ") {
			numCores++
		}
	}
	if numCores == 0 {
		numCores = 1
	}

	return map[string]interface{}{"porcentaje": usoCPU, "cores": numCores}
}

func obtenerAlmacenamiento() map[string]interface{} {
	var stat syscall.Statfs_t
	if err := syscall.Statfs("/", &stat); err != nil {
		return map[string]interface{}{
			"total_gb": 0.0, "usado_gb": 0.0, "disponible_gb": 0.0, "porcentaje": 0,
		}
	}

	totalBytes := stat.Blocks * uint64(stat.Bsize)
	freeBytes := stat.Bfree * uint64(stat.Bsize)
	usedBytes := totalBytes - freeBytes

	totalGB := float64(totalBytes) / (1024 * 1024 * 1024)
	usadoGB := float64(usedBytes) / (1024 * 1024 * 1024)
	disponibleGB := float64(freeBytes) / (1024 * 1024 * 1024)
	porcentaje := 0
	if totalBytes > 0 {
		porcentaje = int(usedBytes * 100 / totalBytes)
	}

	return map[string]interface{}{
		"total_gb": redondear(totalGB, 2), "usado_gb": redondear(usadoGB, 2),
		"disponible_gb": redondear(disponibleGB, 2), "porcentaje": porcentaje,
	}
}

func obtenerUsoDisco() map[string]interface{} {
	var stat syscall.Statfs_t
	if err := syscall.Statfs("/", &stat); err != nil {
		return map[string]interface{}{"uso_porcentaje": 0, "timestamp": float64(time.Now().Unix())}
	}

	totalBytes := stat.Blocks * uint64(stat.Bsize)
	freeBytes := stat.Bfree * uint64(stat.Bsize)
	usedBytes := totalBytes - freeBytes
	porcentaje := 0.0
	if totalBytes > 0 {
		porcentaje = float64(usedBytes) / float64(totalBytes) * 100
	}

	return map[string]interface{}{"uso_porcentaje": redondear(porcentaje, 1), "timestamp": float64(time.Now().Unix())}
}

func obtenerPeso() map[string]interface{} {
	pesoKg := 1.2
	return map[string]interface{}{
		"peso_kg": pesoKg, "umbral_kg": umbralPesoKg, "alerta": pesoKg >= umbralPesoKg,
	}
}

func obtenerVelocidadRed() map[string]interface{} {
	cmd := exec.Command("speedtest-cli", "--simple")
	cmd.Env = os.Environ()
	salida, err := cmd.Output()
	if err == nil {
		lineas := strings.Split(strings.TrimSpace(string(salida)), "\n")
		for _, linea := range lineas {
			if strings.Contains(strings.ToLower(linea), "download") {
				partes := strings.Fields(linea)
				if len(partes) >= 2 {
					velocidadMbps, err := strconv.ParseFloat(partes[1], 64)
					if err == nil {
						return map[string]interface{}{"velocidad": velocidadMbps * 1000}
					}
				}
			}
		}
	}

	cmd = exec.Command("curl", "-o", "/dev/null", "-s", "-w", "%{speed_download}",
		"http://speedtest.ftp.otenet.gr/files/test10Mb.db")
	salida, err = cmd.Output()
	if err == nil {
		velocidadBytesSeg, err := strconv.ParseFloat(strings.TrimSpace(string(salida)), 64)
		if err == nil && velocidadBytesSeg > 0 {
			return map[string]interface{}{"velocidad": velocidadBytesSeg * 8 / 1000}
		}
	}

	return map[string]interface{}{"velocidad": 0}
}

func obtenerWifi() map[string]interface{} {
	cmd := exec.Command("nmcli", "dev", "wifi", "list", "--rescan", "no")
	salida, err := cmd.Output()
	if err == nil {
		lineas := strings.Split(string(salida), "\n")
		for _, linea := range lineas {
			if strings.Contains(linea, "*") {
				campos := strings.Fields(linea)
				if len(campos) >= 7 {
					for i, campo := range campos {
						if campo == "*" {
							// Buscar SSID y señal
							ssid := ""
							for j := 0; j < len(campos); j++ {
								if strings.Count(campos[j], ":") == 5 && len(campos[j]) == 17 {
									if j+1 < len(campos) {
										ssid = campos[j+1]
									}
									break
								}
							}
							// La señal suele estar unas posiciones después
							for k := i + 1; k < len(campos); k++ {
								calidad, err := strconv.Atoi(campos[k])
								if err == nil && calidad > 0 && calidad <= 100 {
									rssi := calidad/2 - 100
									return map[string]interface{}{
										"ssid": ssid, "rssi_dbm": rssi, "calidad": calidad,
									}
								}
							}
						}
					}
				}
			}
		}
	}

	cmd = exec.Command("wpa_cli", "signal_poll")
	salida, err = cmd.Output()
	if err == nil {
		for _, linea := range strings.Split(string(salida), "\n") {
			if strings.HasPrefix(linea, "RSSI=") {
				rssi, err := strconv.Atoi(strings.TrimPrefix(linea, "RSSI="))
				if err == nil && rssi < 0 {
					calidad := 2 * (rssi + 100)
					if calidad < 0 {
						calidad = 0
					}
					if calidad > 100 {
						calidad = 100
					}
					return map[string]interface{}{"ssid": "", "rssi_dbm": rssi, "calidad": calidad}
				}
			}
		}
	}

	return map[string]interface{}{"ssid": "", "rssi_dbm": nil, "calidad": nil}
}

// ==================== FUNCIONES DE SISTEMA ====================

func apagarSistema() (bool, string) {
	log.Println("Iniciando apagado del sistema...")
	cmd := exec.Command("sudo", "shutdown", "-h", "now")
	if err := cmd.Start(); err != nil {
		return false, err.Error()
	}
	return true, "Apagando sistema..."
}

func reiniciarSistema() (bool, string) {
	log.Println("Iniciando reinicio del sistema...")
	cmd := exec.Command("sudo", "reboot")
	if err := cmd.Start(); err != nil {
		return false, err.Error()
	}
	return true, "Reiniciando sistema..."
}

// ==================== UTILIDADES ====================

func parsearMemInfo(linea string) int {
	campos := strings.Fields(linea)
	if len(campos) >= 2 {
		v, _ := strconv.Atoi(campos[1])
		return v
	}
	return 0
}

func redondear(valor float64, decimales int) float64 {
	multi := 1.0
	for i := 0; i < decimales; i++ {
		multi *= 10
	}
	return float64(int(valor*multi+0.5)) / multi
}

func configurarSenales(limpieza func()) {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-c
		log.Println("\nSeñal de cierre recibida...")
		limpieza()
		os.Exit(0)
	}()
}

func obtenerIODisco() map[string]interface{} {
	dispositivo := "mmcblk0"
	tamanoSector := 512

	sectorPath := filepath.Join("/sys/block", dispositivo, "queue/hw_sector_size")
	if datos, err := os.ReadFile(sectorPath); err == nil {
		if v, err := strconv.Atoi(strings.TrimSpace(string(datos))); err == nil {
			tamanoSector = v
		}
	}

	datos, err := os.ReadFile("/proc/diskstats")
	if err != nil {
		return map[string]interface{}{
			"dispositivo": dispositivo, "sectores_leidos": 0,
			"sectores_escritos": 0, "tamano_sector": tamanoSector,
			"timestamp": float64(time.Now().Unix()),
		}
	}

	for _, linea := range strings.Split(string(datos), "\n") {
		partes := strings.Fields(linea)
		if len(partes) >= 14 && partes[2] == dispositivo {
			sectoresLeidos, _ := strconv.Atoi(partes[5])
			sectoresEscritos, _ := strconv.Atoi(partes[9])
			return map[string]interface{}{
				"dispositivo": dispositivo, "sectores_leidos": sectoresLeidos,
				"sectores_escritos": sectoresEscritos, "tamano_sector": tamanoSector,
				"timestamp": float64(time.Now().Unix()),
			}
		}
	}

	return map[string]interface{}{
		"dispositivo": dispositivo, "sectores_leidos": 0,
		"sectores_escritos": 0, "tamano_sector": tamanoSector,
		"timestamp": float64(time.Now().Unix()),
	}
}
