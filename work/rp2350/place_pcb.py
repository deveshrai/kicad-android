#!/usr/bin/env python3
"""Place the footprints of the app-saved board, add the outline, mounting holes and GND zones.

Input is the .kicad_pcb the Android app wrote after "Update PCB from Schematic"; the result is
pushed back and opened in the app. Coordinates are board-relative mm; the board's top-left
corner sits at ORIGIN on the page.
"""
import sys, os, math, uuid
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, dump, find, find1, Str

ORIGIN = (100.0, 60.0)
W, H = 95.0, 65.0

# ref: (x, y, rotation)   board-relative mm, rotation in degrees (KiCad: CCW on screen)
P = {
    'J1': (4.2, 32.0, 270),
    'R1': (13.0, 25.0, 90), 'R2': (13.0, 39.0, 90),
    'R3': (17.5, 29.5, 0), 'R4': (17.5, 34.5, 0),
    'U2': (13.0, 11.0, 0), 'C1': (7.5, 11.0, 90), 'C2': (18.5, 9.0, 90), 'C3': (18.5, 14.5, 90),
    'SW4': (7.5, 44.5, 0), 'R7': (14.5, 44.5, 90),
    'SW5': (7.5, 53.0, 0), 'R8': (14.5, 53.0, 90),
    'U1': (45.0, 31.0, 0),
    'U3': (29.0, 17.0, 0), 'C19': (29.0, 10.5, 0),
    'Y1': (37.0, 45.0, 0), 'R6': (43.0, 45.0, 90), 'C20': (33.0, 45.0, 90), 'C21': (37.0, 49.0, 0),
    'L1': (56.0, 22.0, 90), 'C13': (55.0, 37.5, 90), 'C14': (58.5, 37.5, 90), 'R5': (58.5, 42.0, 0),
    'C15': (59.5, 22.0, 90),
    'SW1': (63.0, 7.5, 0), 'SW2': (73.0, 7.5, 0), 'SW3': (83.0, 7.5, 0),
    'D1': (67.0, 16.0, 0), 'D2': (73.0, 16.0, 0), 'D3': (79.0, 16.0, 0),
    'R9': (67.0, 19.5, 0), 'R10': (73.0, 19.5, 0), 'R11': (79.0, 19.5, 0),
    'J3': (89.5, 22.0, 0),
    'J2': (21.5, 61.0, 90),
    'H1': (3.5, 3.5, 0), 'H2': (91.5, 3.5, 0), 'H3': (3.5, 61.5, 0), 'H4': (91.5, 61.5, 0),
}
# Decoupling caps in a ring around U1 (QFN 7x7): IOVDD x6, QSPI_IOVDD, USB_OTP_VDD, ADC_AVDD, DVDD x3
ring = ['C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'C10', 'C11', 'C12', 'C16', 'C17', 'C18']
ux, uy = P['U1'][0], P['U1'][1]
spots = [(-6.5, -3), (-6.5, 0), (-6.5, 3), (-3, 6.5), (0, 6.5), (3, 6.5),
         (6.5, 3), (6.5, 0), (6.5, -3), (3, -6.5), (0, -6.5), (-3, -6.5)]
for ref, (dx, dy) in zip(ring, spots):
    P[ref] = (ux + dx, uy + dy, 90 if abs(dx) > abs(dy) else 0)


def uid():
    return Str(str(uuid.uuid4()))


def courtyard(fp):
    """Local courtyard bounding box (front or back)."""
    xs, ys = [], []
    for g in fp:
        if not isinstance(g, list) or not g[0].startswith('fp_'):
            continue
        layer = find1(g, 'layer')
        if not layer or 'CrtYd' not in layer[1]:
            continue
        for key in ('start', 'end', 'center', 'mid'):
            n = find1(g, key)
            if n:
                xs.append(float(n[1])); ys.append(float(n[2]))
        pts = find1(g, 'pts')
        if pts:
            for xy in find(pts, 'xy'):
                xs.append(float(xy[1])); ys.append(float(xy[2]))
        if g[0] == 'fp_circle':
            c, e = find1(g, 'center'), find1(g, 'end')
            r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
            xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
    if not xs:
        return (-0.5, -0.5, 0.5, 0.5)
    return (min(xs), min(ys), max(xs), max(ys))


def rotated_box(box, rot):
    x0, y0, x1, y1 = box
    a = math.radians(rot)
    pts = []
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        # KiCad rotation is CCW on screen with y pointing down
        pts.append((x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)))
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def main(src, dst):
    board = parse(open(src).read())
    boxes = {}
    for fp in find(board, 'footprint'):
        ref = next(str(p[2]) for p in find(fp, 'property') if p[1] == 'Reference')
        if ref not in P:
            print('unplaced', ref)
            continue
        x, y, rot = P[ref]
        tr = find1(fp, 'transform')
        find1(tr, 'translate')[1:3] = [round(ORIGIN[0] + x, 4), round(ORIGIN[1] + y, 4)]
        find1(tr, 'rotate')[1] = rot
        b = rotated_box(courtyard(fp), rot)
        boxes[ref] = (x + b[0], y + b[1], x + b[2], y + b[3])

    # Overlap and board-edge check
    problems = 0
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        ba = boxes[a]
        if a not in ('J1',) and (ba[0] < 0 or ba[1] < 0 or ba[2] > W or ba[3] > H):
            print(f'outside board: {a} {tuple(round(v, 2) for v in ba)}'); problems += 1
        for b in refs[i + 1:]:
            bb = boxes[b]
            if ba[0] < bb[2] and bb[0] < ba[2] and ba[1] < bb[3] and bb[1] < ba[3]:
                print(f'overlap: {a} {b}'); problems += 1

    # Remove any previous outline/zones from earlier runs, then add ours
    board[:] = [c for c in board if not (isinstance(c, list) and (
        (c[0] == 'gr_rect' and find1(c, 'layer') and find1(c, 'layer')[1] == 'Edge.Cuts') or c[0] == 'zone'))]
    x0, y0 = ORIGIN
    board.append(['gr_rect', ['start', x0, y0], ['end', x0 + W, y0 + H],
                  ['stroke', ['width', 0.1], ['type', 'default']], ['fill', 'no'],
                  ['layer', Str('Edge.Cuts')], ['uuid', uid()]])
    for layer in ('F.Cu', 'B.Cu'):
        board.append(['zone', ['net', Str('GND')], ['layer', Str(layer)], ['uuid', uid()],
                      ['hatch', 'edge', 0.5], ['connect_pads', ['clearance', 0.3]],
                      ['min_thickness', 0.2], ['filled_areas_thickness', 'no'],
                      ['fill', ['thermal_gap', 0.4], ['thermal_bridge_width', 0.4]],
                      ['polygon', ['pts', ['xy', x0 + 0.5, y0 + 0.5], ['xy', x0 + W - 0.5, y0 + 0.5],
                                   ['xy', x0 + W - 0.5, y0 + H - 0.5], ['xy', x0 + 0.5, y0 + H - 0.5]]]])
    open(dst, 'w').write(dump(board) + '\n')
    print(f'placed {len(boxes)} footprints, {problems} problems -> {dst}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
