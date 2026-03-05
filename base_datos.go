package main

// ==================== BASE DE DATOS (JSON) ====================
// Persistencia basada en archivo JSON - Sin librerías externas
// Reemplaza SQLite manteniendo la misma funcionalidad

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// ==================== ESTRUCTURAS DE DATOS ====================

// Configuracion almacena toda la configuración del drone
type Configuracion struct {
	IPPublica          string            `json:"ip_publica"`
	SolicitarPassword  bool              `json:"solicitar_password"`
	Correo             string            `json:"correo"`
	PasswordHash       string            `json:"password_hash"`
	TamanoMapa         int               `json:"tamano_mapa"`
	TamanoLetraDatos   int               `json:"tamano_letra_datos"`
	GuardarRecorrido   bool              `json:"guardar_recorrido"`
	FrecuenciaGuardado int               `json:"frecuencia_guardado"`
	// Cámara 1
	RTSPCamara1URL       string `json:"rtsp_camara1_url"`
	RTSPCamara1Puerto    int    `json:"rtsp_camara1_puerto"`
	ONVIFCamara1Host     string `json:"onvif_camara1_host"`
	ONVIFCamara1Puerto   int    `json:"onvif_camara1_puerto"`
	ONVIFCamara1Usuario  string `json:"onvif_camara1_usuario"`
	ONVIFCamara1Contrasena string `json:"onvif_camara1_contrasena"`
	ONVIFCamara1Perfil   string `json:"onvif_camara1_perfil"`
	DesactivarCamara1    bool   `json:"desactivar_camara1"`
	IniciarAutoCamara1   bool   `json:"iniciar_auto_camara1"`
	Camara1ModoResolucion string `json:"camara1_modo_resolucion"`
	Camara1Resolucion    string `json:"camara1_resolucion"`
	// Cámara 2
	RTSPCamara2URL       string `json:"rtsp_camara2_url"`
	RTSPCamara2Puerto    int    `json:"rtsp_camara2_puerto"`
	ONVIFCamara2Host     string `json:"onvif_camara2_host"`
	ONVIFCamara2Puerto   int    `json:"onvif_camara2_puerto"`
	ONVIFCamara2Usuario  string `json:"onvif_camara2_usuario"`
	ONVIFCamara2Contrasena string `json:"onvif_camara2_contrasena"`
	ONVIFCamara2Perfil   string `json:"onvif_camara2_perfil"`
	DesactivarCamara2    bool   `json:"desactivar_camara2"`
	IniciarAutoCamara2   bool   `json:"iniciar_auto_camara2"`
	Camara2ModoResolucion string `json:"camara2_modo_resolucion"`
	Camara2Resolucion    string `json:"camara2_resolucion"`
	// Relés
	NombresReles map[int]string `json:"nombres_reles"`
	// Otros
	TemaOscuro       int    `json:"tema_oscuro"`
	VelocidadActual  int    `json:"velocidad_actual"`
	RouterIP         string `json:"router_ip"`
	PantallaCompleta bool   `json:"pantalla_completa"`
}

// RecorridoGPS representa un recorrido GPS completo
type RecorridoGPS struct {
	ID          int           `json:"id"`
	Nombre      string        `json:"nombre"`
	FechaInicio string        `json:"fecha_inicio"`
	FechaFin    *string       `json:"fecha_fin"`
	Activo      bool          `json:"activo"`
	Posiciones  []PosicionGPS `json:"posiciones"`
}

// PosicionGPS representa un punto GPS individual
type PosicionGPS struct {
	ID          int     `json:"id"`
	RecorridoID int     `json:"recorrido_id"`
	Latitud     float64 `json:"latitud"`
	Longitud    float64 `json:"longitud"`
	Altitud     float64 `json:"altitud"`
	Velocidad   float64 `json:"velocidad"`
	Satelites   int     `json:"satelites"`
	Timestamp   string  `json:"timestamp"`
}

// Ubicacion representa un punto de interés guardado
type Ubicacion struct {
	ID                 int     `json:"id"`
	Nombre             string  `json:"nombre"`
	Descripcion        string  `json:"descripcion"`
	Latitud            float64 `json:"latitud"`
	Longitud           float64 `json:"longitud"`
	Icono              string  `json:"icono"`
	Color              string  `json:"color"`
	Categoria          string  `json:"categoria"`
	FechaCreacion      string  `json:"fecha_creacion"`
	FechaActualizacion string  `json:"fecha_actualizacion"`
}

// Destino representa el destino de navegación actual
type Destino struct {
	Latitud            *float64 `json:"latitud"`
	Longitud           *float64 `json:"longitud"`
	Nombre             *string  `json:"nombre"`
	FechaActualizacion string   `json:"fecha_actualizacion"`
}

// HistorialGPSEntry representa una entrada del historial GPS
type HistorialGPSEntry struct {
	ID        int      `json:"id"`
	Latitud   float64  `json:"latitud"`
	Longitud  float64  `json:"longitud"`
	Altitud   *float64 `json:"altitud"`
	Velocidad *float64 `json:"velocidad"`
	Satelites *int     `json:"satelites"`
	Timestamp string   `json:"timestamp"`
}

// DatosDB es la estructura completa de la base de datos
type DatosDB struct {
	Configuracion        Configuracion       `json:"configuracion"`
	EstadoReles          map[int]bool        `json:"estado_reles"`
	RecorridosGPS        []RecorridoGPS      `json:"recorridos_gps"`
	UbicacionesGuardadas []Ubicacion         `json:"ubicaciones_guardadas"`
	HistorialGPS         []HistorialGPSEntry `json:"historial_gps"`
	Destino              *Destino            `json:"destino"`
	SiguienteIDRecorrido int                 `json:"siguiente_id_recorrido"`
	SiguienteIDPosicion  int                 `json:"siguiente_id_posicion"`
	SiguienteIDUbicacion int                 `json:"siguiente_id_ubicacion"`
	SiguienteIDHistorial int                 `json:"siguiente_id_historial"`
}

// BaseDatos maneja la persistencia en archivo JSON
type BaseDatos struct {
	mu   sync.RWMutex
	ruta string
	datos DatosDB
}

// Variable global de la base de datos
var bd *BaseDatos

// ==================== INICIALIZACIÓN ====================

func inicializarBD() {
	rutaDB := filepath.Join(filepath.Dir(os.Args[0]), "base_de_datos", "drone_acuatico.json")
	// Si el ejecutable está en otro directorio, usar ruta relativa
	if _, err := os.Stat(filepath.Dir(rutaDB)); os.IsNotExist(err) {
		rutaDB = filepath.Join("base_de_datos", "drone_acuatico.json")
		os.MkdirAll(filepath.Dir(rutaDB), 0755)
	}

	bd = &BaseDatos{
		ruta: rutaDB,
	}

	// Intentar cargar datos existentes
	if err := bd.cargar(); err != nil {
		log.Printf("Creando nueva base de datos: %v", err)
		bd.datos = crearDatosDefecto()
		bd.guardar()
	}

	// Verificar que los datos tienen valores por defecto correctos
	bd.verificarDatos()
	log.Println("Base de datos inicializada correctamente")
}

func crearDatosDefecto() DatosDB {
	nombresReles := make(map[int]string)
	for i := 1; i <= 9; i++ {
		nombresReles[i] = "Relé " + string(rune('0'+i))
	}

	estadoReles := make(map[int]bool)
	for i := 1; i <= 9; i++ {
		estadoReles[i] = false
	}

	return DatosDB{
		Configuracion: Configuracion{
			IPPublica:          "192.168.1.7",
			TamanoMapa:         400,
			TamanoLetraDatos:   12,
			GuardarRecorrido:   true,
			FrecuenciaGuardado: 30,
			IniciarAutoCamara1: true,
			IniciarAutoCamara2: true,
			ONVIFCamara1Puerto: 8899,
			ONVIFCamara2Puerto: 8899,
			RTSPCamara1Puerto:  554,
			RTSPCamara2Puerto:  554,
			Camara1ModoResolucion: "manual",
			Camara1Resolucion:  "480p",
			Camara2ModoResolucion: "manual",
			Camara2Resolucion:  "480p",
			NombresReles:       nombresReles,
			TemaOscuro:         1,
			VelocidadActual:    50,
		},
		EstadoReles:          estadoReles,
		RecorridosGPS:        []RecorridoGPS{},
		UbicacionesGuardadas: []Ubicacion{},
		HistorialGPS:         []HistorialGPSEntry{},
		SiguienteIDRecorrido: 1,
		SiguienteIDPosicion:  1,
		SiguienteIDUbicacion: 1,
		SiguienteIDHistorial: 1,
	}
}

func (b *BaseDatos) verificarDatos() {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.datos.Configuracion.NombresReles == nil {
		b.datos.Configuracion.NombresReles = make(map[int]string)
	}
	for i := 1; i <= 9; i++ {
		if _, ok := b.datos.Configuracion.NombresReles[i]; !ok {
			b.datos.Configuracion.NombresReles[i] = "Relé " + string(rune('0'+i))
		}
	}
	if b.datos.EstadoReles == nil {
		b.datos.EstadoReles = make(map[int]bool)
	}
	for i := 1; i <= 9; i++ {
		if _, ok := b.datos.EstadoReles[i]; !ok {
			b.datos.EstadoReles[i] = false
		}
	}
	if b.datos.Configuracion.TamanoMapa == 0 {
		b.datos.Configuracion.TamanoMapa = 400
	}
	if b.datos.Configuracion.TamanoLetraDatos == 0 {
		b.datos.Configuracion.TamanoLetraDatos = 12
	}
	if b.datos.Configuracion.FrecuenciaGuardado == 0 {
		b.datos.Configuracion.FrecuenciaGuardado = 30
	}
	if b.datos.Configuracion.VelocidadActual == 0 {
		b.datos.Configuracion.VelocidadActual = 50
	}
	if b.datos.Configuracion.ONVIFCamara1Puerto == 0 {
		b.datos.Configuracion.ONVIFCamara1Puerto = 8899
	}
	if b.datos.Configuracion.ONVIFCamara2Puerto == 0 {
		b.datos.Configuracion.ONVIFCamara2Puerto = 8899
	}
	if b.datos.Configuracion.RTSPCamara1Puerto == 0 {
		b.datos.Configuracion.RTSPCamara1Puerto = 554
	}
	if b.datos.Configuracion.RTSPCamara2Puerto == 0 {
		b.datos.Configuracion.RTSPCamara2Puerto = 554
	}
}

// ==================== PERSISTENCIA ====================

func (b *BaseDatos) cargar() error {
	datos, err := os.ReadFile(b.ruta)
	if err != nil {
		return err
	}
	return json.Unmarshal(datos, &b.datos)
}

func (b *BaseDatos) guardar() error {
	datos, err := json.MarshalIndent(b.datos, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(b.ruta, datos, 0644)
}

func (b *BaseDatos) guardarAsync() {
	go func() {
		b.mu.RLock()
		defer b.mu.RUnlock()
		if err := b.guardar(); err != nil {
			log.Printf("Error guardando BD: %v", err)
		}
	}()
}

// ==================== CONFIGURACIÓN ====================

func obtenerConfiguracion() map[string]interface{} {
	bd.mu.RLock()
	defer bd.mu.RUnlock()
	c := bd.datos.Configuracion

	config := map[string]interface{}{
		"ip_publica":          c.IPPublica,
		"solicitar_password":  c.SolicitarPassword,
		"correo":              c.Correo,
		"tamano_mapa":         c.TamanoMapa,
		"tamano_letra_datos":  c.TamanoLetraDatos,
		"guardar_recorrido":   c.GuardarRecorrido,
		"frecuencia_guardado": c.FrecuenciaGuardado,
		"velocidad_actual":    c.VelocidadActual,
		"router_ip":           c.RouterIP,
		"pantalla_completa":   c.PantallaCompleta,
		// Cámara 1
		"rtsp_camara1_url":        c.RTSPCamara1URL,
		"rtsp_camara1_puerto":     c.RTSPCamara1Puerto,
		"onvif_camara1_host":      c.ONVIFCamara1Host,
		"onvif_camara1_puerto":    c.ONVIFCamara1Puerto,
		"onvif_camara1_usuario":   c.ONVIFCamara1Usuario,
		"onvif_camara1_contrasena": c.ONVIFCamara1Contrasena,
		"onvif_camara1_perfil":    c.ONVIFCamara1Perfil,
		"desactivar_camara1":      c.DesactivarCamara1,
		"iniciar_auto_camara1":    c.IniciarAutoCamara1,
		"camara1_modo_resolucion": c.Camara1ModoResolucion,
		"camara1_resolucion":      c.Camara1Resolucion,
		// Cámara 2
		"rtsp_camara2_url":        c.RTSPCamara2URL,
		"rtsp_camara2_puerto":     c.RTSPCamara2Puerto,
		"onvif_camara2_host":      c.ONVIFCamara2Host,
		"onvif_camara2_puerto":    c.ONVIFCamara2Puerto,
		"onvif_camara2_usuario":   c.ONVIFCamara2Usuario,
		"onvif_camara2_contrasena": c.ONVIFCamara2Contrasena,
		"onvif_camara2_perfil":    c.ONVIFCamara2Perfil,
		"desactivar_camara2":      c.DesactivarCamara2,
		"iniciar_auto_camara2":    c.IniciarAutoCamara2,
		"camara2_modo_resolucion": c.Camara2ModoResolucion,
		"camara2_resolucion":      c.Camara2Resolucion,
		// Relés
		"reles": c.NombresReles,
	}
	return config
}

func guardarConfiguracion(config map[string]interface{}) bool {
	bd.mu.Lock()
	defer bd.mu.Unlock()

	c := &bd.datos.Configuracion

	if v, ok := config["ip_publica"].(string); ok {
		c.IPPublica = v
	}
	if v, ok := config["solicitar_password"].(bool); ok {
		c.SolicitarPassword = v
	}
	if v, ok := config["correo"].(string); ok {
		c.Correo = v
	}
	if v, ok := config["tamano_mapa"]; ok {
		c.TamanoMapa = toInt(v)
	}
	if v, ok := config["tamano_letra_datos"]; ok {
		c.TamanoLetraDatos = toInt(v)
	}
	if v, ok := config["guardar_recorrido"].(bool); ok {
		c.GuardarRecorrido = v
	}
	if v, ok := config["frecuencia_guardado"]; ok {
		c.FrecuenciaGuardado = toInt(v)
	}
	if v, ok := config["velocidad_actual"]; ok {
		c.VelocidadActual = toInt(v)
	}
	if v, ok := config["router_ip"].(string); ok {
		c.RouterIP = v
	}
	if v, ok := config["pantalla_completa"].(bool); ok {
		c.PantallaCompleta = v
	}
	// Cámara 1
	if v, ok := config["rtsp_camara1_url"].(string); ok {
		c.RTSPCamara1URL = v
	}
	if v, ok := config["rtsp_camara1_puerto"]; ok {
		c.RTSPCamara1Puerto = toInt(v)
	}
	if v, ok := config["onvif_camara1_host"].(string); ok {
		c.ONVIFCamara1Host = v
	}
	if v, ok := config["onvif_camara1_puerto"]; ok {
		c.ONVIFCamara1Puerto = toInt(v)
	}
	if v, ok := config["onvif_camara1_usuario"].(string); ok {
		c.ONVIFCamara1Usuario = v
	}
	if v, ok := config["onvif_camara1_contrasena"].(string); ok {
		c.ONVIFCamara1Contrasena = v
	}
	if v, ok := config["onvif_camara1_perfil"].(string); ok {
		c.ONVIFCamara1Perfil = v
	}
	if v, ok := config["desactivar_camara1"].(bool); ok {
		c.DesactivarCamara1 = v
	}
	if v, ok := config["iniciar_auto_camara1"].(bool); ok {
		c.IniciarAutoCamara1 = v
	}
	if v, ok := config["camara1_modo_resolucion"].(string); ok {
		c.Camara1ModoResolucion = v
	}
	if v, ok := config["camara1_resolucion"].(string); ok {
		c.Camara1Resolucion = v
	}
	// Cámara 2
	if v, ok := config["rtsp_camara2_url"].(string); ok {
		c.RTSPCamara2URL = v
	}
	if v, ok := config["rtsp_camara2_puerto"]; ok {
		c.RTSPCamara2Puerto = toInt(v)
	}
	if v, ok := config["onvif_camara2_host"].(string); ok {
		c.ONVIFCamara2Host = v
	}
	if v, ok := config["onvif_camara2_puerto"]; ok {
		c.ONVIFCamara2Puerto = toInt(v)
	}
	if v, ok := config["onvif_camara2_usuario"].(string); ok {
		c.ONVIFCamara2Usuario = v
	}
	if v, ok := config["onvif_camara2_contrasena"].(string); ok {
		c.ONVIFCamara2Contrasena = v
	}
	if v, ok := config["onvif_camara2_perfil"].(string); ok {
		c.ONVIFCamara2Perfil = v
	}
	if v, ok := config["desactivar_camara2"].(bool); ok {
		c.DesactivarCamara2 = v
	}
	if v, ok := config["iniciar_auto_camara2"].(bool); ok {
		c.IniciarAutoCamara2 = v
	}
	if v, ok := config["camara2_modo_resolucion"].(string); ok {
		c.Camara2ModoResolucion = v
	}
	if v, ok := config["camara2_resolucion"].(string); ok {
		c.Camara2Resolucion = v
	}
	// Relés
	if reles, ok := config["reles"].(map[string]interface{}); ok {
		if c.NombresReles == nil {
			c.NombresReles = make(map[int]string)
		}
		for k, v := range reles {
			num := toInt(k)
			if num >= 1 && num <= 9 {
				if s, ok := v.(string); ok {
					c.NombresReles[num] = s
				}
			}
		}
	}

	if err := bd.guardar(); err != nil {
		log.Printf("Error guardando configuración: %v", err)
		return false
	}
	log.Println("Configuración guardada correctamente")
	return true
}

// ==================== ESTADO DE RELÉS ====================

func obtenerEstadoReles() map[int]bool {
	bd.mu.RLock()
	defer bd.mu.RUnlock()
	copia := make(map[int]bool)
	for k, v := range bd.datos.EstadoReles {
		copia[k] = v
	}
	return copia
}

func guardarEstadoRele(numero int, estado bool) bool {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	if bd.datos.EstadoReles == nil {
		bd.datos.EstadoReles = make(map[int]bool)
	}
	bd.datos.EstadoReles[numero] = estado
	bd.guardarAsync()
	return true
}

func restaurarEstadosReles() map[int]bool {
	estados := obtenerEstadoReles()
	for i := 1; i <= 9; i++ {
		if _, ok := estados[i]; !ok {
			estados[i] = false
		}
	}
	return estados
}

// ==================== VELOCIDAD ====================

func guardarVelocidadActual(nivel int) {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	bd.datos.Configuracion.VelocidadActual = nivel
	bd.guardarAsync()
}

func obtenerVelocidadActual() int {
	bd.mu.RLock()
	defer bd.mu.RUnlock()
	v := bd.datos.Configuracion.VelocidadActual
	if v == 0 {
		return 50
	}
	return v
}

// ==================== DESTINO ====================

func guardarDestino(latitud, longitud float64, nombre string) bool {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	ahora := time.Now().Format("2006-01-02 15:04:05")
	var nombrePtr *string
	if nombre != "" {
		nombrePtr = &nombre
	}
	bd.datos.Destino = &Destino{
		Latitud:            &latitud,
		Longitud:           &longitud,
		Nombre:             nombrePtr,
		FechaActualizacion: ahora,
	}
	bd.guardarAsync()
	return true
}

func obtenerDestino() map[string]interface{} {
	bd.mu.RLock()
	defer bd.mu.RUnlock()
	if bd.datos.Destino == nil || bd.datos.Destino.Latitud == nil {
		return nil
	}
	d := bd.datos.Destino
	result := map[string]interface{}{
		"latitud":              *d.Latitud,
		"longitud":             *d.Longitud,
		"fecha_actualizacion": d.FechaActualizacion,
	}
	if d.Nombre != nil {
		result["nombre"] = *d.Nombre
	}
	return result
}

// ==================== RECORRIDOS GPS ====================

func iniciarRecorrido(nombre string) int {
	bd.mu.Lock()
	defer bd.mu.Unlock()

	id := bd.datos.SiguienteIDRecorrido
	bd.datos.SiguienteIDRecorrido++

	recorrido := RecorridoGPS{
		ID:          id,
		Nombre:      nombre,
		FechaInicio: time.Now().Format("2006-01-02 15:04:05"),
		Activo:      true,
		Posiciones:  []PosicionGPS{},
	}
	bd.datos.RecorridosGPS = append(bd.datos.RecorridosGPS, recorrido)
	bd.guardarAsync()
	log.Printf("Recorrido GPS iniciado: ID=%d, Nombre=%s", id, nombre)
	return id
}

func finalizarRecorrido(recorridoID int) bool {
	bd.mu.Lock()
	defer bd.mu.Unlock()
	for i := range bd.datos.RecorridosGPS {
		if bd.datos.RecorridosGPS[i].ID == recorridoID {
			ahora := time.Now().Format("2006-01-02 15:04:05")
			bd.datos.RecorridosGPS[i].Activo = false
			bd.datos.RecorridosGPS[i].FechaFin = &ahora
			bd.guardarAsync()
			log.Printf("Recorrido GPS finalizado: ID=%d", recorridoID)
			return true
		}
	}
	return false
}

func guardarPosicionGPSEnBD(recorridoID int, latitud, longitud, altitud, velocidad float64, satelites int) int {
	bd.mu.Lock()
	defer bd.mu.Unlock()

	id := bd.datos.SiguienteIDPosicion
	bd.datos.SiguienteIDPosicion++

	posicion := PosicionGPS{
		ID:          id,
		RecorridoID: recorridoID,
		Latitud:     latitud,
		Longitud:    longitud,
		Altitud:     altitud,
		Velocidad:   velocidad,
		Satelites:   satelites,
		Timestamp:   time.Now().Format("2006-01-02 15:04:05"),
	}

	for i := range bd.datos.RecorridosGPS {
		if bd.datos.RecorridosGPS[i].ID == recorridoID {
			bd.datos.RecorridosGPS[i].Posiciones = append(bd.datos.RecorridosGPS[i].Posiciones, posicion)
			bd.guardarAsync()
			return id
		}
	}
	return 0
}

func obtenerRecorrido(recorridoID int) map[string]interface{} {
	bd.mu.RLock()
	defer bd.mu.RUnlock()

	for _, r := range bd.datos.RecorridosGPS {
		if r.ID == recorridoID {
			posiciones := make([]map[string]interface{}, 0, len(r.Posiciones))
			for _, p := range r.Posiciones {
				posiciones = append(posiciones, map[string]interface{}{
					"latitud":   p.Latitud,
					"longitud":  p.Longitud,
					"altitud":   p.Altitud,
					"velocidad": p.Velocidad,
					"satelites": p.Satelites,
					"timestamp": p.Timestamp,
				})
			}
			result := map[string]interface{}{
				"id":           r.ID,
				"nombre":       r.Nombre,
				"fecha_inicio": r.FechaInicio,
				"fecha_fin":    r.FechaFin,
				"activo":       r.Activo,
				"posiciones":   posiciones,
			}
			return result
		}
	}
	return nil
}

func obtenerTodosRecorridos(activosSolo bool) []map[string]interface{} {
	bd.mu.RLock()
	defer bd.mu.RUnlock()

	resultado := []map[string]interface{}{}
	for _, r := range bd.datos.RecorridosGPS {
		if activosSolo && !r.Activo {
			continue
		}
		resultado = append(resultado, map[string]interface{}{
			"id":           r.ID,
			"nombre":       r.Nombre,
			"fecha_inicio": r.FechaInicio,
			"fecha_fin":    r.FechaFin,
			"activo":       r.Activo,
		})
	}
	return resultado
}

// ==================== UBICACIONES ====================

func guardarUbicacion(nombre, descripcion string, latitud, longitud float64) int {
	bd.mu.Lock()
	defer bd.mu.Unlock()

	id := bd.datos.SiguienteIDUbicacion
	bd.datos.SiguienteIDUbicacion++

	ahora := time.Now().Format("2006-01-02 15:04:05")
	ubicacion := Ubicacion{
		ID:                 id,
		Nombre:             nombre,
		Descripcion:        descripcion,
		Latitud:            latitud,
		Longitud:           longitud,
		Icono:              "marker",
		Color:              "#3b82f6",
		Categoria:          "general",
		FechaCreacion:      ahora,
		FechaActualizacion: ahora,
	}
	bd.datos.UbicacionesGuardadas = append(bd.datos.UbicacionesGuardadas, ubicacion)
	bd.guardarAsync()
	log.Printf("Ubicación guardada: ID=%d, Nombre=%s", id, nombre)
	return id
}

func obtenerUbicaciones(categoria, busqueda string) []map[string]interface{} {
	bd.mu.RLock()
	defer bd.mu.RUnlock()

	resultado := []map[string]interface{}{}
	for _, u := range bd.datos.UbicacionesGuardadas {
		if categoria != "" && u.Categoria != categoria {
			continue
		}
		if busqueda != "" {
			// Búsqueda simple en nombre y descripción
			if !contieneIgnorarMayusculas(u.Nombre, busqueda) && !contieneIgnorarMayusculas(u.Descripcion, busqueda) {
				continue
			}
		}
		resultado = append(resultado, map[string]interface{}{
			"id":                  u.ID,
			"nombre":              u.Nombre,
			"descripcion":         u.Descripcion,
			"latitud":             u.Latitud,
			"longitud":            u.Longitud,
			"icono":               u.Icono,
			"color":               u.Color,
			"categoria":           u.Categoria,
			"fecha_creacion":      u.FechaCreacion,
			"fecha_actualizacion": u.FechaActualizacion,
		})
	}
	return resultado
}

// ==================== UTILIDADES ====================

func toInt(v interface{}) int {
	switch val := v.(type) {
	case int:
		return val
	case float64:
		return int(val)
	case string:
		n := 0
		for _, c := range val {
			if c >= '0' && c <= '9' {
				n = n*10 + int(c-'0')
			}
		}
		return n
	case bool:
		if val {
			return 1
		}
		return 0
	default:
		return 0
	}
}

func contieneIgnorarMayusculas(s, substr string) bool {
	if len(substr) == 0 {
		return true
	}
	if len(s) < len(substr) {
		return false
	}
	sLower := toLower(s)
	subLower := toLower(substr)
	for i := 0; i <= len(sLower)-len(subLower); i++ {
		if sLower[i:i+len(subLower)] == subLower {
			return true
		}
	}
	return false
}

func toLower(s string) string {
	b := make([]byte, len(s))
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c >= 'A' && c <= 'Z' {
			c += 'a' - 'A'
		}
		b[i] = c
	}
	return string(b)
}
