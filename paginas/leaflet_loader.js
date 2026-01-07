// Carga y muestra un mapa Leaflet centrado en la ubicación GPS recibida
function mostrarMapaGPS(lat, lon, gpsActivo) {
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
    mapDiv.innerHTML = "";
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
    if (window._leafletMap) {
        window._leafletMap.setView([lat, lon], 16);
        if (window._leafletMarker) {
            window._leafletMarker.setLatLng([lat, lon]);
            window._leafletMarker.setIcon(puntoIcon);
        } else {
            window._leafletMarker = L.marker([lat, lon], {icon: puntoIcon}).addTo(window._leafletMap);
        }
        return;
    }
    window._leafletMap = L.map('mapa-gps').setView([lat, lon], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(window._leafletMap);
    window._leafletMarker = L.marker([lat, lon], {icon: puntoIcon}).addTo(window._leafletMap);

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
