package main

// ==================== STREAMING CÁMARAS RTSP → HLS ====================
// Gestiona procesos ffmpeg para convertir RTSP a HLS
// Sin librerías externas

import (
	"fmt"
	"log"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ==================== CONFIGURACIÓN ====================

var hlsOutputDir string

var hlsPlaylistName = map[string]string{
	"cam1": "cam1.m3u8",
	"cam2": "cam2.m3u8",
}

// Resoluciones disponibles
var resolucionConfig = map[string]struct {
	Scale   string
	Bitrate string
	Maxrate string
}{
	"360p":  {"640:360", "1000k", "1500k"},
	"480p":  {"854:480", "1500k", "2000k"},
	"720p":  {"1280:720", "2500k", "3500k"},
	"1080p": {"1920:1080", "4000k", "5000k"},
}

// Procesos ffmpeg activos
var (
	procesosHLS   = map[string]*exec.Cmd{}
	procesosHLSMu sync.Mutex
)

func init() {
	dir, _ := os.Executable()
	hlsOutputDir = filepath.Join(filepath.Dir(dir), "hls")
	if _, err := os.Stat(hlsOutputDir); os.IsNotExist(err) {
		hlsOutputDir = "hls"
	}
}

// ==================== FUNCIONES PRINCIPALES ====================

// hlsAsegurarCarpetas crea las carpetas necesarias para HLS
func hlsAsegurarCarpetas() bool {
	if err := os.MkdirAll(hlsOutputDir, 0755); err != nil {
		log.Printf("Error creando carpeta HLS: %v", err)
		return false
	}
	for _, cam := range []string{"cam1", "cam2"} {
		if err := os.MkdirAll(filepath.Join(hlsOutputDir, cam), 0755); err != nil {
			log.Printf("Error creando carpeta HLS %s: %v", cam, err)
			return false
		}
	}
	log.Println("Carpetas HLS listas")
	return true
}

// obtenerResolucion obtiene la resolución configurada para una cámara
func obtenerResolucion(config map[string]interface{}, camID string, velocidadKbps *float64) string {
	indice := 1
	if camID == "cam2" {
		indice = 2
	}

	modoKey := fmt.Sprintf("camara%d_modo_resolucion", indice)
	resKey := fmt.Sprintf("camara%d_resolucion", indice)

	modo, _ := config[modoKey].(string)

	if modo == "automatico" {
		if velocidadKbps == nil {
			res, _ := config[resKey].(string)
			if res == "" {
				res = "480p"
			}
			return res
		}

		velocidadMbps := *velocidadKbps / 1000.0
		switch {
		case velocidadMbps < 2.0:
			return "360p"
		case velocidadMbps < 5.0:
			return "480p"
		case velocidadMbps < 10.0:
			return "720p"
		default:
			return "1080p"
		}
	}

	// Modo manual
	res, _ := config[resKey].(string)
	if res == "" {
		res = "480p"
	}
	if _, ok := resolucionConfig[res]; !ok {
		res = "480p"
	}
	return res
}

// construirRTSPCandidatos construye una lista de URLs RTSP candidatas
func construirRTSPCandidatos(config map[string]interface{}, indice int) []string {
	if config == nil {
		return nil
	}

	var candidatos []string

	// URL RTSP completa (prioritaria)
	urlKey := fmt.Sprintf("rtsp_camara%d_url", indice)
	if urlCompleta, ok := config[urlKey].(string); ok && strings.HasPrefix(strings.TrimSpace(urlCompleta), "rtsp://") {
		candidatos = append(candidatos, strings.TrimSpace(urlCompleta))
	}

	// Construir desde parámetros ONVIF
	hostKey := fmt.Sprintf("onvif_camara%d_host", indice)
	host, _ := config[hostKey].(string)
	host = strings.TrimSpace(host)

	if host != "" {
		puertoONVIFKey := fmt.Sprintf("onvif_camara%d_puerto", indice)
		puertoRTSPKey := fmt.Sprintf("rtsp_camara%d_puerto", indice)
		usuarioKey := fmt.Sprintf("onvif_camara%d_usuario", indice)
		contrasenaKey := fmt.Sprintf("onvif_camara%d_contrasena", indice)
		perfilKey := fmt.Sprintf("onvif_camara%d_perfil", indice)

		puertoONVIF := toInt(config[puertoONVIFKey])
		if puertoONVIF == 0 {
			puertoONVIF = 8899
		}
		puertoRTSP := toInt(config[puertoRTSPKey])
		if puertoRTSP == 0 {
			puertoRTSP = 554
		}

		usuario, _ := config[usuarioKey].(string)
		contrasena, _ := config[contrasenaKey].(string)
		perfil, _ := config[perfilKey].(string)
		if perfil == "" {
			perfil = "Streaming/Channels/101"
		}
		perfil = strings.Trim(perfil, "/")

		auth := ""
		if usuario != "" {
			auth = usuario
			if contrasena != "" {
				auth += ":" + contrasena
			}
			auth += "@"
		}

		// Generar candidatos con diferentes puertos
		puertos := []int{puertoRTSP}
		if puertoONVIF != puertoRTSP {
			puertos = append(puertos, puertoONVIF)
		}
		if puertoRTSP != 554 && puertoONVIF != 554 {
			puertos = append(puertos, 554)
		}

		for _, p := range puertos {
			url := fmt.Sprintf("rtsp://%s%s:%d/%s", auth, host, p, perfil)
			// Evitar duplicados
			encontrado := false
			for _, c := range candidatos {
				if c == url {
					encontrado = true
					break
				}
			}
			if !encontrado {
				candidatos = append(candidatos, url)
			}
		}
	}

	return candidatos
}

// iniciarHLS inicia streaming RTSP→HLS para una cámara
func iniciarHLS(indiceOID interface{}, urlRTSP interface{}, config map[string]interface{}, velocidadKbps *float64) (bool, string) {
	camID := resolverCamID(indiceOID)
	if camID == "" {
		return false, "Identificador de cámara inválido"
	}

	// Recopilar candidatos
	var candidatos []string
	switch v := urlRTSP.(type) {
	case []string:
		candidatos = v
	case string:
		if v != "" {
			candidatos = []string{v}
		}
	}

	if len(candidatos) == 0 {
		return false, "URL RTSP vacía"
	}

	ultimoError := "URL RTSP no válida"
	for idx, url := range candidatos {
		ok, msg := iniciarHLSSingle(camID, url, config, velocidadKbps)
		if ok {
			if idx > 0 {
				msg = fmt.Sprintf("%s (usando candidato %d)", msg, idx+1)
			}
			return true, msg
		}
		ultimoError = msg
	}
	return false, ultimoError
}

// iniciarHLSSingle lanza ffmpeg para una URL específica
func iniciarHLSSingle(camID, urlRTSP string, config map[string]interface{}, velocidadKbps *float64) (bool, string) {
	// Verificar ffmpeg
	ffmpegPath, err := exec.LookPath("ffmpeg")
	if err != nil {
		return false, "ffmpeg no encontrado en el sistema"
	}

	hlsAsegurarCarpetas()

	// Detener si ya hay un proceso activo
	detenerHLS(camID)

	carpeta := filepath.Join(hlsOutputDir, camID)
	limpiarSalidaHLS(camID)

	playlistName, ok := hlsPlaylistName[camID]
	if !ok {
		playlistName = camID + ".m3u8"
	}
	playlistPath := filepath.Join(carpeta, playlistName)
	segmentPattern := filepath.Join(carpeta, camID+"_%03d.ts")

	// Obtener resolución
	resolucion := obtenerResolucion(config, camID, velocidadKbps)
	resConfig, ok := resolucionConfig[resolucion]
	if !ok {
		resConfig = resolucionConfig["480p"]
	}

	log.Printf("HLS %s: usando %s (%s, %s)", camID, resolucion, resConfig.Scale, resConfig.Bitrate)

	cmd := exec.Command(ffmpegPath,
		"-nostdin",
		"-loglevel", "error",
		"-rtsp_transport", "tcp",
		"-i", urlRTSP,
		"-an",
		"-vf", "scale="+resConfig.Scale,
		"-c:v", "libx264",
		"-preset", "ultrafast",
		"-b:v", resConfig.Bitrate,
		"-maxrate", resConfig.Maxrate,
		"-bufsize", "1000k",
		"-f", "hls",
		"-hls_time", "0.5",
		"-hls_list_size", "3",
		"-hls_flags", "delete_segments+program_date_time",
		"-hls_segment_filename", segmentPattern,
		playlistPath,
	)

	if err := cmd.Start(); err != nil {
		return false, "Error iniciando ffmpeg: " + err.Error()
	}

	procesosHLSMu.Lock()
	procesosHLS[camID] = cmd
	procesosHLSMu.Unlock()

	log.Printf("Iniciando HLS %s desde %s (PID %d)", camID, urlRTSP, cmd.Process.Pid)

	// Esperar hasta 3 segundos para verificar que el proceso no terminó inmediatamente
	for i := 0; i < 6; i++ {
		time.Sleep(500 * time.Millisecond)

		// Verificar si el proceso terminó
		if cmd.ProcessState != nil {
			procesosHLSMu.Lock()
			delete(procesosHLS, camID)
			procesosHLSMu.Unlock()
			return false, "No se pudo abrir el RTSP (proceso terminó)"
		}

		// Verificar si el archivo playlist existe
		if info, err := os.Stat(playlistPath); err == nil && info.Size() > 0 {
			return true, "HLS iniciado"
		}
	}

	return true, "HLS iniciado (validación pendiente)"
}

// detenerHLS detiene el ffmpeg de una cámara
func detenerHLS(indiceOID interface{}) bool {
	camID := resolverCamID(indiceOID)
	if camID == "" {
		return false
	}

	procesosHLSMu.Lock()
	cmd, ok := procesosHLS[camID]
	if !ok {
		procesosHLSMu.Unlock()
		return true
	}
	delete(procesosHLS, camID)
	procesosHLSMu.Unlock()

	if cmd.Process != nil {
		cmd.Process.Signal(os.Interrupt)
		done := make(chan error, 1)
		go func() {
			done <- cmd.Wait()
		}()

		select {
		case <-done:
		case <-time.After(5 * time.Second):
			cmd.Process.Kill()
		}
	}

	log.Printf("HLS detenido para %s", camID)
	return true
}

// hlsDetenerTodos detiene todos los procesos ffmpeg
func hlsDetenerTodos() {
	procesosHLSMu.Lock()
	camIDs := make([]string, 0, len(procesosHLS))
	for id := range procesosHLS {
		camIDs = append(camIDs, id)
	}
	procesosHLSMu.Unlock()

	for _, id := range camIDs {
		detenerHLS(id)
	}
}

// ==================== UTILIDADES ====================

func resolverCamID(indiceOID interface{}) string {
	switch v := indiceOID.(type) {
	case string:
		if v == "cam1" || v == "cam2" {
			return v
		}
	case int:
		if v == 1 {
			return "cam1"
		}
		if v == 2 {
			return "cam2"
		}
	case float64:
		if v == 1 {
			return "cam1"
		}
		if v == 2 {
			return "cam2"
		}
	}
	return ""
}

func limpiarSalidaHLS(camID string) {
	carpeta := filepath.Join(hlsOutputDir, camID)
	entries, err := os.ReadDir(carpeta)
	if err != nil {
		return
	}
	for _, entry := range entries {
		nombre := entry.Name()
		if strings.HasSuffix(nombre, ".ts") || strings.HasSuffix(nombre, ".m3u8") {
			os.Remove(filepath.Join(carpeta, nombre))
		}
	}
}

// ==================== DESCUBRIMIENTO ONVIF ====================

// descubrirONVIF realiza una búsqueda WS-Discovery de cámaras ONVIF en la red
func descubrirONVIF(timeoutSec int) []map[string]interface{} {
	if timeoutSec <= 0 {
		timeoutSec = 3
	}

	messageID := fmt.Sprintf("uuid:%d", time.Now().UnixNano())
	probe := fmt.Sprintf(`<?xml version='1.0' encoding='UTF-8'?>
<e:Envelope xmlns:e='http://www.w3.org/2003/05/soap-envelope'
            xmlns:w='http://schemas.xmlsoap.org/ws/2004/08/addressing'
            xmlns:d='http://schemas.xmlsoap.org/ws/2005/04/discovery'
            xmlns:dn='http://www.onvif.org/ver10/network/wsdl'>
  <e:Header>
    <w:MessageID>%s</w:MessageID>
    <w:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe><d:Types>dn:NetworkVideoTransmitter</d:Types></d:Probe>
  </e:Body>
</e:Envelope>`, messageID)

	addr, err := net.ResolveUDPAddr("udp4", "239.255.255.250:3702")
	if err != nil {
		log.Printf("Error resolviendo multicast: %v", err)
		return []map[string]interface{}{}
	}

	conn, err := net.ListenUDP("udp4", nil)
	if err != nil {
		log.Printf("Error abriendo socket UDP: %v", err)
		return []map[string]interface{}{}
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(time.Duration(timeoutSec) * time.Second))

	_, err = conn.WriteToUDP([]byte(probe), addr)
	if err != nil {
		log.Printf("Error enviando probe ONVIF: %v", err)
		return []map[string]interface{}{}
	}

	dispositivos := map[string]map[string]interface{}{}
	buf := make([]byte, 8192)

	for {
		n, remoteAddr, err := conn.ReadFromUDP(buf)
		if err != nil {
			break
		}

		host := remoteAddr.IP.String()
		txt := string(buf[:n])

		// Buscar XAddrs
		xaddrs := ""
		if idx := strings.Index(txt, "XAddrs"); idx >= 0 {
			// Encontrar inicio del contenido (después del >)
			start := strings.Index(txt[idx:], ">")
			if start >= 0 {
				end := strings.Index(txt[idx+start:], "<")
				if end >= 0 {
					xaddrs = strings.TrimSpace(txt[idx+start+1 : idx+start+end])
				}
			}
		}

		// Inferir puerto desde XAddrs
		puerto := 8899
		if colonIdx := strings.Index(xaddrs, "://"); colonIdx >= 0 {
			resto := xaddrs[colonIdx+3:]
			if portIdx := strings.Index(resto, ":"); portIdx >= 0 {
				portEnd := strings.IndexAny(resto[portIdx+1:], "/ ")
				if portEnd < 0 {
					portEnd = len(resto[portIdx+1:])
				}
				if p, err := strconv.Atoi(resto[portIdx+1 : portIdx+1+portEnd]); err == nil {
					puerto = p
				}
			}
		}

		dispositivos[host] = map[string]interface{}{
			"host":   host,
			"puerto": puerto,
			"xaddrs": xaddrs,
		}
	}

	resultado := make([]map[string]interface{}, 0, len(dispositivos))
	for _, d := range dispositivos {
		resultado = append(resultado, d)
	}
	return resultado
}
