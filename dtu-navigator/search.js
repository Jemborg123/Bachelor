// search.js - Simple working version
let buildingData = {};

console.log('search.js loaded');

// Simple function to open/close panel
function togglePanel() {
    console.log('togglePanel called');
    const panel = document.getElementById('searchPanel');
    if (panel.classList.contains('open')) {
        panel.classList.remove('open');
    } else {
        panel.classList.add('open');
        document.getElementById('searchInput').focus();
    }
}

function closePanel() {
    const panel = document.getElementById('searchPanel');
    panel.classList.remove('open');
    document.getElementById('suggestions').style.display = 'none';
}

function searchBuilding() {
    const query = document.getElementById('searchInput').value.trim().toLowerCase();
    console.log('Searching for:', query);
    
    if (!query || !buildingData) return;
    
    const matches = [];
    for (const [name, coords] of Object.entries(buildingData)) {
        if (name.toLowerCase().includes(query)) {
            matches.push({ name, coords });
        }
    }
    
    console.log('Found matches:', matches.length);
    
    if (matches.length === 1) {
        const coord = matches[0].coords[0];
        if (coord) {
            const lat = coord[1];
            const lng = coord[0];
            
            if (window.mapAPI && window.mapAPI.getStartPoint() === null) {
                window.mapAPI.setStartPoint(lat, lng, matches[0].name);
                closePanel();
            } else if (window.mapAPI && window.mapAPI.getEndPoint() === null) {
                window.mapAPI.setEndPoint(lat, lng, matches[0].name);
                closePanel();
            }
        }
    } else if (matches.length > 1) {
        // Show suggestions
        const suggestionsDiv = document.getElementById('suggestions');
        suggestionsDiv.innerHTML = '<div style="padding: 8px; font-weight: bold;">Suggestions:</div>';
        matches.slice(0, 5).forEach(m => {
            const div = document.createElement('div');
            div.className = 'suggestion-item';
            div.textContent = m.name;
            div.onclick = () => {
                const coord = m.coords[0];
                if (coord) {
                    const lat = coord[1];
                    const lng = coord[0];
                    if (window.mapAPI && window.mapAPI.getStartPoint() === null) {
                        window.mapAPI.setStartPoint(lat, lng, m.name);
                        closePanel();
                    } else if (window.mapAPI && window.mapAPI.getEndPoint() === null) {
                        window.mapAPI.setEndPoint(lat, lng, m.name);
                        closePanel();
                    }
                }
                suggestionsDiv.innerHTML = '';
                suggestionsDiv.style.display = 'none';
            };
            suggestionsDiv.appendChild(div);
        });
        suggestionsDiv.style.display = 'block';
    } else {
        document.getElementById('info').innerHTML = '❌ No building found';
        setTimeout(() => {
            document.getElementById('info').innerHTML = '🔍 Search for a building or tap on map';
        }, 2000);
    }
}

async function loadBuildings() {
    try {
        console.log('Loading buildings from:', API_URL + '/buildings');
        const response = await fetch(API_URL + '/buildings');
        const data = await response.json();
        buildingData = data;
        console.log('Loaded', Object.keys(buildingData).length, 'buildings');
    } catch (error) {
        console.error('Error loading buildings:', error);
    }
}

// Simple event binding when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM ready, binding events');
    
    // Bind search button click
    const fab = document.getElementById('searchFab');
    if (fab) {
        fab.onclick = togglePanel;
        console.log('Fab bound');
    } else {
        console.log('Fab not found!');
    }
    
    // Bind close button
    const closeBtn = document.getElementById('closeSearchBtn');
    if (closeBtn) {
        closeBtn.onclick = closePanel;
    }
    
    // Bind search go button
    const goBtn = document.getElementById('searchBtn');
    if (goBtn) {
        goBtn.onclick = searchBuilding;
    }
    
    // Bind enter key
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.onkeypress = (e) => {
            if (e.key === 'Enter') searchBuilding();
        };
    }
    
    // Load buildings
    loadBuildings();
});