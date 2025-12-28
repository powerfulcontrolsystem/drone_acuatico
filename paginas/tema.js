// ==================== SISTEMA DE TEMA OSCURO/CLARO ====================
// Sistema robusto de temas para todas las páginas del drone acuático
// Los temas se guardan en la base de datos del servidor
// ======================================================================== */

let temaOscuro = true;
let guardandoTema = false;
let switchElement = null;

/**
 * Inicializar el sistema de temas cuando carga la página
 */
async function inicializarTema() {
    try {
        // Obtener el tema guardado del servidor
        const signal = AbortSignal.timeout(5000);
        const response = await fetch('/api/tema', { signal });
        
        if (response.ok) {
            const data = await response.json();
            const tema = data.tema || 'oscuro';
            
            if (tema === 'claro') {
                aplicarTemaClaro(false);
            } else {
                aplicarTemaOscuro(false);
            }
        } else {
            console.warn('Error obteniendo tema del servidor:', response.status);
            aplicarTemaOscuro(false);
        }
    } catch (error) {
        console.error('Error cargando tema:', error);
        aplicarTemaOscuro(false);
    }
    
    // Configurar listeners para todos los switches en la página
    configurarListenersSwitches();
}

/**
 * Buscar y configurar listeners para todos los switches de tema
 */
function configurarListenersSwitches() {
    // Buscar el switch por diferentes selectores posibles
    const switches = [
        document.getElementById('toggle-tema'),
        document.querySelector('#toggle-tema'),
        document.querySelector('input[id*="tema"]'),
        document.querySelector('input[type="checkbox"][id*="tema"]')
    ].filter(Boolean);

    switches.forEach(toggle => {
        if (toggle && !toggle.hasAttribute('data-tema-listener-attached')) {
            toggle.addEventListener('change', cambiarTema);
            toggle.setAttribute('data-tema-listener-attached', 'true');
            switchElement = toggle;
            console.log('Listener de tema configurado');
        }
    });
}

/**
 * Manejar el cambio de tema desde el switch
 */
async function cambiarTema(event) {
    if (guardandoTema) {
        console.warn('Cambio de tema ya en progreso');
        // Revertir el switch mientras se procesa
        if (event.target) {
            event.target.checked = temaOscuro;
        }
        return;
    }

    guardandoTema = true;
    
    try {
        // Determinar tema basado en el estado del switch
        const esModoClaro = event.target ? event.target.checked : !temaOscuro;
        
        if (esModoClaro) {
            await aplicarTemaClaro();
        } else {
            await aplicarTemaOscuro();
        }
    } catch (error) {
        console.error('Error cambiando tema:', error);
        // Revertir el switch en caso de error
        if (event.target) {
            event.target.checked = temaOscuro;
        }
    } finally {
        guardandoTema = false;
    }
}

/**
 * Aplicar tema oscuro
 * @param {boolean} actualizarToggle - Si debe actualizar el estado del switch (default: true)
 */
async function aplicarTemaOscuro(actualizarToggle = true) {
    // Aplicar clase de tema al documento
    document.body.classList.remove('modo-claro');
    document.documentElement.classList.remove('modo-claro');
    
    // Actualizar estado del switch si corresponde
    if (actualizarToggle) {
        const toggles = document.querySelectorAll('input[id*="tema"]');
        toggles.forEach(toggle => {
            toggle.checked = false;
        });
    }
    
    temaOscuro = true;
    console.log('✓ Tema oscuro aplicado');
    
    // Guardar en servidor
    await guardarTemaConReintentos('oscuro', 3);
}

/**
 * Aplicar tema claro
 * @param {boolean} actualizarToggle - Si debe actualizar el estado del switch (default: true)
 */
async function aplicarTemaClaro(actualizarToggle = true) {
    // Aplicar clase de tema al documento
    document.body.classList.add('modo-claro');
    document.documentElement.classList.add('modo-claro');
    
    // Actualizar estado del switch si corresponde
    if (actualizarToggle) {
        const toggles = document.querySelectorAll('input[id*="tema"]');
        toggles.forEach(toggle => {
            toggle.checked = true;
        });
    }
    
    temaOscuro = false;
    console.log('✓ Tema claro aplicado');
    
    // Guardar en servidor
    await guardarTemaConReintentos('claro', 3);
}

/**
 * Guardar tema en el servidor con reintentos automáticos
 * @param {string} tema - Tema a guardar ('oscuro' o 'claro')
 * @param {number} reintentos - Número de reintentos (default: 3)
 */
async function guardarTemaConReintentos(tema, reintentos = 3) {
    if (guardandoTema && reintentos < 3) {
        // Ya hay un guardado en progreso
        return;
    }
    
    for (let intento = 0; intento < reintentos; intento++) {
        try {
            const signal = AbortSignal.timeout(5000);
            const response = await fetch('/api/tema', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tema: tema }),
                signal: signal
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.exito) {
                    console.log(`✓ Tema ${tema} guardado en servidor`);
                    return;
                }
            } else {
                console.warn(`Respuesta servidor ${response.status} al guardar tema`);
            }
        } catch (error) {
            console.warn(`Intento ${intento + 1}/${reintentos} falló:`, error.message);
            
            if (intento < reintentos - 1) {
                // Esperar antes de reintentar
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
    }
    
    console.error(`✗ No se pudo guardar tema después de ${reintentos} intentos`);
}

/**
 * Alternar tema manualmente (útil para botones o atajos)
 */
async function alternarTema() {
    if (guardandoTema) return;
    
    if (temaOscuro) {
        await aplicarTemaClaro();
    } else {
        await aplicarTemaOscuro();
    }
}

// Inicializar cuando cargue el DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarTema);
} else {
    inicializarTema();
}

// Reintentar configurar listeners cada segundo en caso de que el DOM se actualice dinámicamente
setInterval(configurarListenersSwitches, 1000);
