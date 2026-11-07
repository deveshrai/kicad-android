#!/usr/bin/env python3
"""Autoroute the board through KiCad's MCP server, then report what is left unrouted.

Copper pours are removed first: the router sees a filled GND pour as copper covering the layer
and routes far worse around it (23 connections left unrouted instead of 0).  zones.py pours them
again after routing.  Pass --keep-routing to leave existing tracks in place.
"""
import json, sys, time
from mcp_client import KiCad
from place_pcb import clear_routing

k = KiCad()
pcb = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_PCB'][0]
zones = k.api('GetItems', header={'document': pcb}, types=['KOT_PCB_ZONE']).get('items', [])
if zones:
    k.api('DeleteItems', header={'document': pcb}, item_ids=[z['id'] for z in zones])
    print('removed', len(zones), 'zones')
if '--keep-routing' not in sys.argv:
    clear_routing(k, pcb)

t = time.time()
r = k.tool('pcb_autoroute', max_passes=100, optimize=True)
print(f'{time.time() - t:.0f} s', json.dumps(r))
