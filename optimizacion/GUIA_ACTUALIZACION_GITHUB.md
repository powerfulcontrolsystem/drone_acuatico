# 🚀 Sistema de Actualización Inteligente con Optimización de RAM

## 📋 Descripción

Sistema integral para gestionar la RAM de la Raspberry Pi y sincronizar cambios con GitHub. Optimiza automáticamente el consumo de VSCode Server y otros procesos antes de realizar operaciones Git.

## 🆕 Scripts Nuevos Creados

### 1. 🎯 **actualizar_github_inteligente.sh** (PRINCIPAL)
Script maestro que combina verificación de RAM, optimización y subida a GitHub.

**Ubicación:** `/utilidades/actualizar_github_inteligente.sh`

**Uso:**
```bash
# Sin mensaje personalizado (usa fecha/hora automática)
bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh

# Con mensaje personalizado
bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh "Mensaje del commit"
```

**¿Qué hace?**
1. ✅ Verifica el estado de la RAM
2. 🔧 Optimiza automáticamente si RAM > 85%
3. 💬 Pregunta si optimizar si RAM > 70%
4. 📝 Detecta cambios en Git
5. ☁️ Sube cambios a GitHub
6. 📊 Muestra resumen final

**Códigos de color:**
- 🟢 Verde: RAM < 70% (Óptimo)
- 🟡 Amarillo: RAM 70-85% (Aceptable)
- 🔴 Rojo: RAM > 85% (Crítico)

---

### 2. 🧹 **optimizar_ram_agresivo.sh**
Limpieza agresiva de RAM para Raspberry Pi.

**Ubicación:** `/optimizacion/optimizar_ram_agresivo.sh`

**Uso:**
```bash
bash ~/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh
```

**¿Qué limpia?**
1. Cachés del sistema
2. Archivos temporales (/tmp)
3. Logs de VSCode Server
4. Caché de Python (__pycache__, .pyc)
5. Logs del proyecto (comprime > 3MB)
6. Swap (si está muy lleno)
7. Detecta procesos pesados

**Resultados típicos:** Libera entre 50-150 MB

---

### 3. 🔧 **limpiar_vscode_server.sh**
Optimización específica para VSCode Server sin desconectar.

**Ubicación:** `/optimizacion/limpiar_vscode_server.sh`

**Uso:**
```bash
bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh
```

**Optimizaciones aplicadas:**
1. Configura Node.js con límite de 200MB
2. Crea settings.json optimizado
3. Limpia logs de VSCode
4. Elimina caché de extensiones
5. Limpia workspace storage antiguo
6. Libera caché del sistema

**Importante:** Los cambios de Node.js requieren reconexión de VSCode.

---

## 📊 Comparación de Scripts

| Script | Uso de RAM | Velocidad | Agresividad | Requiere Reconexión |
|--------|------------|-----------|-------------|---------------------|
| `limpiar_vscode_server.sh` | VSCode específico | Rápido | Media | Recomendado |
| `optimizar_ram_agresivo.sh` | Sistema completo | Medio | Alta | No |
| `actualizar_github_inteligente.sh` | Ambos si necesario | Automático | Inteligente | No |

---

## 🎮 Uso Recomendado

### Flujo de trabajo diario:
```bash
# Opción 1: Script inteligente todo-en-uno (RECOMENDADO)
bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh "Tu mensaje"

# Opción 2: Solo optimizar RAM
bash ~/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh

# Opción 3: Solo optimizar VSCode
bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh
```

### Alias recomendados (agregar a ~/.bashrc):
```bash
# Agregar al final de ~/.bashrc
alias git-sync='bash ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh'
alias ram-clean='bash ~/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh'
alias vscode-clean='bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh'

# Luego ejecutar: source ~/.bashrc
```

Después puedes usar simplemente:
```bash
git-sync "Mi commit"
ram-clean
vscode-clean
```

---

## 🔥 Optimizaciones Aplicadas

### VSCode Server Settings
Los scripts configuran automáticamente:
- ❌ Desactivar telemetría
- ❌ Desactivar auto-actualización
- ❌ Reducir watchers de archivos
- ❌ Desactivar Git autorefresh
- ❌ Desactivar sugerencias automáticas
- ✅ Auto-guardado optimizado

### Node.js Limits
```bash
NODE_OPTIONS='--max-old-space-size=200'
```
Limita el heap de Node.js a 200MB (VSCode usa Node.js)

---

## ⚡ Tips Adicionales

### Para máxima optimización:
1. **Cierra tabs no usados** en VSCode
2. **Desinstala extensiones pesadas** que no uses
3. **Reconecta VSCode** después de ejecutar `limpiar_vscode_server.sh`
4. **Ejecuta los scripts periódicamente** (cada 1-2 horas si trabajas mucho)
5. **Usa el monitor de RAM** en la interfaz web: http://192.168.1.8:8080

### Automatización (Opcional):
Crear un cron job para limpiar automáticamente:
```bash
# Editar crontab
crontab -e

# Agregar línea (limpia cada 2 horas):
0 */2 * * * bash /home/admin/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh >> /home/admin/limpieza.log 2>&1
```

---

## 📈 Resultados Esperados

### Antes de la optimización:
```
RAM: 776/906 MB (85%) 🔴 CRÍTICO
VSCode Server: ~900 MB
```

### Después de la optimización:
```
RAM: 620/906 MB (68%) 🟢 ÓPTIMO  
VSCode Server: ~600 MB (reconectando)
```

**Ahorro típico:** 150-300 MB dependiendo del uso

---

## 🐛 Solución de Problemas

### VSCode sigue usando mucha RAM
1. Ejecuta: `bash ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh`
2. Cierra VSCode completamente
3. Reconecta VSCode
4. Verifica: `ps aux | grep vscode | awk '{sum+=$6} END {print sum/1024 " MB"}'`

### El script no tiene permisos
```bash
chmod +x ~/drone\ acuatico/utilidades/actualizar_github_inteligente.sh
chmod +x ~/drone\ acuatico/optimizacion/optimizar_ram_agresivo.sh
chmod +x ~/drone\ acuatico/optimizacion/limpiar_vscode_server.sh
```

### Error al subir a GitHub
Verifica configuración de Git:
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"
git remote -v  # Verificar remote
```

---

## 📝 Archivos del Sistema

### Scripts creados:
```
drone acuatico/
├── utilidades/
│   └── actualizar_github_inteligente.sh    🆕 (Script principal)
└── optimizacion/
    ├── optimizar_ram_agresivo.sh           🆕 (Limpieza agresiva)
    ├── limpiar_vscode_server.sh            🆕 (Optimización VSCode)
    └── GUIA_ACTUALIZACION_GITHUB.md        🆕 (Esta guía)
```

### Archivos modificados automáticamente:
- `~/.bashrc` → Añade límites de Node.js
- `~/.vscode-server/data/Machine/settings.json` → Configuración optimizada

---

## 🎯 Casos de Uso

### 1. Antes de empezar a trabajar:
```bash
ram-clean  # Limpiar RAM
```

### 2. Al terminar una sesión de trabajo:
```bash
git-sync "Trabajo del día completado"
```

### 3. RAM al 90% y necesitas trabajar:
```bash
vscode-clean     # Primero VSCode
ram-clean        # Luego sistema completo
# Reconectar VSCode si es necesario
```

### 4. Subida rápida sin optimización:
```bash
cd ~/drone\ acuatico
bash utilidades/subir_github.sh "Cambio rápido"
```

---

## ✅ Checklist de Primera Vez

- [ ] Ejecutar `limpiar_vscode_server.sh`
- [ ] Ejecutar `source ~/.bashrc` para aplicar límites de Node
- [ ] Reconectar VSCode
- [ ] Agregar alias a ~/.bashrc
- [ ] Probar `actualizar_github_inteligente.sh`
- [ ] Verificar RAM en interfaz web: http://192.168.1.8:8080

---

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs: `cat ~/limpieza.log`
2. Verifica RAM: `free -h`
3. Verifica procesos VSCode: `ps aux | grep vscode-server`

---

**Creado:** 20 Diciembre 2025  
**Versión:** 1.0  
**Proyecto:** Drone Acuático - Sistema de Control
