// ==================== APLICAR CONFIGURACIÓN DE TAMAÑO DE LETRA ====================
// Aplica el tamaño de letra configurado a los datos de control

async function aplicarTamanoLetraDatos() {
    try {
        const response = await fetch('/api/config');
        if (response.ok) {
            const config = await response.json();
            const tamano = config.tamano_letra_datos || 12;
            
            // Aplicar tamaño a todos los indicadores de datos
            const selectores = [
                '.indicador-ram',
                '.indicador-temp',
                '.indicador-bat',
                '.indicador-peso',
                '.indicador-red',
                '.indicador-solar',
                '.info-sistema',
                '.info-sistema span',
                '.estado-conexion'
            ];
            
            selectores.forEach(selector => {
                const elementos = document.querySelectorAll(selector);
                elementos.forEach(el => {
                    el.style.fontSize = `${tamano}px`;
                });
            });
            
            console.log(`Tamaño de letra aplicado: ${tamano}px`);
        }
    } catch (error) {
        console.error('Error aplicando tamaño de letra:', error);
    }
}

// Aplicar automáticamente al cargar
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', aplicarTamanoLetraDatos);
} else {
    aplicarTamanoLetraDatos();
}
