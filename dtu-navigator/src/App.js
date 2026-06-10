import React, { useState, useCallback, useRef, useEffect } from 'react';
import { MapContainer, TileLayer, WMSTileLayer, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import 'leaflet/dist/leaflet.css';
import Switch from "react-switch";
import { useGeolocated } from "react-geolocated";
import SearchField from './searchField';

// Fix for Leaflet marker icons in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png',
});

// Your backend API URL (change to your computer's IP)
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Fallback area-of-interest (DTU Lyngby) used until /bounds is fetched.
const AREA_BOUNDS = L.latLngBounds(
  L.latLng(55.779, 12.508),   // south-west
  L.latLng(55.793, 12.532)    // north-east
);

// Stashes the Leaflet map instance into a ref so logic outside click events
// (the GPS handler) can reach it.
function MapRefBinder({ mapRef }) {
  const map = useMap();
  useEffect(() => { mapRef.current = map; }, [map, mapRef]);
  return null;
}

function App() {
  const [startPoint, setStartPoint] = useState(null);
  const [endPoint, setEndPoint] = useState(null);
  const [path, setPath] = useState(null);
  const [distance, setDistance] = useState(null);
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState('Tap on map to set start point');
  const [loading, setLoading] = useState(false);
  const markersRef = useRef({ start: null, end: null });

  
  const [demoSwitch, setDemoSwitch] = useState(false);

  // Route state. Geometry lives on the backend; the client only draws.
  const pathCoordsRef = useRef(null);     // full route [[lat, lng], ...] (for demo-off restore)
  const routeIdRef = useRef(null);        // id returned by /path, used by /progress
  const traveledLineRef = useRef(null);   // start -> pos marker (transparent)
  const remainingLineRef = useRef(null);  // pos marker -> end   (visible)

  const mapRef = useRef(null);            // Leaflet map instance (via MapRefBinder)
  const posMarkerRef = useRef(null);      // blue position marker (GPS or manual)
  const areaBoundsRef = useRef(null);     // bounds fetched from /bounds (overrides default)

  // Throttle: only one /progress request in flight; coalesce drags (latest wins).
  const progressInFlight = useRef(false);
  const progressPending = useRef(null);

  // Pull the real area-of-interest from the backend (falls back to AREA_BOUNDS).
  useEffect(() => {
    axios.get(`${API_URL}/bounds`)
      .then(res => {
        const b = res.data;
        areaBoundsRef.current = L.latLngBounds(
          L.latLng(b.south, b.west), L.latLng(b.north, b.east));
      })
      .catch(() => { /* keep the hardcoded fallback */ });
  }, []);

  // ----- Geolocation -----
  const {
    coords,
    isGeolocationAvailable,
    positionError,
    getPosition,
  } = useGeolocated({
    positionOptions: { enableHighAccuracy: true },
    watchPosition: true,
    userDecisionTimeout: 8000,
    suppressLocationOnMount: true,   // only ask when the user turns tracking on
  });

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

    if (posMarkerRef.current) { posMarkerRef.current.remove(); posMarkerRef.current = null; }

    setStartPoint(null);
    setEndPoint(null);
    setPath(null);
    setDistance(null);
    setStats(null);
    setStatus('Tap on map to set start point');
  }, []);

  // Ask the backend where we are along the route, then redraw the two lines.
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
        routeIdRef.current = d.route_id;
        pathCoordsRef.current = d.path;
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

  // One place that builds the blue marker + wires its drag handlers, shared by
  // both the GPS tracker and manual click-to-place.
  const makePosMarker = useCallback((map, ll) => {
    const m = L.marker(ll, {
      icon: L.divIcon({
        className: 'custom-div-icon',
        html: '<div style="background-color: blue; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
        iconSize: [16, 16]
      }),
      draggable: true
    }).addTo(map);
    m.on('drag', (ev) => updateProgress(ev.latlng));
    m.on('dragend', (ev) => updateProgress(ev.target.getLatLng()));
    return m;
  }, [updateProgress]);

  // Drive the marker from GPS while tracking is on and the fix is in-bounds.
  useEffect(() => {
    if (!demoSwitch || !coords) return;
    const map = mapRef.current;
    if (!map) return;

    const ll = L.latLng(coords.latitude, coords.longitude);
    const area = areaBoundsRef.current || AREA_BOUNDS;
    if (!area.contains(ll)) {
      setStatus('📍 You appear to be outside the tracked area — GPS paused');
      // return;
    }

    if (posMarkerRef.current) {
      posMarkerRef.current.setLatLng(ll);
    } else {
      posMarkerRef.current = makePosMarker(map, ll);
    }
    updateProgress(ll);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coords, demoSwitch, makePosMarker, updateProgress]);

  // Surface geolocation failures while tracking is on.
  useEffect(() => {
    if (demoSwitch && positionError) {
      setStatus('📍 Could not get GPS — tap the map to place the marker manually');
    }
  }, [demoSwitch, positionError]);

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
              if (endPoint && !startPoint) {
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
        setStatus('Calculating path...');
        setLoading(true);

        try {
          const response = await axios.post(`${API_URL}/path`, {
            source: { lat, lng },
            target: { lat: endPoint[0], lng: endPoint[1] }
          });

          const data = response.data;

          if (data.path && data.path.length > 0) {
            const pathLatLng = data.path.map(coord => [coord[0], coord[1]]);
            pathCoordsRef.current = pathLatLng;
            routeIdRef.current = data.route_id;

            const remainingLine = L.polyline(pathLatLng, {
              color: '#ff4444', weight: 5, opacity: 0.8
            }).addTo(map);
            const traveledLine = L.polyline([], {
              color: '#ff4444', weight: 5, opacity: 0
            }).addTo(map);

            remainingLineRef.current = remainingLine;
            traveledLineRef.current = traveledLine;

            setPath(remainingLine);
            setDistance(data.distance);
            setStats(data);
            setStatus(`✓ Distance: ${data.distance.toFixed(0)}m | Time: ${data.time_ms.toFixed(0)}ms | Nodes visited: ${data.nodes_visited}`);
          } else {
            setStatus('No path found! Try different points.');
          }
        } catch (error) {
          console.error('Error:', error);
          setStatus('Error finding path. Make sure backend is running.');
        } finally {
          setLoading(false);
        }
        return;
      }
        if (!startPoint) {
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
            const response = await axios.post(`${API_URL}/path`, {
              source: { lat: startPoint[0], lng: startPoint[1] },
              target: { lat, lng }
            });

            const data = response.data;

            if (data.path && data.path.length > 0) {
              const pathLatLng = data.path.map(coord => [coord[0], coord[1]]);
              pathCoordsRef.current = pathLatLng;
              routeIdRef.current = data.route_id;

              const remainingLine = L.polyline(pathLatLng, {
                color: '#ff4444', weight: 5, opacity: 0.8
              }).addTo(map);
              const traveledLine = L.polyline([], {
                color: '#ff4444', weight: 5, opacity: 0
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

  function liveFeedbackDemo(){
    const nextOn = !demoSwitch;
    setDemoSwitch(nextOn);

    if (nextOn) {
      // Turning tracking on: ask for GPS now (prompt appears on user action).
      if (isGeolocationAvailable) {
        getPosition();
      } else {
        setStatus('Geolocation not supported — tap the map to place the marker');
      }
      return;
    }

    // Turning tracking off: drop the marker and restore the full route.
    if (posMarkerRef.current) { posMarkerRef.current.remove(); posMarkerRef.current = null; }
    progressPending.current = null;
    if (remainingLineRef.current && pathCoordsRef.current) {
      remainingLineRef.current.setLatLngs(pathCoordsRef.current.map(c => L.latLng(c[0], c[1])));
      remainingLineRef.current.setStyle({ color: '#ff4444' });
    }
    if (traveledLineRef.current) traveledLineRef.current.setLatLngs([]);
  }

  // Manual click-to-place fallback (when GPS is unavailable or out of bounds).
  function handleLiveFeedbackDemo(map, click){
    const ll = click.latlng;
    if (!posMarkerRef.current){
      posMarkerRef.current = makePosMarker(map, ll);
    } else {
      posMarkerRef.current.setLatLng(ll);
    }
    updateProgress(ll);
  }
  const searchProps = {
  L,
  mapRef,
  startPoint,
  endPoint,
  setStartPoint,
  setEndPoint,
  setStatus,
  setLoading,
  setPath,
  setDistance,
  setStats,
  pathCoordsRef,
  routeIdRef,
  remainingLineRef,
  traveledLineRef,
  markersRef,
  placeholder: "Search building...",
  style: { width: '200px' }
  };
  return (
    <div style={{ height: '100vh', width: '100%', position: 'relative' }}>
      <MapContainer
        center={[55.7858, 12.5215]}
        zoom={16}
        style={{ height: '100%', width: '100%' }}
        zoomControl={true}
        attributionControl={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        <WMSTileLayer
          url="https://casgis.azurewebsites.net/geoserver/dtu/wms"
          layers="dtu:llyn_bygning_dtu"
          format="image/png"
          transparent={true}
          version="1.1.1"
          attribution="DTU GeoServer"
        />

        <MapRefBinder mapRef={mapRef} />
        <MapClickHandler />
      </MapContainer>
      <div style={{
        position: 'absolute', top: 20, left: 20, right: 20,
        background: loading ? 'rgba(255,255,255,0.9)' : 'white',
        padding: loading ? '8px 12px' : '12px',
        borderRadius: 10, boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
        zIndex: 1000, fontSize: loading ? '12px' : '14px',
        textAlign: 'center', transition: 'all 0.3s ease'
      }}>
        {!loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' , flexWrap: 'wrap'}}>
            <span>search</span>
              <SearchField {...searchProps} />
            <Switch onChange={liveFeedbackDemo} checked={demoSwitch} />
            <span>location</span>
          </div>
        )}
      </div>
      <div style={{
        position: 'absolute', bottom: 20, left: 20, right: 20,
        background: loading ? 'rgba(255,255,255,0.9)' : 'white',
        padding: loading ? '8px 12px' : '12px',
        borderRadius: 10, boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
        zIndex: 1000, fontSize: loading ? '12px' : '14px',
        textAlign: 'center', transition: 'all 0.3s ease'
      }}>
        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
            <div className="spinner" style={{
              width: '16px', height: '16px', border: '2px solid #ccc',
              borderTopColor: '#ff4444', borderRadius: '50%',
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

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default App;