#!/usr/bin/env python3
"""Net classes for the ESP32-S3 Uno-format board, set through KiCad's MCP server."""
from mcp_client import KiCad
import json

k = KiCad()
st = k.tool('kicad_status')
# The project specifier must carry the path exactly as KiCad holds it (with the trailing slash)
PRJ = [d for d in st['open_documents'] if d['type'] == 'DOCTYPE_SCHEMATIC'][0]['project']
D = lambda mm: {'value_nm': int(round(mm * 1e6))}
C = lambda r, g, b: {'r': r / 255, 'g': g / 255, 'b': b / 255, 'a': 1.0}

# Widths for 1 oz copper on a 2-layer 1.6 mm board (IPC-2221, outer layers, 10 degC rise):
# 0.8 mm carries ~2 A, 0.6 mm ~1.5 A, 0.25 mm ~0.7 A.
CLASSES = [
    # name,      track, clearance, via (dia, drill), colour, nets (patterns)
    ('Power_In', 0.80, 0.30, (0.8, 0.4), C(230, 40, 40),   # 7-12 V jack and USB VBUS, up to 1 A
     ['VBUS', '/VBUS_F', '/VIN', '/VIN_RAW']),
    ('Power',    0.60, 0.25, (0.8, 0.4), C(240, 110, 60),  # regulated rails; ESP32-S3 peaks ~0.5 A
     ['+5V', '+3V3']),
    ('GND',      0.50, 0.20, (0.8, 0.4), C(110, 110, 230), ['GND']),  # mostly carried by zones
    ('USB',      0.30, 0.20, (0.6, 0.3), C(60, 140, 230),  # full-speed USB, routed as a pair
     ['/USB_D+', '/USB_D-']),
    ('Analog',   0.25, 0.30, (0.6, 0.3), C(80, 200, 120),  # extra clearance against coupling
     ['/A0', '/A1', '/A2', '/A3']),
    ('Digital',  0.25, 0.20, (0.6, 0.3), C(240, 180, 60), ['/D*']),
    ('I2C',      0.25, 0.20, (0.6, 0.3), C(180, 110, 220), ['/SDA', '/SCL']),
    ('UART',     0.25, 0.20, (0.6, 0.3), C(60, 200, 200), ['/TX', '/RX']),
    ('GPIO',     0.25, 0.20, (0.6, 0.3), C(170, 170, 170), ['/IO18', '/IO3*', '/IO4*']),
    ('Control',  0.25, 0.20, (0.6, 0.3), C(240, 120, 180), ['/EN', '/IO0', '/PWR_LED', '/L_LED']),
]

classes = []
for i, (name, track, clear, (via, drill), colour, _) in enumerate(CLASSES):
    nc = {'name': name, 'priority': i + 1, 'type': 'NCT_EXPLICIT',
          'board': {'track_width': D(track), 'clearance': D(clear), 'color': colour,
                    'via_stack': {'copper_layers': [{'layer': 'BL_F_Cu', 'shape': 'PSS_CIRCLE',
                                  'size': {'x_nm': D(via)['value_nm'], 'y_nm': D(via)['value_nm']}}],
                                  'drill': {'diameter': {'x_nm': D(drill)['value_nm'],
                                                         'y_nm': D(drill)['value_nm']}}}}}
    if name == 'USB':
        nc['board'].update({'diff_pair_track_width': D(0.3), 'diff_pair_gap': D(0.2)})
    classes.append(nc)

# Keep Default, replace the rest (the earlier run had a single Power class)
default = [nc for nc in k.api('GetNetClasses', project=PRJ)['net_classes'] if nc['name'] == 'Default']
print(k.api('SetNetClasses', project=PRJ, net_classes=default + classes, merge_mode='MMM_REPLACE'))
patterns = [{'pattern': p, 'netclass': name} for name, *_, nets in CLASSES for p in nets]
print(k.api('SetNetClassAssignments', project=PRJ, pattern_assignments=patterns,
            merge_mode='MMM_REPLACE'))
got = k.api('GetNetClasses', project=PRJ)
for nc in got.get('net_classes', []):
    b = nc.get('board', {})
    print(f"{nc['name']:8} track {int(b.get('track_width', {}).get('value_nm', 0))/1e6:.2f}  "
          f"clearance {int(b.get('clearance', {}).get('value_nm', 0))/1e6:.2f}  "
          f"via {int(b.get('via_stack', {}).get('copper_layers', [{}])[0].get('size', {}).get('x_nm', 0))/1e6:.2f}")
