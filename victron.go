package main

// ==================== VICTRON VE.Direct (SERIAL) ====================
// Lectura del controlador de carga Victron 75/15 por protocolo VE.Direct
// Formato: texto ASCII con campos separados por tabulación

import (
	"bufio"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// ==================== DETECCIÓN Y LECTURA ====================

// detectarPuertoVictron busca automáticamente el puerto serial del Victron
func detectarPuertoVictron() string {
	patrones := []string{
		"/dev/ttyUSB*",
		"/dev/ttyACM*",
		"/dev/serial/by-id/*Victron*",
		"/dev/serial/by-id/*VE*",
	}

	for _, patron := range patrones {
		matches, _ := filepath.Glob(patron)
		for _, puerto := range matches {
			// Intentar abrir y verificar si tiene datos VE.Direct
			if verificarPuertoVictron(puerto) {
				log.Printf("Victron detectado en %s", puerto)
				return puerto
			}
		}
	}

	log.Println("No se detectó controlador Victron en ningún puerto serial")
	return ""
}

// verificarPuertoVictron verifica si un puerto tiene datos VE.Direct
func verificarPuertoVictron(puerto string) bool {
	// Configurar puerto a 19200 baudios
	if err := exec.Command("stty", "-F", puerto, "19200", "raw", "-echo",
		"cs8", "-parenb", "-cstopb", "min", "0", "time", "5").Run(); err != nil {
		return false
	}

	archivo, err := os.Open(puerto)
	if err != nil {
		return false
	}
	defer archivo.Close()

	scanner := bufio.NewScanner(archivo)
	deadline := time.After(2 * time.Second)

	for i := 0; i < 10; i++ {
		select {
		case <-deadline:
			return false
		default:
		}
		if scanner.Scan() {
			linea := scanner.Text()
			if strings.HasPrefix(linea, "V\t") || strings.HasPrefix(linea, "I\t") || strings.HasPrefix(linea, "VPV\t") {
				return true
			}
		}
	}
	return false
}

// leerVictron lee datos del controlador Victron por VE.Direct
func leerVictron() map[string]interface{} {
	puerto := detectarPuertoVictron()
	if puerto == "" {
		return map[string]interface{}{
			"exito":            false,
			"error":            "Puerto Victron no encontrado",
			"panel_voltaje":    0.0,
			"panel_corriente":  0.0,
			"potencia":         0,
			"bateria_voltaje":  0.0,
			"bateria_corriente": 0.0,
			"estado":           "desconectado",
			"intervalo_frame_s": nil,
		}
	}

	// Configurar puerto serial
	if err := exec.Command("stty", "-F", puerto, "19200", "raw", "-echo",
		"cs8", "-parenb", "-cstopb", "min", "0", "time", "10").Run(); err != nil {
		return errorVictron("Error configurando puerto: " + err.Error())
	}

	archivo, err := os.Open(puerto)
	if err != nil {
		return errorVictron("Error abriendo puerto: " + err.Error())
	}
	defer archivo.Close()

	scanner := bufio.NewScanner(archivo)
	inicio := time.Now()
	timeout := 5 * time.Second

	datosFrameActual := make(map[string]string)
	var datosFrameFinal map[string]string
	var checksumT1 *time.Time
	var intervaloFrame *float64

	for time.Since(inicio) < timeout {
		if !scanner.Scan() {
			break
		}

		linea := strings.TrimSpace(scanner.Text())
		if linea == "" {
			continue
		}

		// Dividir por tabulación
		partes := strings.SplitN(linea, "\t", 2)
		if len(partes) == 2 {
			datosFrameActual[partes[0]] = partes[1]
		}

		// Si encontramos Checksum, tenemos un bloque completo
		if strings.HasPrefix(linea, "Checksum") {
			if len(datosFrameActual) > 0 {
				datosFrameFinal = copiarMapa(datosFrameActual)
			}
			if checksumT1 == nil {
				ahora := time.Now()
				checksumT1 = &ahora
				datosFrameActual = make(map[string]string)
				continue
			} else {
				intervalo := time.Since(*checksumT1).Seconds()
				intervaloFrame = &intervalo
				break
			}
		}
	}

	datos := datosFrameFinal
	if datos == nil {
		datos = datosFrameActual
	}

	// Verificar datos mínimos
	if len(datos) == 0 || datos["V"] == "" {
		return map[string]interface{}{
			"exito":            false,
			"error":            "Datos incompletos o timeout",
			"panel_voltaje":    0.0,
			"panel_corriente":  0.0,
			"potencia":         0,
			"bateria_voltaje":  0.0,
			"bateria_corriente": 0.0,
			"estado":           "error",
			"intervalo_frame_s": nil,
		}
	}

	// Parsear datos
	resultado := parsearDatosVictron(datos)
	resultado["exito"] = true
	resultado["puerto"] = puerto
	resultado["intervalo_frame_s"] = intervaloFrame
	return resultado
}

// ==================== PARSEO DE DATOS ====================

func parsearDatosVictron(datos map[string]string) map[string]interface{} {
	// Estados de carga del Victron
	estadosCarga := map[string]string{
		"0":   "apagado",
		"2":   "falla",
		"3":   "bulk",
		"4":   "absorption",
		"5":   "float",
		"7":   "equalize",
		"252": "external_control",
	}

	// Voltaje batería (mV a V)
	bateriaVoltaje := parseFloat(datos["V"]) / 1000.0
	// Corriente batería (mA a A)
	bateriaCorriente := parseFloat(datos["I"]) / 1000.0
	// Voltaje panel (mV a V)
	panelVoltaje := parseFloat(datos["VPV"]) / 1000.0
	// Potencia panel (W)
	potenciaPanel := parseInt(datos["PPV"])

	// Calcular corriente panel aproximada (P = V × I)
	var panelCorriente float64
	if panelVoltaje > 0 {
		panelCorriente = float64(potenciaPanel) / panelVoltaje
	}

	// Estado de carga
	estadoCode := datos["CS"]
	if estadoCode == "" {
		estadoCode = "0"
	}
	estado := estadosCarga[estadoCode]
	if estado == "" {
		estado = "desconocido"
	}

	// Error code
	errorCode := parseInt(datos["ERR"])
	// Yield today (Wh)
	yieldToday := parseInt(datos["H20"])
	// Max power today (W)
	maxPowerToday := parseInt(datos["H21"])
	// Yield total (kWh × 10)
	yieldTotal := parseFloat(datos["H19"]) / 10.0
	// Yield ayer (Wh)
	yieldAyer := parseInt(datos["H22"])
	// Max power ayer (W)
	maxPowerAyer := parseInt(datos["H23"])

	// Porcentaje de batería basado en voltaje
	minVoltaje := 10.0
	maxVoltaje := 14.0
	porcentaje := int((bateriaVoltaje - minVoltaje) / (maxVoltaje - minVoltaje) * 100)
	if porcentaje < 0 {
		porcentaje = 0
	}
	if porcentaje > 100 {
		porcentaje = 100
	}

	log.Printf("Victron: Panel %.1fV %.2fA (%dW), Batería %.1fV %.2fA (%d%%), Estado: %s",
		panelVoltaje, panelCorriente, potenciaPanel,
		bateriaVoltaje, bateriaCorriente, porcentaje, estado)

	return map[string]interface{}{
		"panel_voltaje":    redondearVictron(panelVoltaje, 2),
		"panel_corriente":  redondearVictron(panelCorriente, 2),
		"potencia":         potenciaPanel,
		"bateria_voltaje":  redondearVictron(bateriaVoltaje, 2),
		"bateria_corriente": redondearVictron(bateriaCorriente, 2),
		"porcentaje":       porcentaje,
		"estado":           estado,
		"error_code":       errorCode,
		"yield_today":      yieldToday,
		"yield_total":      redondearVictron(yieldTotal, 1),
		"max_power_today":  maxPowerToday,
		"yield_ayer":       yieldAyer,
		"max_power_ayer":   maxPowerAyer,
		"cargando":         potenciaPanel > 0,
		"raw_data":         datos,
	}
}

// ==================== FUNCIONES DE BATERÍA Y SOLAR ====================

// obtenerBateria obtiene el estado de la batería desde el Victron
func obtenerBateria() map[string]interface{} {
	datosVictron := leerVictron()

	exito, _ := datosVictron["exito"].(bool)
	if exito {
		voltaje, _ := datosVictron["bateria_voltaje"].(float64)
		corriente, _ := datosVictron["bateria_corriente"].(float64)
		estado, _ := datosVictron["estado"].(string)

		porcentaje := int((voltaje - 10.5) / (14.7 - 10.5) * 100)
		if porcentaje < 0 {
			porcentaje = 0
		}
		if porcentaje > 100 {
			porcentaje = 100
		}

		return map[string]interface{}{
			"porcentaje": porcentaje,
			"voltaje":    voltaje,
			"corriente":  corriente,
			"estado":     estado,
			"conectado":  true,
		}
	}

	errorMsg := "No detectado"
	if e, ok := datosVictron["error"].(string); ok {
		errorMsg = e
	}
	return map[string]interface{}{
		"porcentaje": 0,
		"voltaje":    0.0,
		"corriente":  0.0,
		"estado":     "desconectado",
		"conectado":  false,
		"error":      errorMsg,
	}
}

// obtenerSolar obtiene el estado de los paneles solares
func obtenerSolar() map[string]interface{} {
	datosVictron := leerVictron()

	exito, _ := datosVictron["exito"].(bool)
	if exito {
		datosVictron["conectado"] = true
		return datosVictron
	}

	errorMsg := "No detectado"
	if e, ok := datosVictron["error"].(string); ok {
		errorMsg = e
	}
	return map[string]interface{}{
		"panel_voltaje":    0.0,
		"panel_corriente":  0.0,
		"potencia":         0,
		"bateria_voltaje":  0.0,
		"bateria_corriente": 0.0,
		"estado":           "desconectado",
		"conectado":        false,
		"exito":            false,
		"error":            errorMsg,
		"intervalo_frame_s": nil,
	}
}

// ==================== UTILIDADES ====================

func errorVictron(msg string) map[string]interface{} {
	return map[string]interface{}{
		"exito":            false,
		"error":            msg,
		"panel_voltaje":    0.0,
		"panel_corriente":  0.0,
		"potencia":         0,
		"bateria_voltaje":  0.0,
		"bateria_corriente": 0.0,
		"estado":           "error",
		"intervalo_frame_s": nil,
	}
}

func copiarMapa(m map[string]string) map[string]string {
	copia := make(map[string]string)
	for k, v := range m {
		copia[k] = v
	}
	return copia
}

func parseFloat(s string) float64 {
	v, _ := strconv.ParseFloat(strings.TrimSpace(s), 64)
	return v
}

func parseInt(s string) int {
	v, _ := strconv.Atoi(strings.TrimSpace(s))
	return v
}

func redondearVictron(v float64, decimales int) float64 {
	factor := 1.0
	for i := 0; i < decimales; i++ {
		factor *= 10
	}
	return float64(int(v*factor+0.5)) / factor
}
