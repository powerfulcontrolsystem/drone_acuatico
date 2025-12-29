// ==================== SISTEMA DE 3 TEMAS ====================
// Temas: oscuro (default), claro, negro
// =============================================================

const TEMAS = ['oscuro', 'claro', 'negro'];
let temaActual = 'oscuro';
let cambiandoTema = false;

/**
 * Inicializar sistema de temas
 */
async function inicializarTema() {
    // Aplicar tema oscuro por defecto
    aplicarTema('oscuro', false);
    
    // Cargar tema guardado del servidor
    try {
        const response = await fetch('/api/tema');
        if (response.ok) {
            const data = await response.json();
            const tema = data.tema || 'oscuro';
            aplicarTema(tema, false);
        }
    } catch (error) {
        console.log('No se pudo cargar tema, usando oscuro por defecto');
    }
}

/**
 * Aplicar tema visual
 */
function aplicarTema(tema, guardar = true) {
    // Remover TODAS las clases de tema
    document.body.classList.remove('tema-oscuro', 'tema-claro', 'tema-negro');
    document.documentElement.classList.remove('tema-oscuro', 'tema-claro', 'tema-negro');
    
    // Aplicar clase solo si NO es oscuro (oscuro es el default en :root)
    if (tema === 'claro') {
        document.body.classList.add('tema-claro');
    } else if (tema === 'negro') {
        document.body.classList.add('tema-negro');
    }
    // Para 'oscuro' no agregamos clase, usamos :root
    
    temaActual = tema;
    actualizarIconoBoton();
    
    console.log(`✓ Tema ${tema} aplicado`);
    
    // Guardar en servidor
    if (guardar) {
        guardarTema(tema);
    }
}

/**
 * Actualizar icono del botón según tema actual
 */
function actualizarIconoBoton() {
    const boton = document.getElementById('btn-cambiar-tema');
    if (!boton) return;
    
    const iconos = {
        'oscuro': '🌙',   // Luna
        'claro': '☀️',     // Sol
        'negro': '⚫'      // Círculo negro
    };
    
    boton.textContent = iconos[temaActual] || '🌙';
    boton.title = `Tema: ${temaActual} (clic para cambiar)`;
}

/**
 * Cambiar al siguiente tema
 */
function cambiarTema() {
    if (cambiandoTema) return;
    cambiandoTema = true;
    
    // Obtener siguiente tema
    const indiceActual = TEMAS.indexOf(temaActual);
    const siguienteIndice = (indiceActual + 1) % TEMAS.length;
    const siguienteTema = TEMAS[siguienteIndice];
    
    aplicarTema(siguienteTema, true);
    
    setTimeout(() => { cambiandoTema = false; }, 300);
}

/**
 * Guardar tema en servidor
 */
async function guardarTema(tema) {
    try {
        const response = await fetch('/api/tema', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tema: tema })
        });
        
        if (response.ok) {
            console.log(`✓ Tema ${tema} guardado`);
        }
    } catch (error) {
        console.warn('Error guardando tema:', error);
    }
}

// Inicializar al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarTema);
} else {
    inicializarTema();
}
