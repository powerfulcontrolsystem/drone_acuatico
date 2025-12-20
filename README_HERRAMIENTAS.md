# 🚤 Drone Acuático - Herramientas de Optimización y GitHub

## 🎯 Acceso Rápido

### Menú Principal (Interfaz Interactiva)
```bash
bash ~/drone\ acuatico/menu_herramientas.sh
```

### Actualizar GitHub con Optimización Inteligente
```bash
bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh "Mensaje del commit"
```

---

## 📚 Documentación Completa

📖 **[INSTALACION_COMPLETA.md](INSTALACION_COMPLETA.md)** - Guía de instalación y primeros pasos

📖 **[optimizacion/GUIA_ACTUALIZACION_GITHUB.md](optimizacion/GUIA_ACTUALIZACION_GITHUB.md)** - Documentación detallada de uso

---

## 🛠️ Scripts Disponibles

### 1. 🎯 Actualización Inteligente de GitHub
**Archivo:** `utilidades/actualizar_github_inteligente.sh`
- Verifica RAM automáticamente
- Optimiza si es necesario (RAM > 70%)
- Sube cambios a GitHub
- Muestra resumen completo

### 2. 🧹 Optimización Agresiva de RAM
**Archivo:** `optimizacion/optimizar_ram_agresivo.sh`
- Limpia cachés del sistema
- Elimina temporales
- Limpia VSCode Server
- Comprime logs grandes
- Libera 50-150 MB típicamente

### 3. 🔧 Limpieza de VSCode Server
**Archivo:** `optimizacion/limpiar_vscode_server.sh`
- Configura Node.js (límite 200MB)
- Optimiza settings de VSCode
- Limpia logs y cachés
- Sin desconectar VSCode

### 4. 📊 Menú de Herramientas
**Archivo:** `menu_herramientas.sh`
- Interfaz interactiva
- Acceso a todas las herramientas
- Monitoreo de RAM en tiempo real
- Ver estado del sistema

---

## ⚡ Alias Recomendados

Agregar a `~/.bashrc`:
```bash
alias drone-menu='bash ~/drone\ acuatico/menu_herramientas.sh'
alias git-sync='bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh'
alias ram-clean='bash ~/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh'
alias vscode-clean='bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh'
```

Luego: `source ~/.bashrc`

---

## 📊 Mejoras de Rendimiento

### Antes de la optimización:
```
RAM: 776/906 MB (85%) 🔴 CRÍTICO
VSCode Server: ~900 MB
```

### Después de la optimización:
```
RAM: 620/906 MB (68%) 🟢 ÓPTIMO
VSCode Server: ~600 MB (con reconexión)
```

**Ahorro típico:** 150-300 MB

---

## 🎮 Uso Diario Recomendado

### Al iniciar:
```bash
ram-clean  # O usa el menú
```

### Al terminar:
```bash
git-sync "Trabajo completado"
```

### Si RAM está crítica:
```bash
vscode-clean
ram-clean
# Reconectar VSCode
```

---

## 📂 Estructura del Proyecto

```
drone acuatico/
├── menu_herramientas.sh                    🆕 Menú interactivo
├── INSTALACION_COMPLETA.md                 🆕 Guía de instalación
├── README_HERRAMIENTAS.md                  🆕 Este archivo
├── utilidades/
│   ├── actualizar_github_inteligente.sh    🆕 Script principal
│   └── subir_github.sh                         (Original)
├── optimizacion/
│   ├── optimizar_ram_agresivo.sh           🆕 Optimización RAM
│   ├── limpiar_vscode_server.sh            🆕 Limpieza VSCode
│   ├── GUIA_ACTUALIZACION_GITHUB.md        🆕 Documentación
│   ├── limpiar_memoria_optimizado.sh           (Original)
│   ├── monitor_ram.sh                          (Original)
│   └── optimizar_vscode.sh                     (Actualizado)
└── [resto de archivos del proyecto]
```

---

## 🔥 Características Principales

✅ **Detección inteligente de RAM** - Optimiza solo cuando es necesario  
✅ **Interfaz con colores** - Verde/Amarillo/Rojo según estado  
✅ **Limpieza automática** - VSCode, Python, logs, temporales  
✅ **Configuración persistente** - Settings optimizados guardados  
✅ **Sin interrupciones** - No desconecta VSCode durante limpieza  
✅ **Documentación completa** - Guías paso a paso  
✅ **Menú interactivo** - Fácil acceso a todas las herramientas  

---

## 📞 Comandos Útiles

```bash
# Ver RAM actual
free -h

# Ver procesos pesados
ps aux --sort=-%mem | head -n 10

# Ver uso de VSCode Server
ps aux | grep vscode-server | awk '{sum+=$6} END {print sum/1024 " MB"}'

# Verificar temperatura
vcgencmd measure_temp

# Ver espacio en disco
df -h

# Ver estado de Git
git status
```

---

## 🐛 Solución de Problemas

### VSCode consume mucha RAM
```bash
bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh
# Luego reconectar VSCode
```

### Permisos denegados
```bash
chmod +x ~/drone\ acuatico/menu_herramientas.sh
chmod +x ~/drone\ acuatico/utilidades/*.sh
chmod +x ~/drone\ acuatico/optimizacion/*.sh
```

### Git no sube cambios
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
git remote -v  # Verificar remote
```

---

## 📈 Monitoreo en Tiempo Real

Interfaz web con indicador de RAM:
```
http://192.168.1.8:8080
```

Actualización automática cada 10 segundos con código de colores.

---

## 🎯 Primeros Pasos

1. **Aplicar configuración:**
   ```bash
   source ~/.bashrc
   ```

2. **Limpiar VSCode:**
   ```bash
   bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh
   ```

3. **Reconectar VSCode** desde tu PC

4. **Probar el menú:**
   ```bash
   bash ~/drone\ acuatico/menu_herramientas.sh
   ```

5. **Configurar alias** (opcional):
   ```bash
   echo "alias drone-menu='bash ~/drone\ acuatico/menu_herramientas.sh'" >> ~/.bashrc
   source ~/.bashrc
   ```

---

**Creado:** 20 Diciembre 2025  
**Versión:** 1.0  
**Proyecto:** Drone Acuático - Sistema de Control  
**Estado:** ✅ Operativo

---

**¿Necesitas ayuda?** Lee la [documentación completa](optimizacion/GUIA_ACTUALIZACION_GITHUB.md)
