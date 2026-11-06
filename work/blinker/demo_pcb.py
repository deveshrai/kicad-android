#!/usr/bin/env python3
"""Make the README recording's starting board from the finished one: no tracks, unfilled zones,
and the footprints lined up beside the outline, as if just pulled in from the schematic."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../rp2350'))
from sexpr import parse, dump, find, find1

# ref: page position (mm) to the right of the 64 x 36 mm board at (100, 60), so the board and the
# parts fit a landscape screen together
STAGE = {'BT1': (172, 84), 'SW1': (172, 62), 'U1': (184, 61), 'C3': (196, 62), 'C2': (196, 67),
         'R1': (205, 62), 'R2': (205, 66), 'R3': (205, 70), 'C1': (206, 77), 'D1': (212, 77)}

board = parse(open(sys.argv[1]).read())
board[:] = [c for c in board if not (isinstance(c, list) and c[0] in ('segment', 'via', 'arc'))]
for z in find(board, 'zone'):
    z[:] = [c for c in z if not (isinstance(c, list) and c[0] == 'filled_polygon')]
for fp in find(board, 'footprint'):
    ref = next(str(p[2]) for p in find(fp, 'property') if p[1] == 'Reference')
    find1(find1(fp, 'transform'), 'translate')[1:3] = list(STAGE[ref])
open(sys.argv[2], 'w').write(dump(board) + '\n')
