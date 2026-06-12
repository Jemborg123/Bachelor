import React, { useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://10.110.80.254:5000';

/**
 * Autocomplete box. Its only job is to search and hand the chosen destination
 * back to the parent via onSelectDestination(lat, lng, name) — lat/lng are null
 * when the location has no coordinates, so the parent can message accordingly.
 */
const SearchField = ({ onSelectDestination, placeholder = "Search...", style = {} }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const debounceRef = useRef(null);
  const reqIdRef = useRef(0);          // guards against out-of-order responses
  const containerRef = useRef(null);

  const performSearch = useCallback(async (q) => {
    if (!q) { setSuggestions([]); setShowSuggestions(false); return; }

    const reqId = ++reqIdRef.current;  // only the latest request may update state
    setIsSearching(true);
    try {
      const { data } = await axios.get(`${API_URL}/search`, { params: { q } });
      if (reqId !== reqIdRef.current) return;        // a newer query already fired
      setSuggestions(data.suggestions || []);
      setShowSuggestions(true);
    } catch (err) {
      console.error('Search error:', err);
      if (reqId === reqIdRef.current) setSuggestions([]);
    } finally {
      if (reqId === reqIdRef.current) setIsSearching(false);
    }
  }, []);

  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    setShowSuggestions(false);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => performSearch(value.trim()), 300);
  };

  const handleSelect = (s) => {
    setQuery(s.name);
    setShowSuggestions(false);
    onSelectDestination(s.lat ?? null, s.lng ?? null, s.name);
  };

  const handleClear = () => {
    setQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
  };

  useEffect(() => {
    const onDocClick = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  return (
    <div style={{ position: 'relative', ...style }} ref={containerRef}>
      <input
        value={query}
        onChange={handleChange}
        onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        placeholder={placeholder}
        style={{
          width: '100%', padding: '6px 10px', borderRadius: '4px',
          border: '1px solid #ccc', fontSize: '13px',
          paddingRight: query ? '25px' : '10px'
        }}
      />
      {query && (
        <button
          onClick={handleClear}
          style={{
            position: 'absolute', right: '6px', top: '50%',
            transform: 'translateY(-50%)', background: 'none', border: 'none',
            cursor: 'pointer', fontSize: '12px', color: '#999'
          }}
        >
          ✕
        </button>
      )}
      {isSearching && (
        <div style={{
          position: 'absolute', right: query ? '25px' : '8px', top: '50%',
          transform: 'translateY(-50%)', fontSize: '10px', color: '#999'
        }}>
          ⏳
        </div>
      )}

      {showSuggestions && suggestions.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          background: 'white', border: '1px solid #ddd', borderRadius: '4px',
          marginTop: '4px', maxHeight: '200px', overflowY: 'auto',
          zIndex: 9999, boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
        }}>
          {suggestions.map((s, idx) => (
            <div
              key={idx}
              onClick={() => handleSelect(s)}
              style={{
                padding: '6px 10px', cursor: 'pointer', fontSize: '13px',
                borderBottom: idx < suggestions.length - 1 ? '1px solid #eee' : 'none'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#f0f0f0'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
            >
              {s.name}
              {s.lat == null && (
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