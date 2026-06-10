import React, { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://192.168.0.194:5000';

const SearchField = ({ 
  L,                 // Leaflet ref
  onLocationSelect,  // Callback when location is selected (returns lat, lng, name)
  mapRef,            // Leaflet map reference
  startPoint,        // Current start point
  endPoint,          // Current end point
  setStartPoint,     // Function to set start point
  setEndPoint,       // Function to set end point
  setStatus,         // Function to set status message
  setLoading,        // Function to set loading state
  setPath,           // Function to set path
  setDistance,       // Function to set distance
  setStats,          // Function to set stats
  pathCoordsRef,     // Ref for path coordinates
  routeIdRef,        // Ref for route ID
  remainingLineRef,  // Ref for remaining line
  traveledLineRef,   // Ref for traveled line
  markersRef,        // Ref for markers
  placeholder = "Search...", 
  style = {} 
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef(null);
  const inputRef = useRef(null);

  const performSearch = useCallback(async (searchQuery) => {
    if (!searchQuery || searchQuery.length < 1) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    setIsSearching(true);
    try {
      const response = await axios.get(`${API_URL}/search`, {
        params: { q: searchQuery }
      });
      setSuggestions(response.data.suggestions || []);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Search error:', error);
      setSuggestions([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  const gridToLatLon = async (x, y) => {
    try {
      const response = await axios.post(`${API_URL}/convert-grid-to-latlon`, { x, y });
      return { lat: response.data.lat, lng: response.data.lng };
    } catch (error) {
      console.error('Conversion error:', error);
      return null;
    }
  };

  const handleLocationSelect = async (suggestion) => {
  setQuery(suggestion.name);
  setShowSuggestions(false);
  
  if (!suggestion.coordinates) {
    setStatus(`⚠️ ${suggestion.name} has no coordinates available`);
    return;
  }
  
  // Convert grid to lat/lon first
  try {
    const conversionRes = await axios.post(`${API_URL}/convert-grid-to-latlon`, {
      x: suggestion.coordinates[0],
      y: suggestion.coordinates[1]
    });
    
    const { lat, lng } = conversionRes.data;
    
    // Set as end point
    setEndPoint([lat, lng]);
    
    // Add end marker
    if (markersRef.current.end) markersRef.current.end.remove();
    const endMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'custom-div-icon',
        html: '<div style="background-color: red; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>',
        iconSize: [16, 16]
      })
    }).addTo(mapRef.current);
    markersRef.current.end = endMarker;
    
    mapRef.current.flyTo([lat, lng], 18);
    
    // Check if we have a start point
    if (!startPoint) {
      setStatus(`📍 Destination set to ${suggestion.name}. Now select a starting point by tapping on the map or enabling GPS`);
    } else {
      // Start point exists, calculate path
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
          }).addTo(mapRef.current);
          const traveledLine = L.polyline([], {
            color: '#ff4444', weight: 5, opacity: 0
          }).addTo(mapRef.current);
          
          remainingLineRef.current = remainingLine;
          traveledLineRef.current = traveledLine;
          
          setPath(remainingLine);
          setDistance(data.distance);
          setStats(data);
          setStatus(`✓ Distance: ${data.distance.toFixed(0)}m | Time: ${data.time_ms.toFixed(0)}ms | Nodes visited: ${data.nodes_visited}`);
        } else {
          setStatus('No path found to this location!');
        }
      } catch (error) {
        console.error('Error:', error);
        setStatus('Error finding path');
      } finally {
        setLoading(false);
      }
    }
  } catch (error) {
    console.error('Conversion error:', error);
    setStatus('Error converting coordinates');
  }
};

  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    setShowSuggestions(false);
    
    clearTimeout(searchTimeoutRef.current);
    searchTimeoutRef.current = setTimeout(() => {
      performSearch(value);
    }, 300);
  };

  const handleClear = () => {
    setQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (inputRef.current && !inputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div style={{ position: 'relative', ...style }} ref={inputRef}>
      <input 
        value={query}
        onChange={handleChange}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        placeholder={placeholder}
        style={{
          width: '100%',
          padding: '6px 10px',
          borderRadius: '4px',
          border: '1px solid #ccc',
          fontSize: '13px',
          paddingRight: query ? '25px' : '10px'
        }}
      />
      {query && (
        <button
          onClick={handleClear}
          style={{
            position: 'absolute',
            right: '6px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '12px',
            color: '#999'
          }}
        >
          ✕
        </button>
      )}
      {isSearching && (
        <div style={{
          position: 'absolute',
          right: query ? '25px' : '8px',
          top: '50%',
          transform: 'translateY(-50%)',
          fontSize: '10px',
          color: '#999'
        }}>
          ⏳
        </div>
      )}
      
      {showSuggestions && suggestions.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          right: 0,
          background: 'white',
          border: '1px solid #ddd',
          borderRadius: '4px',
          marginTop: '4px',
          maxHeight: '200px',
          overflowY: 'auto',
          zIndex: 9999,
          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          {suggestions.map((suggestion, idx) => (
            <div
              key={idx}
              onClick={() => handleLocationSelect(suggestion)}
              style={{
                padding: '6px 10px',
                cursor: 'pointer',
                fontSize: '13px',
                borderBottom: idx < suggestions.length - 1 ? '1px solid #eee' : 'none'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#f0f0f0'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
            >
              {suggestion.name}
              {!suggestion.coordinates && (
                <span style={{ fontSize: '10px', color: '#999', marginLeft: '8px' }}>
                  (no coordinates)
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SearchField;