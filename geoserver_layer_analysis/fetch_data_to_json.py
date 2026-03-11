import requests
import json
import xml.etree.ElementTree as ET

# GeoServer REST API URL
geoserver_url = "https://casgis.azurewebsites.net/geoserver/dtu/wms"
workspace = "dtu"

def get_layers_from_geoserver():
    """Fetch all available layers from the GeoServer using WMS GetCapabilities"""
    
    # Request the WMS capabilities document
    params = {
        'service': 'WMS',
        'version': '1.1.1',
        'request': 'GetCapabilities'
    }
    
    try:
        response = requests.get(geoserver_url, params=params)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Define namespace
        namespaces = {
            'wms': 'http://www.opengis.net/wms',
            'xlink': 'http://www.w3.org/1999/xlink'
        }
        
        layers = []
        
        # Find all Layer elements
        for layer in root.findall('.//wms:Layer', namespaces):
            # Get layer name
            name_elem = layer.find('wms:Name', namespaces)
            if name_elem is not None and name_elem.text:
                layer_name = name_elem.text
                
                # Only include layers from the dtu workspace
                if layer_name.startswith(f"{workspace}:"):
                    # Get layer title
                    title_elem = layer.find('wms:Title', namespaces)
                    layer_title = title_elem.text if title_elem is not None else layer_name
                    
                    # Get layer abstract if available
                    abstract_elem = layer.find('wms:Abstract', namespaces)
                    layer_abstract = abstract_elem.text if abstract_elem is not None else ""
                    
                    # Get bounding box
                    bbox = layer.find('wms:LatLonBoundingBox', namespaces)
                    bbox_info = {}
                    if bbox is not None:
                        bbox_info = {
                            'minx': bbox.get('minx'),
                            'miny': bbox.get('miny'),
                            'maxx': bbox.get('maxx'),
                            'maxy': bbox.get('maxy')
                        }
                    
                    # Get CRS/SRS information
                    crs_list = []
                    for crs in layer.findall('wms:CRS', namespaces):
                        if crs.text:
                            crs_list.append(crs.text)
                    
                    # Create layer info object
                    layer_info = {
                        'name': layer_name.split(':')[-1] if ':' in layer_name else layer_name,
                        'full_name': layer_name,
                        'title': layer_title,
                        'abstract': layer_abstract,
                        'workspace': workspace,
                        'bbox': bbox_info,
                        'crs': crs_list
                    }
                    
                    layers.append(layer_info)
        
        return layers
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching capabilities: {e}")
        return None
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return None

def save_layers_to_json(layers, filename='geoserver_layers.json'):
    """Save layer information to a JSON file"""
    
    if layers:
        # Sort layers by name for consistency
        layers.sort(key=lambda x: x['name'])
        
        # Save to JSON file with nice formatting
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(layers, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Successfully saved {len(layers)} layers to {filename}")
        return True
    else:
        print("✗ No layers to save")
        return False

def create_simplified_layer_list(layers, filename='layers_list_simple.json'):
    """Create a simplified version with just name, full_name, and title"""
    
    simplified_layers = []
    for layer in layers:
        simplified_layers.append({
            'name': layer['name'],
            'full_name': layer['full_name'],
            'title': layer['title']
        })
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(simplified_layers, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully saved simplified list to {filename}")

def create_categorized_layers_json(layers, filename='layers_categorized.json'):
    """Create a categorized version of the layers"""
    
    categories = {
        'buildings': [],
        'parking': [],
        'infrastructure': [],
        'green_areas': [],
        'water_sewage': [],
        'electricity': [],
        'telecom': [],
        'gas': [],
        'thermal': [],
        'construction': [],
        'ler_ledninger': [],
        'ler2_ledninger': [],
        'lerext_ledninger': [],
        'llyn': [],
        'other': []
    }
    
    keywords = {
        'buildings': ['bygning', 'building'],
        'parking': ['parkering', 'parking'],
        'infrastructure': ['bro', 'cykel', 'vej', 'letbane', 'mobilitet', 'fortov', 'adgangsvej'],
        'green_areas': ['have', 'graes', 'trae', 'parker', 'facade', 'torv'],
        'water_sewage': ['vand', 'afloeb', 'brandhane'],
        'electricity': ['el', 'belysning'],
        'telecom': ['tele'],
        'gas': ['gas'],
        'thermal': ['termisk'],
        'construction': ['byggefelt', 'byggeplads'],
        'ler_ledninger': ['ler_', 'ledning'],
        'ler2_ledninger': ['ler2_'],
        'lerext_ledninger': ['lerext_'],
        'llyn': ['llyn_']
    }
    
    for layer in layers:
        name = layer['name'].lower()
        title = layer['title'].lower()
        full_name = layer['full_name'].lower()
        
        categorized = False
        
        # Check each category
        for category, cat_keywords in keywords.items():
            for keyword in cat_keywords:
                if keyword in name or keyword in title or keyword in full_name:
                    categories[category].append(layer)
                    categorized = True
                    break
            if categorized:
                break
        
        # If not categorized, put in other
        if not categorized:
            categories['other'].append(layer)
    
    # Remove empty categories
    categories = {k: v for k, v in categories.items() if v}
    
    # Save categorized layers
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(categories, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully saved categorized layers to {filename}")
    
    # Print summary
    print("\n📊 Layer count by category:")
    for category, cat_layers in categories.items():
        print(f"  {category}: {len(cat_layers)} layers")

def main():
    print("🔍 Fetching layers from GeoServer...")
    print(f"URL: {geoserver_url}")
    print("-" * 50)
    
    # Fetch layers from GeoServer
    layers = get_layers_from_geoserver()
    
    if layers:
        print(f"✅ Found {len(layers)} layers from {workspace} workspace")
        print("-" * 50)
        
        # Save full version with all metadata
        save_layers_to_json(layers, 'geoserver_layers_complete.json')
        
        # Save simplified version
        create_simplified_layer_list(layers, 'layers_list.json')
        
        # Save categorized version
        create_categorized_layers_json(layers, 'layers_categorized.json')
        
        # Print first few layers as preview
        print("\n📋 Preview of first 5 layers:")
        for i, layer in enumerate(layers[:5], 1):
            print(f"  {i}. {layer['name']} - {layer['title']}")
        
        print("\n✨ Done! JSON files created:")
        print("  1. geoserver_layers_complete.json - Full metadata")
        print("  2. layers_list.json - Simplified list")
        print("  3. layers_categorized.json - Categorized by type")
        
    else:
        print("❌ Failed to fetch layers from GeoServer")

if __name__ == "__main__":
    main()