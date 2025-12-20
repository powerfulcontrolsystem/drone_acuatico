# 🚤 Drone Acuático - Sistema de Control

Sistema de control remoto para drone acuático basado en Raspberry Pi 3.

## 📁 Estructura del Proyecto

```
drone acuatico/
├── drone_server.py          # Servidor principal con WebSocket
├── control remoto digital/  # Interfaz web
│   └── index.html          # Página de control
├── test_gpio.py            # Test de relés
├── limpiar_memoria.sh      # Script de limpieza de RAM
└── venv_pi/                # Entorno virtual Python
```

## 🚀 Iniciar el Servidor

### 1. Activar entorno virtual
```bash
cd ~/drone\ acuatico
source venv_pi/bin/activate
```

### 2. Ejecutar el servidor
```bash
python drone_server.py
```

El servidor iniciará en: **http://192.168.1.8:8080**

## 🌐 Acceder al Control Remoto

Desde cualquier dispositivo en la misma red WiFi:
- Abrir navegador web
- Ir a: **http://192.168.1.8:8080**

## 🎮 Funcionalidades

### ⚡ Control de Relés
- 9 relés configurables (GPIO 4, 7, 8, 9, 11, 21, 22, 23, 24)
- Click en botón para activar/desactivar
- Indicador visual verde cuando está activo

### 🎮 Control de Movimiento
- **Adelante**: Todos los motores hacia adelante
- **Atrás**: Todos los motores en reversa
- **Derecha**: Giro a la derecha
- **Izquierda**: Giro a la izquierda
- **Parar**: Detener todos los motores

### 📍 Sistema GPS
- Visualización de posición actual en tiempo real
- Botón para guardar ubicaciones
- Lista de ubicaciones guardadas
- Mapa con recorrido (actualización cada 5 segundos)

### ⚖️ Sensor de Peso
- Monitoreo continuo del sensor HX711
- Actualización cada 2 segundos
- Alerta visual y sonora cuando supera 5.0 kg
- Valor umbral configurable

### 📹 Cámaras
- Dos vistas de cámara en vivo
- Placeholder para configurar URLs de cámaras IP

## 🔧 Configuración

### Cambiar Puerto del Servidor
Editar `drone_server.py`:
```python
PORT = 8080  # Cambiar a puerto deseado
```

### Cambiar Umbral de Peso
Editar `drone_server.py`:
```python
PESO_UMBRAL = 5.0  # Cambiar umbral en kg
```

### Configurar URLs de Cámaras
Editar `control remoto digital/index.html`:
```html
<!-- Descomentar y agregar URL -->
<img src="http://IP_CAMARA_1:PUERTO/stream" alt="Cámara 1">
<img src="http://IP_CAMARA_2:PUERTO/stream" alt="Cámara 2">
```

## 🔌 Conexiones GPIO

### Relés (16 canales)
| GPIO | Relé |
|------|------|
| 4    | 1    |
| 7    | 2    |
| 8    | 3    |
| 9    | 4    |
| 11   | 5    |
| 21   | 6    |
| 22   | 7    |
| 23   | 8    |
| 24   | 9    |

### Motores (PWM)
| GPIO | Motor |
|------|-------|
| 18   | 1     |
| 13   | 2     |
| 19   | 3     |
| 12   | 4     |

### Sensores I2C
| GPIO | Función |
|------|---------|
| 2    | SDA     |
| 3    | SCL     |

### Sensor de Peso HX711
| GPIO | Función |
|------|---------|
| 5    | DT      |
| 6    | SCK     |

## 🧹 Mantenimiento

### Limpiar RAM
```bash
bash ~/drone\ acuatico/limpiar_memoria.sh
```

### Verificar Estado de RAM
```bash
free -h
```

### Ver Logs del Servidor
Los logs se muestran en la terminal donde se ejecuta el servidor.

## 🛑 Detener el Servidor

Presionar `Ctrl + C` en la terminal donde se ejecuta el servidor.

## 📝 Notas

- El servidor usa WebSocket para comunicación en tiempo real
- Todas las conexiones GPIO usan lógica inversa (LOW = ON, HIGH = OFF)
- Los motores requieren calibración de ESC antes del primer uso
- El GPS requiere señal satelital (puede tardar 1-2 minutos en exterior)

## 🔐 Información de Acceso

- **Usuario Raspberry**: admin
- **Contraseña**: admin
- **IP Raspberry**: 192.168.1.8
- **Puerto Web**: 8080

## ⚠️ Recomendaciones

1. Ejecutar `limpiar_memoria.sh` antes de iniciar el servidor
2. Monitorear RAM con `htop` durante operación
3. Evitar mantener VSCode abierto mientras el servidor está activo
4. Usar conexión SSH ligera en lugar de VSCode Remote cuando sea posible

---

**Desarrollado para Raspberry Pi 3 | Python 3.13 | 2025**
