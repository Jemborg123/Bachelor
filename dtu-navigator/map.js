// map.js - Core map functionality for DTU Navigator

const API_URL = window.location.hostname === 'localhost' 
    ? 'https://bachelor-ntwt.onrender.com:5000' 
    : 'http://' + window.location.hostname + ':5000';

let map;
let startMarker = null;
let endMarker = null;
let currentPath = null;
let startPoint = null;
let endPoint = null;
let loading = false;

// Global API for search.js to call
window.mapAPI = {
    setStartPoint: (lat, lng, buildingName) => {
        if (loading) return false;
        if (startMarker) startMarker.remove();
        startMarker = L.marker([lat, lng], {
            icon: L.divIcon({
                html: '<div style="background-color: #4CAF50; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
                iconSize: [16, 16]
            })
        }).addTo(map);
        startPoint = { lat, lng };
        const msg = buildingName ? `📍 Start: ${buildingName}. Set end point...` : '📍 Start set. Set end point...';
        document.getElementById('info').innerHTML = msg;
        document.getElementById('info').style.background = '#e8f5e9';
        map.setView([lat, lng], 17);
        return true;
    },
    setEndPoint: (lat, lng, buildingName) => {
        if (loading) return false;
        if (endMarker) endMarker.remove();
        endMarker = L.marker([lat, lng], {
            icon: L.divIcon({
                html: '<div style="background-color: #f44336; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
                iconSize: [16, 16]
            })
        }).addTo(map);
        endPoint = { lat, lng };
        calculatePath();
        return true;
    },
    reset: () => {
        reset();
    },
    getStartPoint: () => startPoint,
    getEndPoint: () => endPoint,
    isLoading: () => loading
};

async function calculatePath() {
    loading = true;
    document.getElementById('info').innerHTML = '<div class="spinner"></div> Calculating shortest path...';
    document.getElementById('info').style.background = 'white';
    
    try {
        const response = await fetch(API_URL + '/path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: startPoint, target: endPoint })
        });
        
        const data = await response.json();
        
        if (data.error) {
            document.getElementById('info').innerHTML = '❌ Error: ' + data.error;
            setTimeout(reset, 3000);
            return;
        }
        
        if (currentPath) currentPath.remove();
        if (data.path && data.path.length > 0) {
            currentPath = L.polyline(data.path, {
                color: '#ff4444',
                weight: 5,
                opacity: 0.8
            }).addTo(map);
            
            map.fitBounds(currentPath.getBounds());
            
            document.getElementById('info').innerHTML = 
                '✅ Distance: <span class="status-distance">' + data.distance.toFixed(0) + 'm</span> | ' +
                'Time: <span class="status-time">' + data.time_ms.toFixed(0) + 'ms</span> | ' +
                'Nodes: <span class="status-nodes">' + data.nodes_visited + '</span>';
            document.getElementById('info').style.background = '#e8f5e9';
        } else {
            document.getElementById('info').innerHTML = '❌ No path found between these points';
            document.getElementById('info').style.background = '#ffebee';
        }
        
        setTimeout(reset, 5000);
        
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('info').innerHTML = '❌ Cannot connect to server. Make sure backend is running.';
        document.getElementById('info').style.background = '#ffebee';
        setTimeout(reset, 4000);
    } finally {
        loading = false;
    }
}

function reset() {
    if (startMarker) startMarker.remove();
    if (endMarker) endMarker.remove();
    if (currentPath) currentPath.remove();
    startPoint = null;
    endPoint = null;
    startMarker = null;
    endMarker = null;
    currentPath = null;
    document.getElementById('info').innerHTML = '🔍 Search for a building or tap on map';
    document.getElementById('info').style.background = 'white';
    document.getElementById('searchInput').value = '';
    document.getElementById('suggestions').style.display = 'none';
}

function initMap() {
    map = L.map('map').setView([55.7858, 12.5215], 16);

    window.mapInstance = map;
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    L.tileLayer.wms('https://casgis.azurewebsites.net/geoserver/dtu/wms', {
        layers: 'dtu:llyn_bygning_dtu',
        format: 'image/png',
        transparent: true,
        attribution: 'DTU GeoServer'
    }).addTo(map);
    
    // Handle map clicks for manual point selection
    map.on('click', async (e) => {
        if (loading) return;
        const { lat, lng } = e.latlng;
        
        if (startPoint === null) {
            if (startMarker) startMarker.remove();
            startMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    html: '<div style="background-color: #4CAF50; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [16, 16]
                })
            }).addTo(map);
            startPoint = { lat, lng };
            document.getElementById('info').innerHTML = '📍 Start set. Tap or search for end point...';
            document.getElementById('info').style.background = '#e8f5e9';
        } 
        else if (endPoint === null) {
            if (endMarker) endMarker.remove();
            endMarker = L.marker([lat, lng], {
                icon: L.divIcon({
                    html: '<div style="background-color: #f44336; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white;"></div>',
                    iconSize: [16, 16]
                })
            }).addTo(map);
            endPoint = { lat, lng };
            calculatePath();
        }
    });
    
    console.log('Map initialized');
}

window.addEventListener('load', initMap);