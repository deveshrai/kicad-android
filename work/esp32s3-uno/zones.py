#!/usr/bin/env python3
"""GND pours on both copper layers of the ESP32-S3 Uno-format board, through KiCad's MCP server.

Each zone is a rectangle over the whole board; the fill is clipped to the Uno outline.  The
module's antenna overhangs the right edge, so no copper reaches under it.  Run after routing:
pcb_autoroute and the zone fill then see the final tracks.
"""
import json
from mcp_client import KiCad

k = KiCad()
pcb = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_PCB'][0]
nm = lambda mm: str(int(round(mm * 1e6)))
D = lambda mm: {'value_nm': nm(mm)}
gnd = [n for n in k.api('GetNets', board=pcb)['nets'] if n.get('name') == 'GND'][0]

X0, Y0, X1, Y1 = 99.0, 46.0, 170.0, 101.0     # covers the outline (100-168.6 x 46.7-99.2)
outline = {'polygons': [{'outline': {'closed': True, 'nodes': [
    {'point': {'x_nm': nm(x), 'y_nm': nm(y)}} for x, y in
    ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1))]}}]}

# Remove zones from an earlier run so the script can be repeated
old = k.api('GetItems', header={'document': pcb}, types=['KOT_PCB_ZONE']).get('items', [])
if old:
    k.api('DeleteItems', header={'document': pcb}, item_ids=[z['id'] for z in old])

zones = []
for layer, name in (('BL_F_Cu', 'GND top'), ('BL_B_Cu', 'GND bottom')):
    zones.append({
        '@type': 'type.googleapis.com/kiapi.board.types.Zone',
        'type': 'ZT_COPPER', 'name': name, 'layers': [layer], 'outline': outline,
        'copper_settings': {
            'net': gnd,
            'connection': {'zone_connection': 'ZCS_THERMAL'},
            'clearance': D(0.3), 'min_thickness': D(0.25),
            'island_mode': 'IRM_ALWAYS', 'fill_mode': 'ZFM_SOLID',
        },
    })
r = k.api('CreateItems', header={'document': pcb}, items=zones)
print([s.get('status') for s in r.get('created_items', [])])
print(k.api('RefillZones', board=pcb))
