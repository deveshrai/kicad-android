#!/usr/bin/env python3
"""Turn the scripted design (gen_sch.py) into a plan for building it by hand in the app:
the parts to place through the symbol chooser, and one net label per pin endpoint, placed
through the label dialog. Power nets are labels too (GND, +3V3, ...), plus PWR_FLAGs.

Writes app_plan.json: {"parts": [...], "labels": [...]}, coordinates in mm (schematic, y down).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'gen_sch.py')).read()
head, design = src.split('# ---------------------------------------------------------------- the design')
design = design.split('# ---------------------------------------------------------------- write')[0]

g = {'__file__': os.path.join(HERE, 'gen_sch.py'), '__name__': 'plan'}
exec(head, g)

parts, labels, ncs = [], [], []
orig_place = g['place']


def place(lib_id, ref, value, x, y, footprint='', unit=1, in_bom=True, on_board=True):
    inst = orig_place(lib_id, ref, value, x, y, footprint, unit, in_bom, on_board)
    if not ref.startswith('#PWR'):
        parts.append({'lib_id': lib_id, 'ref': ref, 'value': value, 'x': x, 'y': y,
                      'footprint': footprint or g['lib_prop'](lib_id, 'Footprint')})
    return inst


def connect(inst, num, net, stub=2.54):
    seen = set()
    for ex, ey, d in g['endpoints'](inst, num):
        key = (round(ex, 3), round(ey, 3))
        if key in seen:
            continue
        seen.add(key)
        if net is None:
            ncs.append({'x': ex, 'y': ey, 'ref': inst['ref'], 'pin': num})
        else:
            labels.append({'net': net, 'x': ex, 'y': ey, 'dir': d, 'ref': inst['ref'], 'pin': num})


def power(net, x, y, d):
    # PWR_FLAG: a part whose single pin gets a label for the flagged net
    pass


g['place'] = place
g['connect'] = connect
g['power'] = power
exec(design.split('# Power flags')[0], g)

# Power flags, one per net without a power-output driver: place the flag, label its pin
for i, net in enumerate(('GND', 'VBUS', '+1V1', 'VREG_AVDD')):
    x, y = 30.48 + i * 15.24, 254.0
    inst = place('power:PWR_FLAG', f'#FLG0{i + 1}', 'PWR_FLAG', x, y)
    connect(inst, '1', net)

# Placement order: switches renumbered so auto-annotation (order of placement) matches
sw = [p for p in parts if p['ref'] in ('SW1', 'SW2', 'SW3')]
rest = [p for p in parts if p not in sw]
i = next(k for k, p in enumerate(rest) if p['ref'] == 'R7')
parts = rest[:i] + sw + rest[i:]
json.dump({'parts': parts, 'labels': labels, 'no_connects': ncs},
          open(os.path.join(HERE, 'app_plan.json'), 'w'), indent=1)
print(f'{len(parts)} parts, {len(labels)} labels, {len(ncs)} no-connects')
xs = [l['x'] for l in labels] + [p['x'] for p in parts]
ys = [l['y'] for l in labels] + [p['y'] for p in parts]
print('extent x', min(xs), max(xs), 'y', min(ys), max(ys))
