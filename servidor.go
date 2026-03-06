package main

// ==================== SERVIDOR HTTP/WEBSOCKET ====================
// Servidor web principal del Drone Acuático
// Sin librerías externas - usa net/http estándar

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ==================== VARIABLES GLOBALES ====================

const (
	HOST   = "0.0.0.0"
	PUERTO = 8080
)

var (
	velocidadActual   = 50
	velocidadActualMu sync.RWMutex

	recorridoActivo   *int
	recorridoActivoMu sync.Mutex

	gestorWS *GestorClientes

	baseDir string // Directorio base del ejecutable
)

// ==================== UTILIDADES HTTP ====================

// relesAJSON convierte map[int]bool a map[string]interface{} para JSON
func relesAJSON(reles map[int]bool) map[string]interface{} {
	result := make(map[string]interface{})
	for k, v := range reles {
		result[strconv.Itoa(k)] = v
	}
	return result
}

func enviarJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func leerJSON(r *http.Request) (map[string]interface{}, error) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		return nil, err
	}
	defer r.Body.Close()
	var datos map[string]interface{}
	err = json.Unmarshal(body, &datos)
	return datos, err
}

func servirPagina(w http.ResponseWriter, nombre string) {
	archivo := filepath.Join(baseDir, "paginas", nombre)
	if _, err := os.Stat(archivo); os.IsNotExist(err) {
		enviarJSON(w, 404, map[string]interface{}{"error": "Página no encontrada"})
		return
	}
	http.ServeFile(w, &http.Request{}, archivo)
}

// ==================== MANEJADORES DE PÁGINAS ====================

func indexHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "control remoto digital.html"))
}

func configuracionHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "configuracion.html"))
}

func mapaGPSHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "mapa_gps.html"))
}

func energiaSolarHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "energia_solar.html"))
}

func pruebaBrushlessHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "prueba_algoritmo_motores_brushless.html"))
}

func ayudaHandler(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, filepath.Join(baseDir, "paginas", "ayuda.html"))
}

// ==================== MANEJADORES API ====================

func apiConfigHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(200)
		return
	}

	if r.Method == "GET" {
		config := obtenerConfiguracion()
		if config != nil {
			enviarJSON(w, 200, config)
		} else {
			enviarJSON(w, 404, map[string]interface{}{"error": "No hay configuración"})
		}
		return
	}

	if r.Method == "POST" {
		datos, err := leerJSON(r)
		if err != nil {
			enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": err.Error()})
			return
		}
		if guardarConfiguracion(datos) {
			// Notificar a clientes WS
			gestorWS.BroadcastJSON(map[string]interface{}{
				"tipo":    "config_actualizada",
				"mensaje": "Nombres de relés actualizados",
			})
			enviarJSON(w, 200, map[string]interface{}{"exito": true, "mensaje": "Configuración guardada correctamente"})
		} else {
			enviarJSON(w, 500, map[string]interface{}{"exito": false, "mensaje": "Error al guardar configuración"})
		}
		return
	}

	enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
}

func apiGPSActualHandler(w http.ResponseWriter, r *http.Request) {
	gps := obtenerPosicionGPS()
	if gps != nil {
		enviarJSON(w, 200, map[string]interface{}{
			"exito": true,
			"datos": gps,
		})
	} else {
		enviarJSON(w, 404, map[string]interface{}{
			"exito": false,
			"error": "No hay datos GPS disponibles",
		})
	}
}

func apiTestWifiHandler(w http.ResponseWriter, r *http.Request) {
	wifi := obtenerWifi()
	log.Printf("Datos WiFi obtenidos: %v", wifi)
	enviarJSON(w, 200, map[string]interface{}{
		"exito": true,
		"datos": wifi,
	})
}

func apiIndicadoresHandler(w http.ResponseWriter, r *http.Request) {
	ram := obtenerRAM()
	temp := obtenerTemperatura()
	cpu := obtenerCPU()
	disco := obtenerAlmacenamiento()
	discoUso := obtenerUsoDisco()
	peso := obtenerPeso()
	wifi := obtenerWifi()
	gps := obtenerPayloadGPS()
	bat := obtenerBateria()
	solar := obtenerSolar()
	voltaje := obtenerVoltajeRaspberry()

	var red float64
	if vel := obtenerVelocidadRed(); vel != nil {
		if v, ok := vel["velocidad"].(float64); ok {
			red = v
		}
	}

	velocidadActualMu.RLock()
	vel := velocidadActual
	velocidadActualMu.RUnlock()

	enviarJSON(w, 200, map[string]interface{}{
		"exito": true,
		"datos": map[string]interface{}{
			"ram":         ram,
			"temperatura": temp,
			"cpu":         cpu,
			"disco":       disco,
			"disco_uso":   discoUso,
			"peso":        peso,
			"wifi":        wifi,
			"gps":         gps,
			"bateria":     bat,
			"solar":       solar,
			"voltaje":     voltaje,
			"red":         red,
			"velocidad":   vel,
		},
	})
}

func apiTemperaturaHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
		return
	}

	temp := obtenerTemperatura()
	enviarJSON(w, 200, map[string]interface{}{
		"exito": true,
		"datos":  temp,
	})
}

func apiRelesHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(200)
		return
	}

	if r.Method == "GET" {
		config := obtenerConfiguracion()
		var nombresReles interface{} = nil
		if config != nil {
			nombresReles = config["reles"]
		}
		enviarJSON(w, 200, map[string]interface{}{
			"exito":        true,
			"reles":        relesAJSON(obtenerEstadoReles()),
			"nombres_reles": nombresReles,
		})
		return
	}

	if r.Method == "POST" {
		datos, err := leerJSON(r)
		if err != nil {
			enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": err.Error()})
			return
		}

		numero := toInt(datos["numero"])
		if numero < 1 || numero > 9 {
			enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": "Número de relé inválido (1-9)"})
			return
		}

		estados := obtenerEstadoReles()
		estadoActual := estados[numero]

		nuevoEstado := !estadoActual
		if v, ok := datos["estado"].(bool); ok {
			nuevoEstado = v
		}

		exito, errMsg := controlarRele(numero, nuevoEstado)
		if !exito {
			enviarJSON(w, 500, map[string]interface{}{
				"exito":  false,
				"numero": numero,
				"estado": nuevoEstado,
				"error":  errMsg,
			})
			return
		}

		relesJSON := relesAJSON(obtenerEstadoReles())
		config := obtenerConfiguracion()
		var nombresReles interface{} = nil
		if config != nil {
			nombresReles = config["reles"]
		}

		gestorWS.BroadcastJSON(map[string]interface{}{
			"tipo":          "reles",
			"reles":         relesJSON,
			"nombres_reles": nombresReles,
		})

		enviarJSON(w, 200, map[string]interface{}{
			"exito":         true,
			"numero":        numero,
			"estado":        nuevoEstado,
			"reles":         relesJSON,
			"nombres_reles": nombresReles,
		})
		return
	}

	enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
}

func apiONVIFDiscoverHandler(w http.ResponseWriter, r *http.Request) {
	dispositivos := descubrirONVIF(3)
	enviarJSON(w, 200, map[string]interface{}{
		"exito":        true,
		"dispositivos": dispositivos,
	})
}

func apiUbicacionesHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == "OPTIONS" {
		w.WriteHeader(200)
		return
	}

	if r.Method == "GET" {
		busqueda := r.URL.Query().Get("q")
		if busqueda == "" {
			busqueda = r.URL.Query().Get("busqueda")
		}
		categoria := r.URL.Query().Get("categoria")
		ubicaciones := obtenerUbicaciones(categoria, busqueda)
		enviarJSON(w, 200, map[string]interface{}{
			"exito":       true,
			"ubicaciones": ubicaciones,
		})
		return
	}

	if r.Method == "POST" {
		datos, err := leerJSON(r)
		if err != nil {
			enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": err.Error()})
			return
		}
		nombre, _ := datos["nombre"].(string)
		descripcion, _ := datos["descripcion"].(string)
		lat, latOk := datos["latitud"].(float64)
		lon, lonOk := datos["longitud"].(float64)
		if !latOk || !lonOk {
			enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": "Latitud y longitud requeridas"})
			return
		}
		id := guardarUbicacion(nombre, descripcion, lat, lon)
		if id > 0 {
			enviarJSON(w, 200, map[string]interface{}{"exito": true, "id": id})
		} else {
			enviarJSON(w, 500, map[string]interface{}{"exito": false, "error": "No se pudo guardar la ubicación"})
		}
		return
	}

	enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
}

func apiRecorridosHandler(w http.ResponseWriter, r *http.Request) {
	activosStr := strings.ToLower(r.URL.Query().Get("activos"))
	activos := activosStr == "1" || activosStr == "true" || activosStr == "si" || activosStr == "sí" || activosStr == "yes"
	recorridos := obtenerTodosRecorridos(activos)
	enviarJSON(w, 200, map[string]interface{}{
		"exito":      true,
		"recorridos": recorridos,
	})
}

func apiRecorridoDetalleHandler(w http.ResponseWriter, r *http.Request) {
	// Extraer ID del path: /api/recorridos/123
	partes := strings.Split(r.URL.Path, "/")
	if len(partes) < 4 {
		enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": "ID de recorrido requerido"})
		return
	}
	idStr := partes[len(partes)-1]
	id, err := strconv.Atoi(idStr)
	if err != nil {
		enviarJSON(w, 400, map[string]interface{}{"exito": false, "error": "ID de recorrido inválido"})
		return
	}
	detalle := obtenerRecorrido(id)
	if detalle == nil {
		enviarJSON(w, 404, map[string]interface{}{"exito": false, "error": "Recorrido no encontrado"})
		return
	}
	enviarJSON(w, 200, map[string]interface{}{
		"exito":     true,
		"recorrido": detalle,
	})
}

func apiReiniciarHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
		return
	}
	log.Println("Solicitud de reinicio recibida")
	go reiniciarSistema()
	enviarJSON(w, 200, map[string]interface{}{
		"exito":   true,
		"mensaje": "Sistema reiniciándose...",
	})
}

func apiApagarHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		enviarJSON(w, 405, map[string]interface{}{"error": "Método no permitido"})
		return
	}
	log.Println("Solicitud de apagado recibida")
	go apagarSistema()
	enviarJSON(w, 200, map[string]interface{}{
		"exito":   true,
		"mensaje": "Sistema apagándose...",
	})
}

// ==================== WEBSOCKET HANDLER ====================

func wsHandler(w http.ResponseWriter, r *http.Request) {
	conn, err := AceptarWebSocket(w, r)
	if err != nil {
		log.Printf("Error aceptando WebSocket: %v", err)
		return
	}

	gestorWS.Agregar(conn)
	defer func() {
		gestorWS.Eliminar(conn)
		conn.Close()
		log.Println("Cliente WebSocket desconectado")
	}()

	log.Printf("Cliente WebSocket conectado: %s", r.RemoteAddr)

	// Enviar estado inicial
	enviarEstadoInicial(conn)

	// Bucle de lectura
	for {
		datos, err := conn.ReadMessage()
		if err != nil {
			break
		}
		procesarMensajeWS(conn, datos)
	}
}

func enviarEstadoInicial(conn *WSConn) {
	config := obtenerConfiguracion()
	if config == nil {
		config = map[string]interface{}{}
	}
	destino := obtenerDestino()
	relesRaw := obtenerEstadoReles()
	relesJSON := relesAJSON(relesRaw)

	velocidadActualMu.RLock()
	vel := velocidadActual
	velocidadActualMu.RUnlock()

	// Obtener GPS con fallback a última posición guardada
	gps := obtenerPayloadGPS()
	if valido, _ := gps["valido"].(bool); !valido {
		// Intentar obtener última posición del historial GPS
		bd.mu.RLock()
		historial := bd.datos.HistorialGPS
		if len(historial) > 0 {
			ultima := historial[len(historial)-1]
			gps = map[string]interface{}{
				"latitud":  ultima.Latitud,
				"longitud": ultima.Longitud,
				"valido":   false,
			}
		}
		// Si no hay historial, buscar en ubicaciones guardadas
		if _, hasLat := gps["latitud"]; !hasLat {
			ubicaciones := bd.datos.UbicacionesGuardadas
			if len(ubicaciones) > 0 {
				ultima := ubicaciones[len(ubicaciones)-1]
				gps = map[string]interface{}{
					"latitud":  ultima.Latitud,
					"longitud": ultima.Longitud,
					"valido":   false,
				}
			}
		}
		bd.mu.RUnlock()
	}

	// Obtener datos rápidos primero (RAM, CPU, etc. son instantáneos)
	ram := obtenerRAM()
	temp := obtenerTemperatura()
	cpu := obtenerCPU()
	disco := obtenerAlmacenamiento()
	peso := obtenerPeso()
	wifi := obtenerWifi()

	// Enviar datos rápidos inmediatamente para que la UI responda al instante
	conn.SendJSON(map[string]interface{}{
		"tipo":          "conexion",
		"mensaje":       "WebSocket conectado",
		"reles":         relesJSON,
		"nombres_reles": config["reles"],
		"velocidad":     vel,
		"ram":           ram,
		"temperatura":   temp,
		"cpu":           cpu,
		"disco":         disco,
		"peso":          peso,
		"wifi":          wifi,
		"gps":           gps,
		"destino":       destino,
	})

	// Enviar datos lentos (Victron serial) por separado para no bloquear
	go func() {
		bat := obtenerBateria()
		conn.SendJSON(map[string]interface{}{"tipo": "bateria", "datos": bat})
		solar := obtenerSolar()
		conn.SendJSON(map[string]interface{}{"tipo": "solar", "datos": solar})
	}()
}

func procesarMensajeWS(conn *WSConn, datos map[string]interface{}) {
	tipo, _ := datos["tipo"].(string)

	switch tipo {
	case "rele":
		procesarRele(conn, datos)
	case "motor":
		procesarMotor(conn, datos)
	case "velocidad":
		procesarVelocidad(conn, datos)
	case "sistema":
		procesarSistema(conn, datos)
	case "gps_guardar":
		procesarGPSGuardar(conn)
	case "gps_destino":
		procesarGPSDestino(conn, datos)
	case "camara":
		procesarCamara(conn, datos)
	case "obtener_datos":
		procesarObtenerDatos(conn)
	case "guardar_config":
		procesarGuardarConfig(conn, datos)
	case "obtener_config":
		procesarObtenerConfig(conn)
	case "iniciar_recorrido":
		procesarIniciarRecorrido(conn, datos)
	case "finalizar_recorrido":
		procesarFinalizarRecorrido(conn)
	case "obtener_recorridos":
		procesarObtenerRecorridos(conn)
	default:
		conn.SendJSON(map[string]interface{}{
			"tipo":    "error",
			"mensaje": fmt.Sprintf("Comando \"%s\" no reconocido", tipo),
		})
	}
}

// ==================== PROCESADORES DE MENSAJES WS ====================

func procesarRele(conn *WSConn, datos map[string]interface{}) {
	numero := toInt(datos["numero"])
	estado := false
	if v, ok := datos["estado"].(bool); ok {
		estado = v
	}
	log.Printf("Comando de relé recibido: número=%d, estado=%v", numero, estado)

	exito, errMsg := controlarRele(numero, estado)
	log.Printf("Resultado de controlarRele: exito=%v, error=%s", exito, errMsg)

	estadoStr := "off"
	if estado {
		estadoStr = "on"
	}
	conn.SendJSON(map[string]interface{}{
		"tipo":   "respuesta_rele",
		"numero": numero,
		"estado": estadoStr,
		"exito":  exito,
		"error":  errMsg,
	})

	// Notificar a todos los clientes
	relesJSON := relesAJSON(obtenerEstadoReles())
	config := obtenerConfiguracion()
	var nombresReles interface{} = nil
	if config != nil {
		nombresReles = config["reles"]
	}
	gestorWS.BroadcastJSON(map[string]interface{}{
		"tipo":          "reles",
		"reles":         relesJSON,
		"nombres_reles": nombresReles,
	})
}

func procesarMotor(conn *WSConn, datos map[string]interface{}) {
	// Modo prueba brushless (con ciclo)
	if _, ok := datos["ciclo"]; ok {
		ciclo := toInt(datos["ciclo"])
		exito, errMsg := controlarMotor("adelante", ciclo)
		conn.SendJSON(map[string]interface{}{
			"tipo":   "motor_estado",
			"estado": fmt.Sprintf("Motores al %d%% (prueba brushless)", ciclo),
			"exito":  exito,
			"error":  errMsg,
		})
		return
	}

	// Modo normal
	direccion, _ := datos["direccion"].(string)
	if direccion == "" {
		direccion = "parar"
	}
	velocidadActualMu.RLock()
	vel := velocidadActual
	velocidadActualMu.RUnlock()

	exito, errMsg := controlarMotor(direccion, vel)
	conn.SendJSON(map[string]interface{}{
		"tipo":      "respuesta_motor",
		"direccion": direccion,
		"exito":     exito,
		"error":     errMsg,
	})
}

func procesarVelocidad(conn *WSConn, datos map[string]interface{}) {
	nivel := toInt(datos["nivel"])
	if nivel == 0 {
		nivel = 50
	}

	velocidadActualMu.Lock()
	velocidadActual = nivel
	velocidadActualMu.Unlock()

	guardarVelocidadActual(nivel)

	conn.SendJSON(map[string]interface{}{
		"tipo":      "respuesta_velocidad",
		"velocidad": nivel,
		"exito":     true,
	})

	// Broadcast a todos
	gestorWS.BroadcastJSON(map[string]interface{}{
		"tipo":      "velocidad",
		"velocidad": nivel,
	})
}

func procesarSistema(conn *WSConn, datos map[string]interface{}) {
	comando, _ := datos["comando"].(string)
	switch comando {
	case "apagar":
		exito, mensaje := apagarSistema()
		conn.SendJSON(map[string]interface{}{
			"tipo":    "sistema",
			"comando": "apagar",
			"mensaje": mensaje,
			"exito":   exito,
		})
	case "reiniciar":
		exito, mensaje := reiniciarSistema()
		conn.SendJSON(map[string]interface{}{
			"tipo":    "sistema",
			"comando": "reiniciar",
			"mensaje": mensaje,
			"exito":   exito,
		})
	}
}

func procesarGPSGuardar(conn *WSConn) {
	recorridoActivoMu.Lock()
	recID := recorridoActivo
	recorridoActivoMu.Unlock()

	exito, mensaje := guardarPosicionGPSActual(recID)
	conn.SendJSON(map[string]interface{}{
		"tipo":    "respuesta_gps",
		"accion":  "guardar",
		"exito":   exito,
		"mensaje": mensaje,
	})
}

func procesarGPSDestino(conn *WSConn, datos map[string]interface{}) {
	lat, latOk := datos["latitud"].(float64)
	lon, lonOk := datos["longitud"].(float64)
	nombre, _ := datos["nombre"].(string)

	if !latOk || !lonOk {
		conn.SendJSON(map[string]interface{}{
			"tipo":    "destino_actual",
			"exito":   false,
			"mensaje": "Coordenadas inválidas",
		})
		return
	}

	ok := guardarDestino(lat, lon, nombre)
	respuesta := map[string]interface{}{
		"tipo":     "destino_actual",
		"exito":    ok,
		"latitud":  lat,
		"longitud": lon,
		"nombre":   nombre,
	}
	conn.SendJSON(respuesta)

	if ok {
		gestorWS.BroadcastJSON(respuesta)
	}
}

func procesarCamara(conn *WSConn, datos map[string]interface{}) {
	indice := toInt(datos["indice"])
	if indice == 0 {
		indice = 1
	}
	accion, _ := datos["accion"].(string)
	if accion == "" {
		accion = "iniciar"
	}
	camID := "cam1"
	if indice == 2 {
		camID = "cam2"
	}

	config := obtenerConfiguracion()
	if config == nil {
		config = map[string]interface{}{}
	}

	if accion == "iniciar" {
		candidatos := construirRTSPCandidatos(config, indice)
		var rtspPrimera interface{}
		if len(candidatos) > 0 {
			rtspPrimera = candidatos[0]
		}

		// Obtener velocidad de red para modo automático
		velocidadDatos := obtenerVelocidadRed()
		var velKbps *float64
		if velocidadDatos != nil {
			if v, ok := velocidadDatos["velocidad"].(float64); ok {
				velKbps = &v
			}
		}

		exito, mensaje := iniciarHLS(camID, candidatos, config, velKbps)
		conn.SendJSON(map[string]interface{}{
			"tipo":    "camara",
			"indice":  indice,
			"accion":  "iniciar",
			"exito":   exito,
			"rtsp":    rtspPrimera,
			"mensaje": mensaje,
		})
	} else if accion == "detener" {
		detenerHLS(camID)
		conn.SendJSON(map[string]interface{}{
			"tipo":   "camara",
			"indice": indice,
			"accion": "detener",
			"exito":  true,
		})
	}
}

func procesarObtenerDatos(conn *WSConn) {
	relesJSON := relesAJSON(obtenerEstadoReles())
	config := obtenerConfiguracion()
	var nombresReles interface{} = nil
	if config != nil {
		nombresReles = config["reles"]
	}
	conn.SendJSON(map[string]interface{}{"tipo": "reles", "reles": relesJSON, "nombres_reles": nombresReles})
	conn.SendJSON(map[string]interface{}{"tipo": "ram", "datos": obtenerRAM()})
	conn.SendJSON(map[string]interface{}{"tipo": "temperatura", "datos": obtenerTemperatura()})
	conn.SendJSON(map[string]interface{}{"tipo": "cpu", "datos": obtenerCPU()})
	conn.SendJSON(map[string]interface{}{"tipo": "almacenamiento", "datos": obtenerAlmacenamiento()})
	conn.SendJSON(map[string]interface{}{"tipo": "disco_uso", "datos": obtenerUsoDisco()})
	conn.SendJSON(map[string]interface{}{"tipo": "peso", "datos": obtenerPeso()})
	conn.SendJSON(map[string]interface{}{"tipo": "gps", "datos": obtenerPayloadGPS()})

	velocidadActualMu.RLock()
	vel := velocidadActual
	velocidadActualMu.RUnlock()
	conn.SendJSON(map[string]interface{}{"tipo": "velocidad", "velocidad": vel})

	// Enviar datos de Victron (batería y solar) en paralelo para no bloquear
	go func() {
		conn.SendJSON(map[string]interface{}{"tipo": "bateria", "datos": obtenerBateria()})
		conn.SendJSON(map[string]interface{}{"tipo": "solar", "datos": obtenerSolar()})
	}()
}

func procesarGuardarConfig(conn *WSConn, datos map[string]interface{}) {
	config, _ := datos["config"].(map[string]interface{})
	if config == nil {
		conn.SendJSON(map[string]interface{}{
			"tipo":    "config_guardada",
			"exito":   false,
			"mensaje": "Configuración vacía",
		})
		return
	}
	if guardarConfiguracion(config) {
		conn.SendJSON(map[string]interface{}{
			"tipo":    "config_guardada",
			"exito":   true,
			"mensaje": "Configuración guardada en la base de datos",
		})
	} else {
		conn.SendJSON(map[string]interface{}{
			"tipo":    "config_guardada",
			"exito":   false,
			"mensaje": "Error al guardar configuración",
		})
	}
}

func procesarObtenerConfig(conn *WSConn) {
	config := obtenerConfiguracion()
	if config == nil {
		config = map[string]interface{}{}
	}
	conn.SendJSON(map[string]interface{}{
		"tipo":  "config_actual",
		"datos": config,
	})
}

func procesarIniciarRecorrido(conn *WSConn, datos map[string]interface{}) {
	nombre, _ := datos["nombre"].(string)
	if nombre == "" {
		nombre = "Recorrido sin título"
	}

	id := iniciarRecorrido(nombre)

	recorridoActivoMu.Lock()
	recorridoActivo = &id
	recorridoActivoMu.Unlock()

	conn.SendJSON(map[string]interface{}{
		"tipo":         "recorrido_iniciado",
		"recorrido_id": id,
		"nombre":       nombre,
	})
}

func procesarFinalizarRecorrido(conn *WSConn) {
	recorridoActivoMu.Lock()
	recID := recorridoActivo
	recorridoActivo = nil
	recorridoActivoMu.Unlock()

	if recID != nil {
		finalizarRecorrido(*recID)
		conn.SendJSON(map[string]interface{}{
			"tipo":  "recorrido_finalizado",
			"exito": true,
		})
	} else {
		conn.SendJSON(map[string]interface{}{
			"tipo":    "recorrido_finalizado",
			"exito":   false,
			"mensaje": "No hay recorrido activo",
		})
	}
}

func procesarObtenerRecorridos(conn *WSConn) {
	recorridos := obtenerTodosRecorridos(false)
	conn.SendJSON(map[string]interface{}{
		"tipo":       "lista_recorridos",
		"recorridos": recorridos,
	})
}

// ==================== TAREAS PERIÓDICAS ====================

// enviarDatosPeriodicos envía datos del sistema cada 5 segundos
func enviarDatosPeriodicos() {
	time.Sleep(3 * time.Second)

	for {
		time.Sleep(5 * time.Second)

		if gestorWS.CantidadClientes() == 0 {
			continue
		}

		ram := obtenerRAM()
		temp := obtenerTemperatura()
		cpu := obtenerCPU()
		almacenamiento := obtenerAlmacenamiento()
		discoUso := obtenerUsoDisco()
		bat := obtenerBateria()
		peso := obtenerPeso()
		solar := obtenerSolar()
		wifi := obtenerWifi()
		gps := obtenerPayloadGPS()
		voltaje := obtenerVoltajeRaspberry()

		datosBrujula := obtenerDatosBrujula()
		if datosBrujula == nil {
			datosBrujula = map[string]interface{}{"valido": false, "azimuth": nil}
		}

		mensajes := []map[string]interface{}{
			{"tipo": "ram", "datos": ram},
			{"tipo": "temperatura", "datos": temp},
			{"tipo": "cpu", "datos": cpu},
			{"tipo": "almacenamiento", "datos": almacenamiento},
			{"tipo": "disco_uso", "datos": discoUso},
			{"tipo": "bateria", "datos": bat},
			{"tipo": "peso", "datos": peso},
			{"tipo": "solar", "datos": solar},
			{"tipo": "wifi", "datos": wifi},
			{"tipo": "voltaje", "datos": voltaje},
			{"tipo": "gps", "datos": gps},
			{"tipo": "brujula", "datos": datosBrujula},
		}

		for _, msg := range mensajes {
			gestorWS.BroadcastJSON(msg)
		}
	}
}

// enviarVelocidadRedPeriodica envía velocidad de red cada 30 segundos
func enviarVelocidadRedPeriodica() {
	time.Sleep(5 * time.Second)

	for {
		time.Sleep(30 * time.Second)

		if gestorWS.CantidadClientes() == 0 {
			continue
		}

		velocidadRed := obtenerVelocidadRed()
		gestorWS.BroadcastJSON(map[string]interface{}{
			"tipo":  "velocidad_red",
			"datos": velocidadRed,
		})
	}
}

// guardarGPSAutomatico guarda la posición GPS según configuración
func guardarGPSAutomatico() {
	for {
		config := obtenerConfiguracion()
		if config == nil {
			time.Sleep(5 * time.Second)
			continue
		}

		guardarRecorrido, _ := config["guardar_recorrido"].(bool)
		if !guardarRecorrido {
			time.Sleep(5 * time.Second)
			continue
		}

		frecuencia := toInt(config["frecuencia_guardado"])
		if frecuencia < 5 {
			frecuencia = 30
		}

		recorridoActivoMu.Lock()
		if recorridoActivo == nil {
			id := iniciarRecorrido("")
			recorridoActivo = &id
			log.Printf("Recorrido GPS automático iniciado: ID %d", id)
		}
		recID := recorridoActivo
		recorridoActivoMu.Unlock()

		exito, mensaje := guardarPosicionGPSActual(recID)
		if exito {
			log.Printf("GPS guardado automáticamente: %s", mensaje)
		}

		time.Sleep(time.Duration(frecuencia) * time.Second)
	}
}

// ==================== ROUTER Y ARRANQUE ====================

func configurarRutas(mux *http.ServeMux) {
	// Páginas HTML
	mux.HandleFunc("/", indexHandler)
	mux.HandleFunc("/configuracion.html", configuracionHandler)
	mux.HandleFunc("/mapa_gps.html", mapaGPSHandler)
	mux.HandleFunc("/energia_solar.html", energiaSolarHandler)
	mux.HandleFunc("/prueba_algoritmo_motores_brushless.html", pruebaBrushlessHandler)
	mux.HandleFunc("/ayuda.html", ayudaHandler)

	// APIs REST
	mux.HandleFunc("/api/config", apiConfigHandler)
	mux.HandleFunc("/api/reles", apiRelesHandler)
	mux.HandleFunc("/api/gps/actual", apiGPSActualHandler)
	mux.HandleFunc("/api/test/wifi", apiTestWifiHandler)
	mux.HandleFunc("/api/indicadores", apiIndicadoresHandler)
	mux.HandleFunc("/api/temperatura", apiTemperaturaHandler)
	mux.HandleFunc("/api/onvif/discover", apiONVIFDiscoverHandler)
	mux.HandleFunc("/api/ubicaciones", apiUbicacionesHandler)
	mux.HandleFunc("/api/recorridos/", func(w http.ResponseWriter, r *http.Request) {
		// Si es exactamente /api/recorridos o /api/recorridos/
		path := strings.TrimSuffix(r.URL.Path, "/")
		if path == "/api/recorridos" {
			apiRecorridosHandler(w, r)
		} else {
			apiRecorridoDetalleHandler(w, r)
		}
	})
	mux.HandleFunc("/api/reiniciar", apiReiniciarHandler)
	mux.HandleFunc("/api/apagar", apiApagarHandler)

	// WebSocket
	mux.HandleFunc("/ws", wsHandler)

	// Archivos estáticos
	staticDir := filepath.Join(baseDir, "paginas")
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir(staticDir))))

	// HLS streaming
	hlsDir := filepath.Join(baseDir, "hls")
	os.MkdirAll(hlsDir, 0755)
	mux.Handle("/hls/", addCORSHeaders(http.StripPrefix("/hls/", http.FileServer(http.Dir(hlsDir)))))
}

// addCORSHeaders agrega headers CORS y no-cache para HLS
func addCORSHeaders(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Cache-Control", "no-cache, no-store, must-revalidate")
		w.Header().Set("Pragma", "no-cache")
		w.Header().Set("Expires", "0")
		if strings.HasSuffix(r.URL.Path, ".m3u8") {
			w.Header().Set("Content-Type", "application/vnd.apple.mpegurl")
		} else if strings.HasSuffix(r.URL.Path, ".ts") {
			w.Header().Set("Content-Type", "video/mp2t")
		}
		h.ServeHTTP(w, r)
	})
}

// iniciarServidor arranca el servidor HTTP
func iniciarServidor() {
	mux := http.NewServeMux()
	configurarRutas(mux)

	servidor := &http.Server{
		Addr:              fmt.Sprintf("%s:%d", HOST, PUERTO),
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       75 * time.Second,
	}

	log.Printf("Servidor escuchando en http://%s:%d", HOST, PUERTO)

	if err := servidor.ListenAndServe(); err != nil {
		log.Fatalf("Error iniciando servidor: %v", err)
	}
}
