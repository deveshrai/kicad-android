#!/usr/bin/env python3
"""Place the 555 blinker footprints, add the outline and GND zones.

Input is the .kicad_pcb the Android app wrote after "Update PCB from Schematic"; the result is
pushed back and opened in the app. Coordinates are board-relative mm; the board's top-left
corner sits at ORIGIN on the page.
"""
import sys, os, math, uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../rp2350'))
from sexpr import parse, dump, find, find1, Str

ORIGIN = (100.0, 60.0)
W, H = 64.0, 36.0
RC = 4.0   # corner radius

# ref: (x, y, rotation)   board-relative mm; THT footprints have their origin on pad 1
# Left: the CR2032 holder.  Middle: switch, decoupling, timer, CV cap.  Right: timing
# resistors, LED resistor, timing cap and the LED.
P = {
    'BT1': (4.0, 18.0, 0),
    'SW1': (36.0, 5.0, 0),
    'C3': (37.0, 10.5, 0),
    'U1': (37.0, 14.0, 0),
    'C2': (37.0, 27.5, 0),
    'R1': (50.0, 5.0, 0),
    'R2': (50.0, 10.0, 0),
    'R3': (50.0, 15.0, 0),
    'C1': (50.0, 23.0, 0),
    'D1': (57.0, 24.0, 0),
}

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


def inside_board(b):
    """Box fully inside the rounded-rectangle outline."""
    if b[0] < 0 or b[1] < 0 or b[2] > W or b[3] > H:
        return False
    for cx, cy in ((RC, RC), (W - RC, RC), (RC, H - RC), (W - RC, H - RC)):
        for x, y in ((b[0], b[1]), (b[2], b[1]), (b[0], b[3]), (b[2], b[3])):
            in_corner = (x < RC if cx == RC else x > W - RC) and (y < RC if cy == RC else y > H - RC)
            if in_corner and math.hypot(x - cx, y - cy) > RC:
                return False
    return True


def outline(x0, y0):
    """Edge.Cuts lines and arcs for a W x H board with RC corners."""
    def seg(kind, *pts):
        node = [kind] + [[k, round(px, 4), round(py, 4)] for k, (px, py) in pts]
        return node + [['stroke', ['width', 0.1], ['type', 'default']], ['layer', Str('Edge.Cuts')], ['uuid', uid()]]
    x1, y1 = x0 + W, y0 + H
    d = RC * (1 - math.cos(math.radians(45)))
    return [
        seg('gr_line', ('start', (x0 + RC, y0)), ('end', (x1 - RC, y0))),
        seg('gr_line', ('start', (x1, y0 + RC)), ('end', (x1, y1 - RC))),
        seg('gr_line', ('start', (x1 - RC, y1)), ('end', (x0 + RC, y1))),
        seg('gr_line', ('start', (x0, y1 - RC)), ('end', (x0, y0 + RC))),
        seg('gr_arc', ('start', (x1 - RC, y0)), ('mid', (x1 - d, y0 + d)), ('end', (x1, y0 + RC))),
        seg('gr_arc', ('start', (x1, y1 - RC)), ('mid', (x1 - d, y1 - d)), ('end', (x1 - RC, y1))),
        seg('gr_arc', ('start', (x0 + RC, y1)), ('mid', (x0 + d, y1 - d)), ('end', (x0, y1 - RC))),
        seg('gr_arc', ('start', (x0, y0 + RC)), ('mid', (x0 + d, y0 + d)), ('end', (x0 + RC, y0))),
    ]


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
        old_rot = float(find1(tr, 'rotate')[1])
        find1(tr, 'rotate')[1] = rot
        # Pad angles are stored absolute (footprint rotation included); positions stay local
        for pad in find(fp, 'pad'):
            at = find1(pad, 'at')
            ang = (float(at[3]) if len(at) > 3 else 0.0) - old_rot + rot
            ang = (ang + 180) % 360 - 180
            del at[3:]
            if ang:
                at.append(round(ang, 4))
        b = rotated_box(courtyard(fp), rot)
        boxes[ref] = (x + b[0], y + b[1], x + b[2], y + b[3])

    # Overlap and board-edge check
    problems = 0
    refs = sorted(boxes)
    for i, a in enumerate(refs):
        ba = boxes[a]
        if a not in ('J1',) and not inside_board(ba):
            print(f'outside board: {a} {tuple(round(v, 2) for v in ba)}'); problems += 1
        for b in refs[i + 1:]:
            bb = boxes[b]
            if ba[0] < bb[2] and bb[0] < ba[2] and ba[1] < bb[3] and bb[1] < ba[3]:
                print(f'overlap: {a} {b}'); problems += 1

    # Remove any previous outline/zones from earlier runs, then add ours
    board[:] = [c for c in board if not (isinstance(c, list) and (
        (c[0] in ('gr_rect', 'gr_line', 'gr_arc') and find1(c, 'layer') and find1(c, 'layer')[1] == 'Edge.Cuts')
        or c[0] == 'zone'))]
    x0, y0 = ORIGIN
    board.extend(outline(x0, y0))
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
