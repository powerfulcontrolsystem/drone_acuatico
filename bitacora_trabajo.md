# Bitácora de trabajo - Drone Acuático

## Resumen de avances y pendientes

### Última actualización: 2026-03-07

---

## Avances recientes
- Automatización del historial de binarios y ejecuciones en `historial_binarios.txt`.
- Indicadores de sistema (Temp, RAM, Disco, Bat, RPI) en la UI, con manejo de errores y valores legibles.
- Indicador visual y textual de bajo voltaje de la Raspberry Pi en la misma fila de indicadores.
- Botón de diagnóstico para ver la respuesta de `/api/indicadores` en la caja de logs.
- Separación clara entre la última ejecución del script y el último binario generado.

## Pendientes / Próximos pasos
- Automatizar la actualización del resumen en `historial_binarios.txt` desde el script `iniciar_servidor.sh`.
- Verificar y corregir la obtención de datos reales para los indicadores si siguen mostrando `--`.
- Mejorar la robustez del backend para que siempre entregue datos útiles, incluso si algún sensor o comando falla.
- Eliminar el botón de diagnóstico temporal cuando ya no sea necesario.
- (Opcional) Mejorar la visualización de logs y errores en la UI.

## Notas
- Siempre trabajar sobre archivos remotos en la Raspberry Pi vía SSH.
- Validar cambios en remoto antes de subir al repositorio.
- Mantener este documento actualizado tras cada sesión de trabajo relevante.

---

## Normas para el agente Go
- Siempre debe revisar y actualizar este documento (`bitacora_trabajo.md`) al inicio y al final de cada sesión.
- Debe consultar aquí el estado del proyecto, avances y pendientes antes de sugerir o ejecutar cambios.
- Si el usuario retoma el proyecto tras una pausa, debe leer este archivo y proponer continuar desde el último pendiente registrado.

---

## Historial de sesiones
- 2026-03-07: Se implementó la bitácora, se mejoró el historial de binarios y se avanzó en la robustez de los indicadores.
- 2026-03-07: En progreso: estamos trabajando en que los indicadores funcionen correctamente y comprobando que el binario se cree cada vez que iniciamos el servidor.
