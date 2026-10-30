"""Build local Light/Dark app tiles from the bundled service marks; no network."""
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ICONS = ROOT / 'app/assets/icons'
# Top/bottom background and foreground for each mode. Brand paths retain their licences.
PALETTES = {
    'stremio': ('#9570ff', '#4f25d9', '#ffffff', '#af8aff'),
    'netflix': ('#15171c', '#08090c', '#e50914', '#e50914'),
    'disneyplus': ('#062451', '#057ea9', '#ffffff', '#79ddff'),
    'youtube': ('#ffffff', '#f1f1f4', '#ff0033', '#ff0033'),
    'appletv': ('#292929', '#080808', '#ffffff', '#ffffff'),
    'primevideo': ('#079fff', '#0060df', '#ffffff', '#079fff'),
    'abciview': ('#08abbb', '#00788f', '#ffffff', '#23d8e6'),
    'sbs': ('#23252c', '#101115', '#ffffff', '#f5f5f7'),
    'applemusic': ('#ff626e', '#ee2447', '#ffffff', '#ff4869'),
    'spotify': ('#24d269', '#139b47', '#07160b', '#1ed760'),
    'hbomax': ('#5033ba', '#27146b', '#ffffff', '#c8baff'),
    'tubi': ('#fff34a', '#e2d512', '#111111', '#fff34a'),
    'appstore': ('#10c7ff', '#0066f5', '#ffffff', '#099fff'),
    'aquaplay': ('#16e8db', '#0754f2', '#ffffff', '#11dae7'),
}

def tile(brand, mode, palette):
    source = ET.fromstring((ICONS / (brand + '.svg')).read_text())
    fg = palette[2] if mode == 'light' else palette[3]
    for node in source.iter():
        if 'fill' in node.attrib and node.attrib['fill'] != 'none': node.set('fill', fg)
        if 'stroke' in node.attrib and node.attrib['stroke'] != 'none': node.set('stroke', fg)
        if node.tag.endswith('title'): node.text = brand
    if source.get('fill') != 'none':
        source.set('fill', fg)
    source.set('x', '12'); source.set('y', '12'); source.set('width', '40'); source.set('height', '40')
    # Large wordmarks need a wider viewport; other glyphs remain optically balanced.
    if brand in ['appletv', 'disneyplus', 'hbomax', 'primevideo', 'tubi']:
        source.set('x', '8'); source.set('width', '48')
    if brand == 'youtube':
        # Put a white play triangle behind the path's cutout in both tile modes.
        back = ET.Element('{http://www.w3.org/2000/svg}rect', {'x':'9','y':'8','width':'8','height':'8','fill':'#ffffff'})
        source.insert(0, back)
    top, bottom = palette[:2] if mode == 'light' else ('#202329', '#07090d')
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<title>' + brand + ' — ' + mode + '</title><defs><linearGradient id="tile" x2="0" y2="1">'
            '<stop stop-color="' + top + '"/><stop offset="1" stop-color="' + bottom + '"/>'
            '</linearGradient></defs><rect x=".5" y=".5" width="63" height="63" rx="14" fill="url(#tile)" '
            'stroke="#ffffff" stroke-opacity=".10"/>' + ET.tostring(source, encoding='unicode') + '</svg>\n')

for mode in ['light', 'dark']:
    destination = ICONS / mode
    destination.mkdir(exist_ok=True)
    for brand, palette in PALETTES.items():
        (destination / (brand + '.svg')).write_text(tile(brand, mode, palette))
print('Generated 28 app tiles from bundled SVG marks.')
