import folium
import json
from branca.element import IFrame

# Load the layers from JSON file
with open('layers_list.json', 'r') as f:
    layers_data = json.load(f)

# Base URL for the GeoServer WMS service
base_url = "https://casgis.azurewebsites.net/geoserver/dtu/wms"

# Center coordinates for DTU area (approximate)
center_lat = 55.7858
center_lon = 12.5215

# Create a base map
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    control_scale=True
)

# Add OpenStreetMap as base layer
folium.TileLayer(
    tiles='OpenStreetMap',
    name='OpenStreetMap',
    attr='OpenStreetMap'
).add_to(m)

# Add each layer from the GeoServer
for layer in layers_data:
    layer_name = layer['full_name']
    layer_title = layer['title']
    
    # Create WMS layer
    wms_layer = folium.WmsTileLayer(
        url=base_url,
        name=layer_title,
        layers=layer_name,
        fmt='image/png',
        transparent=True,
        version='1.1.1',
        attr=f'GeoServer - {layer_title}',
        overlay=True,
        control=True
    )
    
    wms_layer.add_to(m)

# Add layer control to toggle layers on/off
folium.LayerControl(collapsed=False).add_to(m)

# Save the map
m.save('dtu_layers_map.html')

print(f"Map created with {len(layers_data)} layers")
print("Open 'dtu_layers_map.html' in your web browser to view")