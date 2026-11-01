#!/usr/bin/env python3
"""Drive eeschema on the tablet over adb to build app_plan.json by hand, like a user with a
keyboard: the cursor is moved with the arrow keys (one 50 mil grid step each, exact) and
Return clicks at the cursor. Symbols come from the chooser (A), labels from the label dialog (L).

Usage: app_drive.py STATE_X STATE_Y {parts|labels|ncs|all} [start_index]
  STATE_X/Y: the current cursor position in mils (read it from the status bar once).
The cursor position is tracked in cursor.json between runs.
"""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SERIAL = 'R5GL8486SDD'
GRID = 50                  # mils
STATE = os.path.join(HERE, 'cursor.json')
SHOTS = os.path.join(HERE, 'drive-shots')
os.makedirs(SHOTS, exist_ok=True)

plan = json.load(open(os.path.join(HERE, 'app_plan.json')))


def mils(mm):
    v = mm / 0.0254
    r = round(v / GRID) * GRID
    assert abs(v - r) < 0.5, (mm, v)
    return int(r)


def sh(cmd):
    subprocess.run(['adb', '-s', SERIAL, 'shell', cmd], check=True)


def shot(name):
    with open(os.path.join(SHOTS, name + '.png'), 'wb') as f:
        subprocess.run(['adb', '-s', SERIAL, 'exec-out', 'screencap', '-p'], stdout=f, check=True)


class Cursor:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def save(self):
        json.dump({'x': self.x, 'y': self.y}, open(STATE, 'w'))

    def keys_to(self, x, y):
        dx, dy = (x - self.x) // GRID, (y - self.y) // GRID
        assert (x - self.x) % GRID == 0 and (y - self.y) % GRID == 0
        keys = (['22'] * dx if dx > 0 else ['21'] * -dx) + (['20'] * dy if dy > 0 else ['19'] * -dy)
        self.x, self.y = x, y
        self.save()
        return keys


def keyevents(keys, chunk=60):
    """Arrow-key strings for a shell command (chunked so each input call stays short)."""
    out = []
    for i in range(0, len(keys), chunk):
        out.append('input keyevent ' + ' '.join(keys[i:i + chunk]))
    return out


def text_arg(s):
    return "'" + s.replace(' ', '%s').replace("'", '') + "'"


def run(cmds):
    sh('; '.join(cmds))


# Label orientation: R rotates the floating label 90 degrees CCW (right -> up -> left -> down)
ORDER = [0, 90, 180, 270]
orient = {'v': 0}


def rotate_to(d):
    n = (ORDER.index(d) - ORDER.index(orient['v'])) % 4
    orient['v'] = d
    return ['input keyevent 46'] * n          # KEYCODE_R


def place_part(cur, p):
    name = p['lib_id'].split(':')[1]
    x, y = mils(p['x']), mils(p['y'])
    # No taps anywhere: KiCad re-reads the pointer after the chooser closes, and a tap would
    # move it. The chooser keeps its last search, so select-all first; Tab+Enter picks the
    # highlighted best match (Enter in the search box itself doesn't).
    run(keyevents(cur.keys_to(x, y)) + [
        'input keyevent 29', 'sleep 2.5',                       # A: chooser
        'input keycombination 113 29', f'input text {text_arg(name)}', 'sleep 2.5',
        'input keyevent 61', 'sleep 0.3', 'input keyevent 66', 'sleep 2',
        'input keyevent 66', 'sleep 1',                         # Return: place at cursor
        'input keyevent 111', 'sleep 0.5'])                     # Escape: end the tool
    if p['value'] and p['value'] != name and not p['ref'].startswith('#'):
        # V: edit the value of the symbol under the cursor
        run(['input keyevent 50', 'sleep 2', 'input keycombination 113 29',
             f'input text {text_arg(p["value"])}', 'input keyevent 66', 'sleep 1'])


def place_labels(cur, labels):
    # L opens the label tool; the first Return clicks at the cursor
    run(['input keyevent 40', 'sleep 1'])
    for i, l in enumerate(labels):
        x, y = mils(l['x']), mils(l['y'])
        cmds = keyevents(cur.keys_to(x, y)) + [
            'input keyevent 66', 'sleep 1.8',                 # click: label dialog
            'input keycombination 113 29',                    # Ctrl+A
            f'input text {text_arg(l["net"])}', 'sleep 0.3',
            'input keyevent 66', 'sleep 1.0'] + rotate_to(l['dir']) + [
            'input keyevent 66', 'sleep 0.5']                 # place
        run(cmds)
        print(f'label {i} {l["net"]} at {x},{y} ({l["ref"]}.{l["pin"]})', flush=True)
    run(['input keyevent 111', 'sleep 0.5'])


def main():
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    x = int(sys.argv[1]) if sys.argv[1] != '-' else st['x']
    y = int(sys.argv[2]) if sys.argv[2] != '-' else st['y']
    cur = Cursor(x, y)
    what = sys.argv[3]
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    end = int(sys.argv[5]) if len(sys.argv) > 5 else None
    if what == 'parts':
        for i, p in enumerate(plan['parts'][start:end], start):
            place_part(cur, p)
            print(f'part {i} {p["ref"]} {p["lib_id"]} {p["value"]}', flush=True)
            if i % 8 == 7:
                shot(f'part{i:02d}')
    elif what == 'labels':
        # one label per connection point; stacked pins share one
        seen, labels = set(), []
        for l in plan['labels']:
            k = (mils(l['x']), mils(l['y']))
            if k not in seen:
                seen.add(k)
                labels.append(l)
        sel = labels[start:end]
        for j in range(0, len(sel), 20):
            place_labels(cur, sel[j:j + 20])
            shot(f'labels{start + j:03d}')
    elif what == 'ncs':
        for n in plan['no_connects']:
            run(keyevents(cur.keys_to(mils(n['x']), mils(n['y']))) + ['input keyevent 45', 'sleep 1',
                                                                       'input keyevent 66', 'sleep 0.5',
                                                                       'input keyevent 111'])
    print('cursor', cur.x, cur.y)


if __name__ == '__main__':
    main()
