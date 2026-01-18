// Calcula distancia (km) y rumbo (grados) entre dos coordenadas usando Haversine
function calcularDistanciaYRumbo(lat1, lon1, lat2, lon2) {
    const R = 6371; // Radio Tierra en km
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const distancia = R * c;
    
    // Calcular rumbo (bearing)
    const y = Math.sin(dLon * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180);
    const x = Math.cos(lat1 * Math.PI / 180) * Math.sin(lat2 * Math.PI / 180) -
              Math.sin(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.cos(dLon * Math.PI / 180);
    const rumbo = (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
    
    return { distancia: distancia, rumbo: rumbo };
}

// Actualiza o dibuja la ruta entre GPS actual y destino
function actualizarRuta() {
    if (!window._leafletMap || !window._gpsActual || !window._destinoActual) {
        // Si no hay mapa, GPS o destino, limpiar ruta
        if (window._leafletRuta) {
            window._leafletMap.removeLayer(window._leafletRuta);
            window._leafletRuta = null;
        }
        if (window._leafletInfoControl) {
            window._leafletMap.removeControl(window._leafletInfoControl);
            window._leafletInfoControl = null;
        }
        return;
    }
    
    const gps = window._gpsActual;
    const dest = window._destinoActual;
    const coords = [[gps.lat, gps.lon], [dest.lat, dest.lon]];
    
    // Dibujar o actualizar polyline
    if (window._leafletRuta) {
        window._leafletRuta.setLatLngs(coords);
    } else {
        window._leafletRuta = L.polyline(coords, {
            color: '#1e88e5',
            weight: 3,
            opacity: 0.7,
            dashArray: '10, 5'
        }).addTo(window._leafletMap);
    }
    
    // Calcular distancia y rumbo
    const info = calcularDistanciaYRumbo(gps.lat, gps.lon, dest.lat, dest.lon);
    
    // Crear o actualizar control de info
    if (window._leafletInfoControl) {
        window._leafletMap.removeControl(window._leafletInfoControl);
    }
    
    window._leafletInfoControl = L.control({position: 'topright'});
    window._leafletInfoControl.onAdd = function() {
        const div = L.DomUtil.create('div', 'info-ruta');
        div.innerHTML = '<div style="background:#fff;padding:8px 12px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.2);font-size:13px;line-height:1.6;">' +
                        '<strong style="color:#1e88e5;">📍 Ruta al Destino</strong><br>' +
                        'Distancia: <strong>' + info.distancia.toFixed(2) + ' km</strong><br>' +
                        'Rumbo: <strong>' + Math.round(info.rumbo) + '°</strong>' +
                        '</div>';
        return div;
    };
    window._leafletInfoControl.addTo(window._leafletMap);
}

// Carga y muestra un mapa Leaflet centrado en la ubicación GPS recibida
function mostrarMapaGPS(lat, lon, gpsActivo) {
    if (!isFinite(lat) || !isFinite(lon)) {
        return;
    }
    if (!window.L) {
        const leafletCss = document.createElement('link');
        leafletCss.rel = 'stylesheet';
        leafletCss.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(leafletCss);
        const leafletJs = document.createElement('script');
        leafletJs.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        leafletJs.onload = () => crearMapa(lat, lon, gpsActivo);
        document.body.appendChild(leafletJs);
    } else {
        crearMapa(lat, lon, gpsActivo);
    }
}

function crearMapa(lat, lon, gpsActivo) {
    let mapDiv = document.getElementById('mapa-gps');
    if (!mapDiv) {
        // Si no existe, no crear el div, ya que ahora está en el HTML
        return;
    }
    // NO limpiar innerHTML porque destruye el mapa de Leaflet existente
    // Definir icono personalizado: punto circular animado o fijo
    var puntoHtml;
    if (gpsActivo) {
        puntoHtml = '<div class="punto-gps punto-gps-verde"></div>';
    } else {
        puntoHtml = '<div class="punto-gps punto-gps-rojo"></div>';
    }
    var puntoIcon = L.divIcon({
        className: 'punto-gps-animado',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        html: puntoHtml
    });
    // Guardar posición GPS actual
    window._gpsActual = { lat: lat, lon: lon };
    
    if (window._leafletMap) {
        const keepZoom = window._leafletMap.getZoom() || 16;
        if (window.autoCenter !== false) {
            const z = Math.max(keepZoom, 16);
            window._leafletMap.setView([lat, lon], z);
        }
        if (window._leafletMarker) {
            window._leafletMarker.setLatLng([lat, lon]);
            window._leafletMarker.setIcon(puntoIcon);
        } else {
            window._leafletMarker = L.marker([lat, lon], {icon: puntoIcon}).addTo(window._leafletMap);
        }
        actualizarRuta(); // Actualizar ruta si hay destino
        return;
    }
    window._leafletMap = L.map('mapa-gps').setView([lat, lon], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(window._leafletMap);
    window._leafletMarker = L.marker([lat, lon], {icon: puntoIcon}).addTo(window._leafletMap);
    
    // Agregar event listener para clic en el mapa
    window._leafletMap.on('click', function(e) {
        const latClick = e.latlng.lat.toFixed(6);
        const lonClick = e.latlng.lng.toFixed(6);
        const confirmar = confirm('¿Establecer destino en:\n' + latClick + ', ' + lonClick + '?');
        if (confirmar && window.ws && window.ws.readyState === 1) {
            const nombre = (document.getElementById('gps-nombre')?.value || '').trim();
            console.log('Estableciendo destino desde clic en mapa:', latClick, lonClick);
            window.ws.send(JSON.stringify({ 
                tipo: 'gps_destino', 
                latitud: parseFloat(latClick), 
                longitud: parseFloat(lonClick),
                nombre: nombre || undefined
            }));
        }
    });

    // Agregar estilos para animación y colores
    if (!window._puntoGpsStyle) {
        var style = document.createElement('style');
        style.innerHTML = `
            .punto-gps {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                box-shadow: 0 0 8px #43a04788;
            }
            .punto-gps-verde {
                background: #43a047;
                animation: puntoParpadeo 1s infinite alternate;
            }
            .punto-gps-rojo {
                background: #e53935;
            }
            @keyframes puntoParpadeo {
                0% { opacity: 1; box-shadow: 0 0 8px #43a04788; }
                100% { opacity: 0.4; box-shadow: 0 0 18px #43a04744; }
            }
        `;
        document.head.appendChild(style);
        window._puntoGpsStyle = true;
    }
}

// Muestra o actualiza un marcador de destino en el mapa
function mostrarDestino(lat, lon, nombre) {
    function _colocar() {
        if (!window._leafletMap) {
            // Si el mapa aún no existe, créalo con un zoom razonable
            crearMapa(lat, lon, false);
        }
        
        // Guardar destino actual
        window._destinoActual = { lat: lat, lon: lon, nombre: nombre };
        
        const html = '<div class="punto-destino" title="Destino"></div>';
        var destinoIcon = L.divIcon({
            className: 'destino-icon',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
            html
        });
        if (window._leafletDestinoMarker) {
            window._leafletDestinoMarker.setLatLng([lat, lon]);
            window._leafletDestinoMarker.setIcon(destinoIcon);
        } else {
            window._leafletDestinoMarker = L.marker([lat, lon], {icon: destinoIcon}).addTo(window._leafletMap);
        }
        const label = nombre && nombre.trim() ? nombre.trim() : (lat.toFixed(5) + ", " + lon.toFixed(5));
        window._leafletDestinoMarker.bindPopup('Destino: ' + label, {autoClose: false});
        
        // Actualizar ruta
        actualizarRuta();
    }

    if (!window.L) {
        // Si Leaflet no está cargado aún, cárguelo y luego coloque el destino
        const leafletCss = document.createElement('link');
        leafletCss.rel = 'stylesheet';
        leafletCss.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(leafletCss);
        const leafletJs = document.createElement('script');
        leafletJs.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        leafletJs.onload = _colocar;
        document.body.appendChild(leafletJs);
    } else {
        _colocar();
    }

    // Estilos para el marcador de destino
    if (!window._destinoStyle) {
        var style = document.createElement('style');
        style.innerHTML = `
            .punto-destino {
                width: 18px;
                height: 18px;
                border-radius: 50%;
                background: #1e88e5;
                border: 2px solid #bbdefb;
                box-shadow: 0 0 8px #1e88e588;
            }
        `;
        document.head.appendChild(style);
        window._destinoStyle = true;
    }
}
