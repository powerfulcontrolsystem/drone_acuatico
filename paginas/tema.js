// ==================== SISTEMA DE TEMA OSCURO/CLARO ====================
// Archivo compartido para todas las páginas del drone acuático
// Los temas se guardan en la base de datos del servidor

let temaOscuro = true;
let guardandoTema = false;  // Flag para evitar múltiples solicitudes simultáneas
let timerReintentoTema = null;

// Inicializar tema al cargar la página
async function inicializarTema() {
    try {
        // Obtener tema desde el servidor con timeout
        const signal = AbortSignal.timeout(5000);  // 5 segundos de timeout
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
            console.warn('Respuesta no OK al obtener tema:', response.status);
            aplicarTemaOscuro(false);
        }
    } catch (error) {
        console.error('Error cargando tema:', error);
        aplicarTemaOscuro(false);
    }
    
    // Agregar listener al toggle si existe
    const toggle = document.getElementById('toggle-tema');
    if (toggle) {
        toggle.addEventListener('change', cambiarTema);
    }
}

async function cambiarTema() {
    // Evitar múltiples cambios simultáneos
    if (guardandoTema) {
        console.warn('Cambio de tema ya en progreso, ignorando solicitud');
        return;
    }
    
    const toggle = document.getElementById('toggle-tema');
    temaOscuro = toggle ? !toggle.checked : !temaOscuro;
    
    if (temaOscuro) {
        await aplicarTemaOscuro();
    } else {
        await aplicarTemaClaro();
    }
}

async function aplicarTemaOscuro(actualizarToggle = true) {
    document.body.classList.remove('modo-claro');
    if (actualizarToggle) {
        const toggle = document.getElementById('toggle-tema');
        if (toggle) toggle.checked = false;
    }
    temaOscuro = true;
    
    // Guardar en el servidor (con reintentos)
    await guardarTemaConReintentos('oscuro', 3);
}

async function aplicarTemaClaro(actualizarToggle = true) {
    document.body.classList.add('modo-claro');
    if (actualizarToggle) {
        const toggle = document.getElementById('toggle-tema');
        if (toggle) toggle.checked = true;
    }
    temaOscuro = false;
    
    // Guardar en el servidor (con reintentos)
    await guardarTemaConReintentos('claro', 3);
}

async function guardarTemaConReintentos(tema, reintentos = 3) {
    // Evitar múltiples solicitudes simultáneas
    if (guardandoTema) {
        console.warn('Guardando tema ya en progreso');
        return;
    }
    
    guardandoTema = true;
    
    for (let intento = 0; intento < reintentos; intento++) {
        try {
            const signal = AbortSignal.timeout(5000);  // 5 segundos de timeout
            const response = await fetch('/api/tema', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tema: tema }),
                signal: signal
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.exito) {
                    console.log(`Tema ${tema} guardado exitosamente`);
                    guardandoTema = false;
                    return;
                }
            }
        } catch (error) {
            console.error(`Error en intento ${intento + 1} de guardar tema:`, error.message);
            
            // No reintentar si es el último intento
            if (intento < reintentos - 1) {
                // Esperar 1 segundo antes de reintentar
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
    }
    
    guardandoTema = false;
    console.error(`No se pudo guardar el tema después de ${reintentos} intentos`);
}

// Inicializar automáticamente cuando cargue el DOM
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarTema);
} else {
    inicializarTema();
}
