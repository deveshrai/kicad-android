#!/usr/bin/env python3
"""Place the ESP32-S3 Uno-format board through KiCad's MCP server (pcb_move_footprint).

The Uno template keeps the shield headers J1-J4 and the mounting holes where an Uno has them.
The module's antenna end overhangs the right edge, so its keepout lies off the board; the USB-B
and DC jack overhang the left edge like an Uno's.  KiCad coordinates, mm, y down.
"""
from mcp_client import KiCad

PLACE = {
    #       x       y       rot
    'U1':  (161.50, 78.00, 270),   # antenna to the right, off the board
    'J6':  (109.30, 62.00, 180),   # USB-B, opening to the left
    'J7':  (110.00, 86.50, 0),     # DC jack, opening to the left
    'J5':  (118.00, 60.00, 90),    # extra IO, 2x8 along the top
    'SW1': (143.00, 58.50, 0),     # RESET
    'SW2': (154.00, 58.50, 0),     # BOOT
    # EN / IO0 parts in one row under the buttons, 0805s turned upright 3 mm apart (any further
    # left and R2 blocks the tracks leaving the module's left-hand pads); their references go
    # above them, see REF_TEXT
    'R2':  (149.50, 66.00, 90),    # IO0 pull-up
    'C6':  (152.50, 66.00, 90),    # EN delay
    'R1':  (155.50, 66.00, 90),    # EN pull-up
    'C5':  (159.50, 66.00, 90),    # 10u at the module's 3V3 pin
    'C4':  (162.50, 66.00, 90),    # 100n at the module's 3V3 pin
    'F1':  (115.50, 66.50, 90),    # USB polyfuse
    'D1':  (115.50, 72.50, 90),    # USB Schottky
    'R3':  (121.00, 66.50, 0),
    'D3':  (126.00, 66.50, 0),     # ON
    'R4':  (121.00, 71.50, 0),
    'D4':  (126.00, 71.50, 0),     # L
    'D2':  (119.00, 84.00, 0),     # DC jack reverse protection
    'C1':  (119.00, 89.00, 0),
    'U2':  (127.00, 85.00, 0),     # 5 V
    'C2':  (133.00, 90.00, 0),
    'U3':  (140.00, 85.00, 0),     # 3.3 V
    'C3':  (140.00, 91.50, 0),
}

RULES = [{
    'name': 'ESP32 module courtyard',
    'comments': 'The module courtyard includes the antenna keepout guideline (24 mm each side), '
                'which an Uno-sized board cannot meet; the antenna overhangs the edge instead.',
    'condition': "A.Reference == 'U1' || B.Reference == 'U1'",
    'constraints': [{'type': 'CRCT_COURTYARD_CLEARANCE'}],
    'severity': 'RS_IGNORE',
}]

# Reference text moved off the parts around the module: (x, y, angle)
REF_TEXT = {'U1': (165.0, 78.0, 90),   # on the module body, between its pad rows
            'R2': (149.5, 63.5, 0), 'C6': (152.5, 63.5, 0), 'R1': (155.5, 63.5, 0),
            'C5': (159.5, 63.5, 0), 'C4': (162.5, 63.5, 0)}


def clear_routing(k, pcb):
    items = k.api('GetItems', header={'document': pcb},
                  types=['KOT_PCB_TRACE', 'KOT_PCB_ARC', 'KOT_PCB_VIA']).get('items', [])
    if items:
        k.api('DeleteItems', header={'document': pcb}, item_ids=[i['id'] for i in items])
    print('removed', len(items), 'tracks and vias')


def move_ref_text(k, pcb):
    fps = k.api('GetItems', header={'document': pcb}, types=['KOT_PCB_FOOTPRINT'])['items']
    for fp in fps:
        ref = fp['reference_field']['text']['text']['text']
        if ref in REF_TEXT:
            x, y, a = REF_TEXT[ref]
            t = fp['reference_field']['text']['text']
            t['position'] = {'x_nm': str(int(x * 1e6)), 'y_nm': str(int(y * 1e6))}
            t['attributes']['angle'] = {'value_degrees': a}
            r = k.api('UpdateItems', header={'document': pcb}, items=[fp])
            print(ref, 'reference text', r.get('updated_items', [{}])[0].get('status'))


if __name__ == '__main__':
    import sys
    k = KiCad()
    pcb = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_PCB'][0]
    if '--clear-routing' in sys.argv:
        clear_routing(k, pcb)
    for ref, (x, y, rot) in PLACE.items():
        r = k.tool('pcb_move_footprint', reference=ref, x=x, y=y, rotation=rot)
        print(f"{ref:4} -> {r['x']:.2f}, {r['y']:.2f} @ {r['rotation']:.0f}")
    move_ref_text(k, pcb)
    print(k.api('SetCustomDesignRules', board=pcb, rules=RULES))
