
# DRONE ACUÁTICO 

## ubicación del proyecto en pc Windows
D:\Drone acuatico

## ubicación del proyecto en la raspberry
home/admin/drone acuatico

## DESCRIPCIÓN
El dron acuático está diseñado para ofrecer una experiencia de pesca inteligente y navegación autónoma. Se alimenta de energía solar, cuenta con una batería de alta capacidad y dispone de cuatro motores brushless para garantizar una movilidad precisa.

Integra sensores como GPS para registrar rutas y ubicaciones de pesca, y cámaras con inteligencia artificial para detección de colisiones y optimización de la navegación.

## características
- Permite programar rutas basada en el gps.
- permite ver en tiempo real las dos cámaras wifi del drone
- 

El control del dron se realiza mediante una **Raspberry Pi**, que ejecuta un **servidor web en Python**, permitiendo el control remoto desde dispositivos móviles y la integración de herramientas adicionales gracias a la conectividad a internet.

Este sistema combina energía renovable, sensores avanzados y control remoto para navegacion y exploración acuática.

---

## TECNOLOGÍA A USAR
- Raspberry Pi 3
- Módulo de relé de 16 canales 5V
- Panel solar bifacial 100W
- Controladora de carga Victron MPPT 75/15
- Batería LiFePO4 12V 30Ah
- Brújula electrónica hiBCTR GY-271 QMC5883L
- Router WiFi Firstnum CPE C1 con SIM 4G LTE
- 2 cámaras WiFi 2K 360° Cinnado
- Antena GPS USB VFAN Gmouse
- Sensor LiDAR TF-Luna (0.7 ft – 26.2 ft)
- 4 motores de propulsión submarinos brushless (hélices de 4 palas)
- Sensor de peso HX711 10kg
- ESC bidireccional ApisQueen 2–6S 45A
- Motor paso a paso 5V con controladora ULN2003
- Módulo cámara mini para Raspberry Pi (OV5647 5MP 1080p)

---

## CONEXIONES EN RASPBERRY PI

### MÓDULO DE RELÉ DE 16 CANALES
| GPIO Raspberry | Relé |
|---------------|------|
| Pin 4 | 5V |
| Pin 6 | GND |
| GPIO 4 | Canal 1 |
| GPIO 7 | Canal 2 |
| GPIO 8 | Canal 3 |
| GPIO 9 | Canal 4 |
| GPIO 11 | Canal 5 |
| GPIO 21 | Canal 6 |
| GPIO 22 | Canal 7 |
| GPIO 23 | Canal 8 |
| GPIO 24 | Canal 9 |

---

### ESC – MOTORES PROPULSORES
| GPIO Raspberry | Motor |
|---------------|-------|
| GPIO 18 (PWM) | Motor 1 |
| GPIO 13 (PWM) | Motor 2 |
| GPIO 19 (PWM) | Motor 3 |
| GPIO 12 (PWM) | Motor 4 |

---

### SENSOR TF-LUNA Y BRÚJULA (I2C)
Ambos sensores comparten el bus I2C.

| GPIO | TF-Luna | Brújula |
|-----|---------|---------|
| GPIO 2 (SDA) | Cable X | Cable X |
| GPIO 3 (SCL) | Cable Y | Cable Y |

---

### SENSOR DE PESO HX711
| GPIO | Conexión |
|-----|----------|
| GPIO 5 | Cable verde |
| GPIO 6 | — |

---

## SOFTWARE
Todo el software se desarrolla principalmente en **Python**.  
La Raspberry Pi funciona como **servidor central** del sistema.

El control se realiza desde:
- Teléfono móvil
- Tableta
- PC

Usando únicamente un navegador web.

---

## PÁGINA WEB – "control remoto digital"

La página web simula un control remoto físico del dron, usando solo html y java, usando lo mas simple posible.

## nombre de la pagina
"control remoto digital"

### FUNCIONES
1. Activar relé 1  
2. Activar relé 2  
3. Activar relé 3  
4. Activar relé 4  
5. Activar relé 5  
6. Activar relé 6  
7. Activar relé 7  
8. Activar relé 8  
9. Activar relé 9  
10. Adelante  
11. Atrás  
12. Derecha  
13. Izquierda  
14. Guardar ubicación GPS  

La página muestra **dos vistas de cámara en vivo** mediante las URLs de las cámaras IP.

---

## UBICACIÓN GPS
La web muestra:
- Mapa
- Posición actual
- Recorrido del dron en tiempo real

---

## ALERTAS
El valor del **sensor de peso** se visualiza en la web.  
Al superar un umbral configurado:
- Alerta visual
- Alerta sonora

---

## SEGURIDAD Y CONEXIÓN SSH
## Carpeta del proyecto Raspberry: home/admin/drone
El usuario de raspberry es: admin
Clave de usuario admin: admin
La dirección ip de la raspberry es : 192.168.1.8

## protocolo de comunicacion 
se usara web socket para comunicar la web con el servidor.py

## Ubicacion de pa pagina "control remoto digital" dentro del proyecto.
Todo lo relacionado con la pagina, es decir el archivo html, java etc, debe estar en una carpeta llamada "control remoto digital", es decir en: drone acuatico/control remoto digital/
- todas las imagenes en la carpeta imagenes
- En python todo bien organizado

## Nota
- Todo el codigo debe tener su respectivo comentario explicando en cada linea.
- El codigo python debe estar separado organizado por funciones.
-

## conexion a raspberry
usuario: admin
clave: admin
ip: 192.168.1.8