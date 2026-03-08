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

// --- Formatear RAM ---
function formatearRAM(ram) {
	if (!ram || typeof ram !== 'object') return '--';
	if (typeof ram.percent !== 'undefined') return ram.percent + '%';
	return '--';
}

// --- Formatear Disco ---
function formatearDisco(disco) {
	if (!disco || typeof disco !== 'object') return '--';
	if (typeof disco.porcentaje !== 'undefined') return disco.porcentaje + '%';
	return '--';
}

// --- Formatear Batería ---
function formatearBateria(bat) {
	if (!bat || typeof bat !== 'object') return '--';
	if (!bat.conectado) return 'N/C';
	if (typeof bat.porcentaje !== 'undefined') return bat.porcentaje + '%';
	return '--';
}

// --- Formatear Voltaje RPI ---
function formatearVoltaje(volt) {
	if (!volt || typeof volt !== 'object') {
		if (typeof volt === 'number') return volt + ' V';
		if (typeof volt === 'string') return volt;
		return '--';
	}
	let valor = '--';
	if (volt.voltaje !== undefined && volt.voltaje !== null) {
		valor = volt.voltaje + ' V';
	}
	return valor;
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
			const ramTexto = formatearRAM(d.ram);
			setIndicadorTexto('ram-valor', ramTexto);
			const celdaRam = document.getElementById('indicador-ram');
			if (celdaRam && d.ram && typeof d.ram.percent === 'number') {
				if (d.ram.percent < 60) celdaRam.style.color = '#a3e635';
				else if (d.ram.percent < 85) celdaRam.style.color = '#ff9800';
				else celdaRam.style.color = '#f44336';
			}
		}
		// Disco
		if (typeof d.disco !== 'undefined') {
			const discoTexto = formatearDisco(d.disco);
			setIndicadorTexto('disco-valor', discoTexto);
			const celdaDisco = document.getElementById('indicador-disco');
			if (celdaDisco && d.disco && typeof d.disco.porcentaje === 'number') {
				if (d.disco.porcentaje < 70) celdaDisco.style.color = '#60a5fa';
				else if (d.disco.porcentaje < 90) celdaDisco.style.color = '#ff9800';
				else celdaDisco.style.color = '#f44336';
			}
		}
		// Batería
		if (typeof d.bateria !== 'undefined') {
			const batTexto = formatearBateria(d.bateria);
			setIndicadorTexto('bateria-valor', batTexto);
			const celdaBat = document.getElementById('indicador-bateria');
			if (celdaBat && d.bateria && typeof d.bateria.porcentaje === 'number') {
				if (d.bateria.porcentaje > 50) celdaBat.style.color = '#4caf50';
				else if (d.bateria.porcentaje > 20) celdaBat.style.color = '#ff9800';
				else celdaBat.style.color = '#f44336';
			}
		}
		// Voltaje Raspberry Pi
		if (typeof d.voltaje !== 'undefined') {
			const voltTexto = formatearVoltaje(d.voltaje);
			setIndicadorTexto('voltaje-valor', voltTexto);
			let alerta = false;
			if (d.voltaje && typeof d.voltaje === 'object') {
				alerta = !!d.voltaje.alerta;
			}
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
// Polling de todos los indicadores cada 5 segundos
setInterval(function() {
	cargarIndicadoresRaspberryFallback();
}, 5000);
window.addEventListener('DOMContentLoaded', function() {
	setTimeout(obtenerTemperatura, 500);
	setTimeout(cargarIndicadoresRaspberryFallback, 1000);
});
