#!/usr/bin/env python3
"""P9 test: import SnapEDA's ESP32-S31-WROOM-1-N16R16V zip through KiCad's MCP server, then use
the part: library status, symbol on the schematic (its Footprint field), footprint on the board,
and a 3D render with its STEP model.  The trial parts are deleted again afterwards."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../esp32s3-uno'))
from mcp_client import KiCad

ZIP = '/storage/emulated/0/Download/ESP32-S31-WROOM-1-N16R16V-KiCad.zip'
k = KiCad()
scope = sys.argv[1] if len(sys.argv) > 1 else 'global'
r = k.tool('kicad_import_library_package', path=ZIP, scope=scope)
print('import', json.dumps(r, indent=1))
SYM, FP = r['symbol_libraries'][0], r['footprint_libraries'][0]

st = k.api('GetLibraryStatuses', types=['LT_SYMBOL', 'LT_FOOTPRINT'], scope='LTS_BOTH')
for s in st.get('statuses', st.get('libraries', [])):
    if SYM in json.dumps(s) or FP in json.dumps(s):
        print('status', s)

docs = {d['type']: d for d in k.tool('kicad_status')['open_documents']}
sch, pcb = docs['DOCTYPE_SCHEMATIC'], docs['DOCTYPE_PCB']

# Symbol: placed off the sheet's used area, footprint field checked, then deleted
p = k.api('PlaceSymbolFromLibrary', header={'document': sch},
          lib_id={'library_nickname': SYM, 'entry_name': 'ESP32-S31-WROOM-1-N16R16V'},
          position={'x_nm': 380000000, 'y_nm': 150000000}, reference='U9')
item = p['item']
print('symbol', item['reference_field']['text']['text'] if 'reference_field' in item else '',
      'footprint field:', item['footprint_field']['text']['text'],
      'pins:', sum(1 for i in item['definition']['items'] if 'Pin' in i['item']['@type']))

# Footprint: placed on the board, pads counted, a render taken, then deleted
f = k.api('PlaceFootprintFromLibrary', header={'document': pcb},
          lib_id={'library_nickname': FP, 'entry_name': 'ESP32-S31-WROOM-1'},
          position={'x_nm': 132000000, 'y_nm': 72000000}, layer='BL_F_Cu')  # over the board, for the render
fp = f.get('item', f)
print('footprint placed; models:', json.dumps(fp.get('definition', {}).get('models', fp.get('models', '?')))[:400])
pads = [i for i in fp.get('definition', {}).get('items', []) if 'Pad' in i.get('@type', '')]
print('pads', len(pads))
L = lambda v: {'x_nm': v, 'y_nm': v, 'z_nm': v}
out = pcb['project']['path'].rstrip('/') + '/s31-render.png'
print(k.api('RunBoardJobExportRender', job_settings={'document': pcb, 'output_path': out},
            format='RF_PNG', quality='RQ_HIGH', background_style='RBS_OPAQUE', width=1600,
            height=1200, side='RS_TOP', zoom=1.0, procedural_textures=True, anti_alias=True,
            post_process=True, light_side_intensity=L(0.5), light_camera_intensity=L(0.3),
            light_side_elevation=60))
if '--keep' not in sys.argv:
    k.api('DeleteItems', header={'document': sch}, item_ids=[item['id']])
    k.api('DeleteItems', header={'document': pcb}, item_ids=[fp['id']])
    print('trial parts deleted')
