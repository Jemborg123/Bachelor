import React, { useState, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, WMSTileLayer, Marker, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import Switch from "react-switch";

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

  // Route state. Geometry now lives on the backend; the client only draws.
  const pathCoordsRef = useRef(null);     // full route [[lat, lng], ...] (for demo-off restore)
  const routeIdRef = useRef(null);        // id returned by /path, used by /progress
  const traveledLineRef = useRef(null);   // start -> pos marker (transparent)
  const remainingLineRef = useRef(null);  // pos marker -> end   (visible)

  // Throttle: only one /progress request in flight; coalesce drags (latest wins).
  const progressInFlight = useRef(false);
  const progressPending = useRef(null);   // latest { latlng } waiting to be sent

  // Clear all markers and path
  const resetRoute = useCallback(() => {
    if (markersRef.current.start) markersRef.current.start.remove();
    if (markersRef.current.end) markersRef.current.end.remove();
    markersRef.current = { start: null, end: null };

    if (traveledLineRef.current) { traveledLineRef.current.remove(); traveledLineRef.current = null; }
    if (remainingLineRef.current) { remainingLineRef.current.remove(); remainingLineRef.current = null; }
    pathCoordsRef.current = null;
    routeIdRef.current = null;
    progressInFlight.current = false;
    progressPending.current = null;

    if (posMarker) { posMarker.remove(); setPosMarker(null); }

    setStartPoint(null);
    setEndPoint(null);
    setPath(null);
    setDistance(null);
    setStats(null);
    setStatus('Tap on map to set start point');
  }, []);

  // Ask the backend where we are along the route, then redraw the two lines.
  // Reads refs + setStatus only, so it's safe from a captured drag handler.
  const sendProgress = useCallback(async (latlng) => {
    const routeId = routeIdRef.current;
    if (routeId == null) return;
    if (!traveledLineRef.current || !remainingLineRef.current) return;

    progressInFlight.current = true;
    try {
      const res = await axios.post(`${API_URL}/progress`, {
        route_id: routeId,
        position: { lat: latlng.lat, lng: latlng.lng },
      });
      const d = res.data;

      if (d.rerouted) {
        // Strayed too far — backend rebuilt the route from the marker to the end.
        routeIdRef.current = d.route_id;       // track the new route from now on
        pathCoordsRef.current = d.path;        // so demo-off restores the new one
        traveledLineRef.current.setLatLngs([]);
        remainingLineRef.current.setLatLngs(d.remaining.map(c => L.latLng(c[0], c[1])));
        remainingLineRef.current.setStyle({ color: '#ff4444' });
        setStatus('🔄 Off route — rerouted from your position');
      } else {
        traveledLineRef.current.setLatLngs(d.traveled.map(c => L.latLng(c[0], c[1])));
        remainingLineRef.current.setLatLngs(d.remaining.map(c => L.latLng(c[0], c[1])));
        if (d.off_route) {
          remainingLineRef.current.setStyle({ color: '#ffaa00' });
          setStatus(`⚠️ Off route — ${d.distance_m.toFixed(0)}m from the path`);
        } else {
          remainingLineRef.current.setStyle({ color: '#ff4444' });
          setStatus(`On route — ${d.distance_m.toFixed(0)}m from the path`);
        }
      }
    } catch (err) {
      console.error('progress error', err);
    } finally {
      progressInFlight.current = false;
      if (progressPending.current) {
        const next = progressPending.current;
        progressPending.current = null;
        sendProgress(next);
      }
    }
  }, []);

  const updateProgress = useCallback((latlng) => {
    if (progressInFlight.current) {
      progressPending.current = latlng;   // coalesce: keep only the latest
      return;
    }
    sendProgress(latlng);
  }, [sendProgress]);

  // Map click handler component
  function MapClickHandler() {
    const map = useMapEvents({
      click: async (e) => {
        const { lat, lng } = e.latlng;

        if (loading) {
          setStatus('Please wait, calculating path...');
          return;
        }

        if (path != null && demoSwitch){
          handleLiveFeedbackDemo(map, e);
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
              pathCoordsRef.current = pathLatLng;
              routeIdRef.current = data.route_id;   // used by /progress

              // Visible "ahead of you" line (full route to begin with).
              const remainingLine = L.polyline(pathLatLng, {
                color: '#ff4444',
                weight: 5,
                opacity: 0.8
              }).addTo(map);

              // "Behind you" line, transparent so the consumed part disappears.
              // Bump opacity (e.g. 0.25 + grey) for a faded trail instead.
              const traveledLine = L.polyline([], {
                color: '#ff4444',
                weight: 5,
                opacity: 0
              }).addTo(map);

              remainingLineRef.current = remainingLine;
              traveledLineRef.current = traveledLine;

              setPath(remainingLine);
              setDistance(data.distance);
              setStats(data);
              setStatus(`✓ Distance: ${data.distance.toFixed(0)}m | Time: ${data.time_ms.toFixed(0)}ms | Nodes visited: ${data.nodes_visited}`);
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

  const [demoSwitch, setDemoSwitch] = useState(false);
  function liveFeedbackDemo(){
    const next = !demoSwitch;
    setDemoSwitch(next);

    // Turning the demo off: drop the position marker and restore the full route.
    if (!next) {
      if (posMarker) { posMarker.remove(); setPosMarker(null); }
      progressPending.current = null;
      if (remainingLineRef.current && pathCoordsRef.current) {
        remainingLineRef.current.setLatLngs(pathCoordsRef.current.map(c => L.latLng(c[0], c[1])));
        remainingLineRef.current.setStyle({ color: '#ff4444' });
      }
      if (traveledLineRef.current) traveledLineRef.current.setLatLngs([]);
    }
  }

  const [posMarker, setPosMarker] = useState(null);
  function handleLiveFeedbackDemo(map, click){
    const { lat, lng } = click.latlng;
    if (posMarker == null){
      const marker = L.marker([lat, lng], {
        icon: L.divIcon({
          className: 'custom-div-icon',
          html: '<div style="background-color: blue; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
          iconSize: [16, 16]
        }),
        draggable: true
      }).addTo(map);

      // Live update while dragging; final precise update when the drag ends.
      marker.on('drag', (ev) => updateProgress(ev.latlng));
      marker.on('dragend', (ev) => updateProgress(ev.target.getLatLng()));

      setPosMarker(marker);
    }
    else{
      posMarker.setLatLng([lat, lng]);
    }
    // Update immediately on click-to-place too.
    updateProgress(click.latlng);
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
        <WMSTileLayer
          url="https://casgis.azurewebsites.net/geoserver/dtu/wms"
          layers="dtu:llyn_bygning_dtu"
          format="image/png"
          transparent={true}
          version="1.1.1"
          attribution="DTU GeoServer"
        />

        <MapClickHandler />
      </MapContainer>
      <div style={{
        position: 'absolute',
        top: 20,
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
        {!loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <span>search from</span>
            <input name="fromInput" />
            <span>to</span>
            <input name="toInput" />
            <Switch onChange={liveFeedbackDemo} checked={demoSwitch} />
          </div>
        )}

      </div>
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