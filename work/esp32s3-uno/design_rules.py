#!/usr/bin/env python3
"""Board design rules for the ESP32-S3 Uno-format board, through KiCad's MCP server.

The module footprint has 0.2 mm thermal vias under its ground pad, so the minimum through-hole
drill comes down to 0.2 mm, and the minimum track to 0.15 mm for the neck-downs at the module's
pads (both well inside what common 2-layer fabs make). The track and via sizes
match the net classes, so they are offered in the board editor's track and via lists.
"""
import json
from mcp_client import KiCad

k = KiCad()
pcb = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_PCB'][0]
nm = lambda mm: {'value_nm': str(int(round(mm * 1e6)))}

rules = k.api('GetBoardDesignRules', board=pcb)['rules']
rules['constraints']['min_through_drill'] = nm(0.2)
# The router necks tracks down to ~0.19 mm where they leave the module's 1.27 mm-pitch pads
rules['constraints']['min_track_width'] = nm(0.15)
rules['predefined_sizes'] = {
    'tracks': [{'width': nm(w)} for w in (0.25, 0.3, 0.5, 0.6, 0.8)],
    'vias': [{'diameter': nm(d), 'drill': nm(h)} for d, h in ((0.6, 0.3), (0.8, 0.4))],
}
# Leave out severities without a rule type; they cannot be set back
rules['severities'] = [s for s in rules['severities'] if 'rule_type' in s]
print(k.api('SetBoardDesignRules', board=pcb, rules=rules))
c = k.api('GetBoardDesignRules', board=pcb)['rules']
print('min_through_drill', int(c['constraints']['min_through_drill']['value_nm']) / 1e6, 'mm;',
      'tracks', [int(t['width']['value_nm']) / 1e6 for t in c['predefined_sizes']['tracks']])
