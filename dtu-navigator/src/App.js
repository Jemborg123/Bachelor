import React, { useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';

// Fix for Leaflet marker icons in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
});

// Your backend API URL (change to your computer's IP)
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [path, setPath] = useState(null);
  const [distance, setDistance] = useState(null);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState('Tap on map to set start point');
  const [loading, setLoading] = useState(false);
  const markersRef = useRef({ start: null, end: null });

  // Clear all markers and path
  const resetRoute = useCallback(() => {
    if (markersRef.current.start) markersRef.current.start.remove();
    if (markersRef.current.end) markersRef.current.end.remove();
    markersRef.current = { start: null, end: null };
    setStartPoint(null);
    setEndPoint(null);
    setPath(null);
    setDistance(null);
    setStats(null);
    setStatus('Tap on map to set start point');
  }, []);

  // Map click handler component
  function MapClickHandler() {
    const map = useMapEvents({
      click: async (e) => {
        const { lat, lng } = e.latlng;
        
        if (loading) {
          setStatus('Please wait, calculating path...');
          return;
        }
        
        if (!startPoint) {
          // Set start point
          const marker = L.marker([lat, lng], { 
            icon: L.divIcon({ 
              className: 'custom-div-icon',
              html: '<div style="background-color: green; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
              iconSize: [16, 16]
            })
          }).addTo(map);
          markersRef.current.start = marker;
          
          setStartPoint([lat, lng]);
          setStatus('Start point set. Tap to set end point...');
        } 
        else if (!endPoint) {
          // Set end point
          const marker = L.marker([lat, lng], {
            icon: L.divIcon({
              className: 'custom-div-icon',
              html: '<div style="background-color: red; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
              iconSize: [16, 16]
            })
          }).addTo(map);
          markersRef.current.end = marker;
          
          setEndPoint([lat, lng]);
          setStatus('Calculating path...');
          setLoading(true);
          
          try {
            // Call backend to get path
            const response = await axios.post(`${API_URL}/path`, {
              source: { lat: startPoint[0], lng: startPoint[1] },
              target: { lat, lng }
            });
            
            const data = response.data;
            
            // Draw path
            if (data.path && data.path.length > 0) {
              const pathLatLng = data.path.map(coord => [coord[0], coord[1]]);
              const polyline = L.polyline(pathLatLng, { 
                color: '#ff4444', 
                weight: 5, 
                opacity: 0.8 
              }).addTo(map);
              setPath(polyline);
              setDistance(data.distance);
              setStats(data);
              setStatus(`✓ Distance: ${data.distance.toFixed(0)}m | Time: ${data.time_ms.toFixed(0)}ms | Nodes visited: ${data.nodes_visited}`);
              
              // Auto reset after 5 seconds
              setTimeout(() => {
                resetRoute();
                if (polyline) polyline.remove();
              }, 5000);
            } else {
              setStatus('No path found! Try different points.');
              setTimeout(resetRoute, 3000);
            }
          } catch (error) {
            console.error('Error:', error);
            setStatus('Error finding path. Make sure backend is running.');
            setTimeout(resetRoute, 3000);
          } finally {
            setLoading(false);
          }
        }
      }
    });
    
    return null;
  }

  return (
    <div style={{ height: '100vh', width: '100%', position: 'relative' }}>
      <MapContainer 
        center={[55.7858, 12.5215]} 
        zoom={16} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
        attributionControl={true}
      >
        {/* Base OpenStreetMap tiles */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        
        {/* DTU Buildings overlay (WMS) */}
        <TileLayer
          url="https://casgis.azurewebsites.net/geoserver/dtu/wms?service=WMS&version=1.1.1&request=GetMap&layers=dtu:llyn_bygning_dtu&styles=&format=image/png&transparent=true&bbox={bbox-epsg-3857}"
          attribution="DTU GeoServer"
        />
        
        <MapClickHandler />
      </MapContainer>
      
      {/* Status panel */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        right: 20,
        background: loading ? 'rgba(255,255,255,0.9)' : 'white',
        padding: loading ? '8px 12px' : '12px',
        borderRadius: 10,
        boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
        zIndex: 1000,
        fontSize: loading ? '12px' : '14px',
        textAlign: 'center',
        transition: 'all 0.3s ease'
      }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <div className="spinner" style={{
              width: '16px',
              height: '16px',
              border: '2px solid #ccc',
              borderTopColor: '#ff4444',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite'
            }} />
            <span>Finding best route...</span>
          </div>
        )}
        <div style={{ fontWeight: loading ? 'normal' : '500' }}>{status}</div>
        {stats && !loading && (
          <div style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
            Algorithm: {stats.algorithm || 'A*'} | Nodes explored: {stats.nodes_visited}
          </div>
        )}
      </div>
      
      {/* Loading animation keyframes */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default App;