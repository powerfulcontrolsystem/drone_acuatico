// ============================================================
// indicadores.js — Funciones de indicadores del sistema
// Todas las funciones de indicadores centralizadas en un archivo
// ============================================================

// --- Función auxiliar para actualizar texto de un indicador ---
function setIndicadorTexto(id, valor) {
	const el = document.getElementById(id);
	if (!el) return;
	el.textContent = valor;
}

// --- Temperatura ---
function actualizarTemperatura(temperatura) {
	const celda = document.getElementById('indicador-temp');
	let tempNum = null;
	let valor = '--';
	if (temperatura && typeof temperatura.temperatura !== 'undefined') {
		tempNum = Number(temperatura.temperatura);
		if (!isNaN(tempNum)) valor = tempNum.toFixed(1) + ' °C';
	} else if (typeof temperatura === 'number' || (typeof temperatura === 'string' && temperatura !== '')) {
		tempNum = Number(temperatura);
		if (!isNaN(tempNum)) valor = tempNum.toFixed(1) + ' °C';
	}
	setIndicadorTexto('temp-valor', valor);
	if (celda) {
		if (tempNum === null || isNaN(tempNum)) {
			celda.style.color = '#f2f2f2';
		} else if (tempNum < 45) {
			celda.style.color = '#4caf50';
		} else if (tempNum < 60) {
			celda.style.color = '#ff9800';
		} else {
			celda.style.color = '#f44336';
		}
	}
}

// --- Obtener temperatura de la Raspberry Pi por API ---
async function obtenerTemperatura() {
	try {
		const res = await fetch('/api/temperatura', { cache: 'no-store' });
		if (!res.ok) return;
		const data = await res.json();
		if (data.exito && data.datos && typeof data.datos.temperatura !== 'undefined') {
			actualizarTemperatura(data.datos);
		}
	} catch (e) {
		console.warn('Error obteniendo temperatura:', e);
	}
}
// Alias para compatibilidad
var cargarTemperaturaRaspberry = obtenerTemperatura;

// --- Mapa GPS ---
function actualizarMapaDesdeGPS(gps) {
	if (!(gps && gps.latitud && gps.longitud)) return;
	const lat = Number(gps.latitud);
	const lon = Number(gps.longitud);
	const gpsActivo = gps.valido === true;
	if (!isNaN(lat) && !isNaN(lon) && typeof mostrarMapaGPS === 'function') {
		mostrarMapaGPS(lat, lon, gpsActivo);
	}
}

// --- Actualizar todos los indicadores (datos completos) ---
function actualizarIndicadores(data) {
	try {
		const d = data.datos || data;

		// Temperatura
		if (typeof actualizarTemperatura === 'function') {
			actualizarTemperatura(d.temperatura);
		}
		// RAM
		if (typeof d.ram !== 'undefined') {
			setIndicadorTexto('ram-valor', d.ram ? d.ram : '--');
		}
		// Disco
		if (typeof d.disco !== 'undefined') {
			setIndicadorTexto('disco-valor', d.disco ? d.disco : '--');
		}
		// Batería
		if (typeof d.bateria !== 'undefined') {
			setIndicadorTexto('bateria-valor', d.bateria ? d.bateria : '--');
		}
		// Voltaje Raspberry Pi
		if (typeof d.voltaje !== 'undefined') {
			let volt = d.voltaje;
			let valor = '--';
			let alerta = false;
			if (volt && typeof volt === 'object') {
				valor = (volt.voltaje !== undefined && volt.voltaje !== null) ? volt.voltaje : '--';
				alerta = !!volt.alerta;
			} else if (typeof volt === 'number' || typeof volt === 'string') {
				valor = volt;
			}
			setIndicadorTexto('voltaje-valor', valor);
			const iconoAlerta = document.getElementById('icono-voltaje-alerta');
			const iconoOk = document.getElementById('icono-voltaje-ok');
			const textoAlerta = document.getElementById('voltaje-alerta-texto');
			if (alerta) {
				if (iconoAlerta) iconoAlerta.style.display = 'inline';
				if (iconoOk) iconoOk.style.display = 'none';
				if (textoAlerta) { textoAlerta.textContent = '¡Bajo voltaje!'; textoAlerta.style.color = '#f44336'; }
			} else {
				if (iconoAlerta) iconoAlerta.style.display = 'none';
				if (iconoOk) iconoOk.style.display = 'inline';
				if (textoAlerta) { textoAlerta.textContent = 'OK'; textoAlerta.style.color = '#4caf50'; }
			}
		}
		// GPS
		if (typeof actualizarMapaDesdeGPS === 'function') {
			actualizarMapaDesdeGPS(d.gps);
		}
	} catch (eIndic) {
		console.error('Error en actualizarIndicadores:', eIndic);
	}
}

// --- Fallback HTTP para indicadores (cuando WebSocket no está disponible) ---
async function cargarIndicadoresRaspberryFallback() {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), 2500);
	try {
		const res = await fetch('/api/indicadores', { signal: controller.signal, cache: 'no-store' });
		if (!res.ok) return;
		const data = await res.json();
		if (data && data.datos) {
			actualizarIndicadores(data);
		}
	} catch (e) {
		console.warn('No se pudo actualizar indicadores (fallback):', e);
	} finally {
		clearTimeout(timeoutId);
	}
}

// --- Polling de indicadores (se activa cuando WS se desconecta) ---
var pollingIndicadores = null;

function iniciarPollingIndicadores() {
	if (pollingIndicadores) return;
	const ejecutar = async () => {
		if (typeof cargarIndicadoresRaspberryFallback === 'function') {
			await cargarIndicadoresRaspberryFallback();
		}
	};
	ejecutar();
	pollingIndicadores = setInterval(ejecutar, 3000);
}

function detenerPollingIndicadores() {
	if (!pollingIndicadores) return;
	clearInterval(pollingIndicadores);
	pollingIndicadores = null;
}

// --- Inicialización automática ---
// Polling de temperatura cada 5 segundos
setInterval(obtenerTemperatura, 5000);
window.addEventListener('DOMContentLoaded', function() {
	setTimeout(obtenerTemperatura, 500);
});
