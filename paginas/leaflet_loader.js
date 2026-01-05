// Carga y muestra un mapa Leaflet centrado en la ubicación GPS recibida
function mostrarMapaGPS(lat, lon) {
    if (!window.L) {
        const leafletCss = document.createElement('link');
        leafletCss.rel = 'stylesheet';
        leafletCss.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(leafletCss);
        const leafletJs = document.createElement('script');
        leafletJs.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        leafletJs.onload = () => crearMapa(lat, lon);
        document.body.appendChild(leafletJs);
    } else {
        crearMapa(lat, lon);
    }
}

function crearMapa(lat, lon) {
    let mapDiv = document.getElementById('mapa-gps');
    if (!mapDiv) {
        // Si no existe, no crear el div, ya que ahora está en el HTML
        return;
    }
    mapDiv.innerHTML = "";
    // Definir icono personalizado de barco/lancha
    var barcoIcon = L.icon({
        iconUrl: 'https://cdn-icons-png.flaticon.com/128/2933/2933186.png', // Icono de lancha/barco transparente
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16]
    });
    if (window._leafletMap) {
        window._leafletMap.setView([lat, lon], 16);
        if (window._leafletMarker) {
            window._leafletMarker.setLatLng([lat, lon]);
            window._leafletMarker.setIcon(barcoIcon);
        } else {
            window._leafletMarker = L.marker([lat, lon], {icon: barcoIcon}).addTo(window._leafletMap);
        }
        return;
    }
    window._leafletMap = L.map('mapa-gps').setView([lat, lon], 16);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(window._leafletMap);
    window._leafletMarker = L.marker([lat, lon], {icon: barcoIcon}).addTo(window._leafletMap);
}
