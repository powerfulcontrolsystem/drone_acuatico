# Guía para el Agente IA 

## 🎯 Regla Principal

**REGLAS CONCISAS:** Cada regla en este documento debe ser clara, directa y sin ejemplos extensos. Solo agregar lo que el usuario solicite explícitamente.


### Idioma
Siempre responder en **español**.

### Contexto del Proyecto
Consultar [Descripcion del proyecto.md](Descripcion%20del%20proyecto.md) para entender el contexto antes de proponer mejoras.

### Actualización del Repositorio
No actualizar el repositorio sin autorización explícita del usuario. El usuario debe probar el proyecto primero y luego autorizarlo.
Cuando autorizado, ejecutar:
```bash
ssh admin@192.168.1.14 "cd /home/admin/drone_acuatico && ./subir_cambios_a_repositorio.sh 'Mensaje descriptivo del cambio'"
```

## 📝 Nota técnica sobre actualización del repositorio

Para actualizar el repositorio de este proyecto, utilicé el script automatizado `subir_cambios_a_repositorio.sh` ubicado en `/home/admin/drone_acuatico`. El procedimiento consiste en conectarse por SSH a la Raspberry Pi (IP 192.168.1.21) con el usuario `admin` y ejecutar el script pasando como argumento el mensaje de commit. El comando utilizado fue:

ssh admin@192.168.1.21 "cd /home/admin/drone_acuatico && ./subir_cambios_a_repositorio.sh 'Mensaje descriptivo del cambio'"

Este script realiza internamente el `git add`, `git commit` y `git push`, asegurando que todos los cambios locales se suban correctamente al repositorio remoto. Es importante tener la contraseña de admin a mano para completar la autenticación SSH.

##🔧 Configuración de Acceso Remoto
### Información de Conexión
- **Host:** 192.168.1.21
- **Usuario:** admin
- **Contraseña:** admin
- **Directorio del proyecto:** /home/admin/drone_acuatico

### ⚠️ IMPORTANTE: Ejecución de Comandos
Cuando se está usando la extensión **SSH-FS** en VSCode, los archivos se pueden editar directamente usando rutas como:
```
ssh://raspberry-admin/home/admin/drone_acuatico/archivo.py
```
