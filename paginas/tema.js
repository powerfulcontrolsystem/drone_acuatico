// ==================== TEMA OSCURO UNIVERSAL ====================
// Solo tema oscuro - sin cambios ni base de datos
// ===============================================================

/**
 * Inicializar tema oscuro (sin lógica de cambio)
 */
function inicializarTema() {
    // Solo aplicar tema oscuro
    document.body.style.background = 'var(--color-bg-primary)';
    document.body.style.color = 'var(--color-text-primary)';
    console.log('✓ Tema oscuro aplicado (único)');
}

// Inicializar al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', inicializarTema);
} else {
    inicializarTema();
}
