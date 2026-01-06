# Proyecto: Sistema de Control Remoto Digital para Dron Acuático

## Descripción General
Este proyecto implementa un sistema completo de control remoto digital para un dron acuático, permitiendo la operación y monitoreo en tiempo real de sus funciones principales (motores, relés, cámaras, sensores y GPS) desde una interfaz web moderna y responsiva. El sistema está diseñado para ser ejecutado en una Raspberry Pi, integrando hardware de control, transmisión de video, y visualización de datos en vivo.

## Componentes del Proyecto

### 1. Servidor Backend (`servidor.py`)
- **Función:** Gestiona la comunicación entre la interfaz web y el hardware del dron (GPIO, sensores, cámaras, etc.).
- **Tecnología:** Python, aiohttp, WebSocket.
- **Responsabilidades:**
  - Control de relés y motores vía WebSocket.
  - Lectura y envío de datos de sensores (RAM, temperatura, batería, red, peso, solar, GPS).
  - Transmisión de estados y eventos a todos los clientes conectados.
  - Gestión de configuración persistente (nombres de relés, tamaño de letra, etc.).

### 2. Interfaz Web (Carpeta `paginas/`)
- **Archivos principales:**
  - `control remoto digital.html`: Página principal de control y monitoreo.
  - `configuracion.html`: Página para ajustar parámetros y nombres de relés.
  - `tema_universal.css`: Hoja de estilos global, controla el formato de todos los cuadros y botones.
  - `leaflet_loader.js`: Carga y muestra el mapa GPS usando Leaflet.
  - `config-ui.js`: Aplica el tamaño de letra configurado a los indicadores.
- **Características:**
  - Botones para controlar 9 relés, con nombres configurables y colores según estado.
  - Panel de dirección (cruz) y botones de velocidad.
  - Indicadores en tiempo real de RAM, temperatura, batería, red, peso, solar, velocidad y GPS.
  - Visualización de cámaras en vivo (HLS).
  - Mapa GPS con marcador de posición.
  - Menú flotante para configuración, reinicio y apagado.
  - Diseño responsivo y compacto.

### 3. Transmisión de Video (Carpeta `hls/`)
- **Función:** Almacena los segmentos de video HLS generados por las cámaras.
- **Archivos:**
  - `cam1/`, `cam2/`: Carpetas con archivos `.ts` y listas `.m3u8` para cada cámara.

### 4. Base de Datos y Configuración (Carpeta `base_de_datos/`)
- **Archivo principal:** `base_datos.py`
- **Función:** Gestiona la configuración persistente (nombres de relés, parámetros de usuario, etc.).

### 5. Scripts Útiles
- `iniciar_servidor.sh`: Inicia el servidor backend.
- `conectar_raspberry.sh`: Script de conexión/configuración para la Raspberry Pi.
- `subir_cambios_a_repositorio.sh`: Automatiza el push de cambios al repositorio.

### 6. Documentación y Recursos
- Carpeta `documentacion/`: Contiene descripciones, estilos y este manual.

## Estructura de Carpetas
- `paginas/`: Archivos HTML, CSS y JS de la interfaz web.
- `hls/`: Segmentos de video HLS para streaming.
- `base_de_datos/`: Código y archivos de configuración persistente.
- `documentacion/`: Documentos explicativos y manuales.
- `venv_pi/`: Entorno virtual de Python para dependencias.

## Requisitos y Puesta en Marcha
1. **Hardware:** Raspberry Pi con acceso a GPIO, cámaras y red.
2. **Software:** Python 3.13+, dependencias en `venv_pi/`.
3. **Iniciar servidor:**
   - Ejecutar `bash iniciar_servidor.sh` en la Raspberry Pi.
4. **Acceso web:**
   - Abrir un navegador y acceder a la IP de la Raspberry Pi en el puerto configurado (por defecto 8080).
5. **Configuración:**
   - Usar el menú de la interfaz para ajustar nombres de relés, tamaño de letra, etc.

## Notas Finales
- Todo el formato visual se controla desde `tema_universal.css`.
- El sistema es modular y puede ampliarse fácilmente.
- Para cualquier cambio, actualizar el repositorio usando el script correspondiente.

---
Este documento permite a cualquier persona replicar y entender el funcionamiento del sistema de control remoto digital para dron acuático tal como está implementado actualmente.