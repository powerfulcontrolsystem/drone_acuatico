#!/bin/bash
HTML_FILE=/home/admin/drone_acuatico/paginas/control remoto digital.html

# 1. Quitar la vieja tabla indicadores-tabla (si existe de intentos previos)
sed -i /<table class="indicadores-tabla"/,/<\/table>/d $HTML_FILE

# 2. Quitar el script de cargarIndicadoresReales viejo al final (que inyectaba batteria, disco, etc)
sed -i /function asegurarFilaIndicadores() {/,/})();/d $HTML_FILE

# 3. Sobre-escribir la función actualizarTemperatura vieja e inyectar el controlador de RAM nuevo
sed -i /function actualizarTemperatura(temperatura) {/!b;n;c\\
 const celdaTemp = document.getElementById(\indicador-temp\');\\
 let tempNum = null;\\
 if (temperatura && typeof temperatura.temperatura !== \undefined\') {\\
 document.getElementById(\temp-valor\').textContent = Number(temperatura.temperatura).toFixed(1) + " °C\';\\
                        tempNum = Number(temperatura.temperatura);\\
                } else {\\
                        document.getElementById(\temp-valor\').textContent = \--\';\\
                }\\
                if (celdaTemp) {\\
                        if (tempNum === null || isNaN(tempNum)) {\\
                                celdaTemp.style.background = \#23272b\'; celdaTemp.style.color = \#f2f2f2\';\\
                        } else if (tempNum < 45) {\\
                                celdaTemp.style.background = \#43a047\'; celdaTemp.style.color = \#fff\';\\
                                celdaTemp.style.boxShadow = \0 2px 8px rgba 67 160 71 0.4 \';\\
                        } else if (tempNum < 60) {\\
                                celdaTemp.style.background =  \#fbc02d\'; celdaTemp.style.color = \#23272b\';\\
                                celdaTemp.style.boxShadow = \0 2px 8px rgba 251 192 45 0.4 \';\\
                        } else {\\
                                celdaTemp.style.background =  \#d32f2f\'; celdaTemp.style.color = \#fff\';\\
                                celdaTemp.style.boxShadow = \0 2px 8px rgba 211 47 47 0.4 \';\\
                        }\\
                }\\
        }\\
\\
        function actualizarRAM(ramData) {\\
                const celdaRam = document.getElementById( \indicador-ram\');\\
                let ramNum = null;\\
                if (ramData && typeof ramData.percent !== \undefined\') {\\
                        document.getElementById(\ram-valor\').textContent = Math.round(ramData.percent) + " %\';\\
 ramNum = Number(ramData.percent);\\
 } else {\\
 document.getElementById(\ram-valor\').textContent = \--\';\\
 }\\
 if (celdaRam) {\\
 if (ramNum === null || isNaN(ramNum)) {\\
 celdaRam.style.background = \#23272b\'; celdaRam.style.color = \#f2f2f2\';\\
 } else if (ramNum < 60) {\\
 celdaRam.style.background = \#43a047\'; celdaRam.style.color = \#fff\';\\
 celdaRam.style.boxShadow = \0 2px 8px rgba 67 160 71 0.4 \';\\
 } else if (ramNum < 85) {\\
 celdaRam.style.background =  \#fbc02d\'; celdaRam.style.color = \#23272b\';\\
 celdaRam.style.boxShadow = \0 2px 8px rgba 251 192 45 0.4 \';\\
 } else {\\
 celdaRam.style.background =  \#d32f2f\'; celdaRam.style.color = \#fff\';\\
 celdaRam.style.boxShadow = \0 2px 8px rgba 211 47 47 0.4 \';\\
 }\\
 }\\
 }\\
\\
 // Modificar cargarTemperaturaRaspberry para que llame la API de indicadores unificada\\
 async function cargarTemperaturaRaspberry() {\\
 const controller = new AbortController();\\
 const timeoutId = setTimeout(() => controller.abort(), 2500);\\
 try {\\
 const res = await fetch( \/api/indicadores\', { signal: controller.signal, cache: \no-store\' });\\
 if (!res.ok) return;\\
 const data = await res.json();\\
 if (data && data.datos) {\\
 actualizarTemperatura(data.datos.temperatura);\\
 actualizarRAM(data.datos.ram);\\
 }\\
 } catch (e) {\\
 console.warn(\No se pudieron actualizar indicadores:\', e);\\
 } finally {\\
 clearTimeout(timeoutId);\\
 }\\
 } // Fin parche 
