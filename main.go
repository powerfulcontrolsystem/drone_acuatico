package main

// ==================== PUNTO DE ENTRADA ====================
// Función principal del Drone Acuático
// Inicializa todos los subsistemas y arranca el servidor

import (
	"log"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"
)

func main() {
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)

	log.Println("============================================================")
	log.Println("  SERVIDOR DRONE ACUÁTICO - CONTROL REMOTO WEB (Go)")
	log.Println("============================================================")
	log.Printf("Iniciando en http://0.0.0.0:%d", PUERTO)
	log.Println("============================================================")

	// Determinar directorio base
	exe, err := os.Executable()
	if err != nil {
		baseDir, _ = os.Getwd()
	} else {
		baseDir = filepath.Dir(exe)
	}
	// Si hay un directorio "paginas" en el CWD, usar CWD
	if _, err := os.Stat(filepath.Join(baseDir, "paginas")); os.IsNotExist(err) {
		cwd, _ := os.Getwd()
		if _, err := os.Stat(filepath.Join(cwd, "paginas")); err == nil {
			baseDir = cwd
		}
	}
	log.Printf("Directorio base: %s", baseDir)

	// Terminar procesos previos
	matarProcesosServidorPrevios()

	// Inicializar base de datos
	inicializarBD()
	log.Println("Base de datos inicializada")

	// Cargar velocidad almacenada
	velocidadActualMu.Lock()
	velocidadActual = obtenerVelocidadActual()
	velocidadActualMu.Unlock()

	// Inicializar GPIO
	inicializarGPIO()

	// Restaurar estados de relés desde la base de datos
	log.Println("Restaurando estados de relés desde base de datos...")
	estadosGuardados := restaurarEstadosReles()
	for numero, estado := range estadosGuardados {
		if estado {
			exito, errMsg := controlarRele(numero, true)
			if exito {
				log.Printf("Relé %d activado (restaurado desde BD)", numero)
			} else {
				log.Printf("No se pudo activar relé %d: %s", numero, errMsg)
			}
			time.Sleep(1 * time.Second)
		}
	}

	// Iniciar GPS
	iniciarGPS()

	// Inicializar brújula
	inicializarBrujula()

	// Inicializar gestor de WebSockets
	gestorWS = NuevoGestorClientes()

	// Preparar carpetas HLS
	hlsAsegurarCarpetas()

	// Auto-iniciar cámaras si están configuradas
	config := obtenerConfiguracion()
	if config != nil {
		// Cámara 1
		desactivar1, _ := config["desactivar_camara1"].(bool)
		autoStart1 := true
		if v, ok := config["iniciar_auto_camara1"].(bool); ok {
			autoStart1 = v
		}
		if !desactivar1 && autoStart1 {
			candidatos := construirRTSPCandidatos(config, 1)
			if len(candidatos) > 0 {
				exito, msg := iniciarHLS("cam1", candidatos, config, nil)
				if exito {
					log.Printf("Cámara 1 iniciada: %s", candidatos[0])
				} else {
					log.Printf("No se pudo iniciar cámara 1: %s", msg)
				}
			}
		}

		// Cámara 2
		desactivar2, _ := config["desactivar_camara2"].(bool)
		autoStart2 := true
		if v, ok := config["iniciar_auto_camara2"].(bool); ok {
			autoStart2 = v
		}
		if !desactivar2 && autoStart2 {
			candidatos := construirRTSPCandidatos(config, 2)
			if len(candidatos) > 0 {
				exito, msg := iniciarHLS("cam2", candidatos, config, nil)
				if exito {
					log.Printf("Cámara 2 iniciada: %s", candidatos[0])
				} else {
					log.Printf("No se pudo iniciar cámara 2: %s", msg)
				}
			}
		}
	}

	// Tareas periódicas en goroutines
	go enviarDatosPeriodicos()
	go enviarVelocidadRedPeriodica()
	go guardarGPSAutomatico()
	go gestorWS.IniciarHeartbeat()

	// Manejo de señales para cierre limpio
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		sig := <-sigChan
		log.Printf("Señal recibida: %v. Cerrando...", sig)
		cerrarTodo()
		os.Exit(0)
	}()

	// Iniciar servidor (bloquea)
	iniciarServidor()
}

// cerrarTodo libera todos los recursos al cerrar
func cerrarTodo() {
	log.Println("Cerrando servidor...")

	// Finalizar recorrido GPS activo
	recorridoActivoMu.Lock()
	if recorridoActivo != nil {
		finalizarRecorrido(*recorridoActivo)
		log.Printf("Recorrido GPS finalizado: ID=%d", *recorridoActivo)
	}
	recorridoActivoMu.Unlock()

	// Detener GPS
	detenerGPS()

	// Cerrar brújula
	cerrarBrujula()

	// Liberar GPIO
	liberarGPIO()

	// Detener cámaras HLS
	hlsDetenerTodos()

	// Cerrar todos los WebSockets
	gestorWS.CerrarTodos()

	log.Println("Servidor detenido correctamente")
}
