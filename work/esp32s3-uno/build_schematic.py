#!/usr/bin/env python3
"""Draw the ESP32-S3 Uno-format board's schematic in KiCad on the tablet, through KiCad's MCP
server (kicad_api tool, IPC API commands).  Every pin is joined to its net by a label or a power
symbol, so the schematic is a set of blocks around the module.  KiCad shows every step live.

Run with the schematic editor open (kicad_open_editor schematic) on an empty sheet.
"""
import json, sys
from mcp_client import KiCad

k = KiCad()
DOC = [d for d in k.tool('kicad_status')['open_documents'] if d['type'] == 'DOCTYPE_SCHEMATIC'][0]
HDR = {'document': DOC}
nm = lambda mm: int(round(mm * 1e6))

POWER = {'GND': 'GND', '+3V3': '+3V3', '+5V': '+5V', 'VBUS': 'VBUS'}
# Which way a power symbol's body points for each orientation (verified on screen)
GND_ROT = {'down': 'SSO_0', 'up': 'SSO_180', 'right': 'SSO_90', 'left': 'SSO_270'}
SUP_ROT = {'up': 'SSO_0', 'down': 'SSO_180', 'left': 'SSO_90', 'right': 'SSO_270'}
# Pin orientation (direction from the pin's end into the body) -> outward direction
OUTWARD = {'SPO_RIGHT': 'left', 'SPO_LEFT': 'right', 'SPO_UP': 'down', 'SPO_DOWN': 'up'}
SPIN = {'left': 'SLSS_LEFT', 'right': 'SLSS_RIGHT', 'up': 'SLSS_UP', 'down': 'SLSS_BOTTOM'}
ROTATE = {  # symbol orientation applied to a pin direction
    'SSO_0': {'left': 'left', 'right': 'right', 'up': 'up', 'down': 'down'},
}


def clear_sheet():
    items = k.api('GetItems', header=HDR, types=['KOT_SCH_SYMBOL', 'KOT_SCH_LABEL',
                                                 'KOT_SCH_NO_CONNECT', 'KOT_SCH_LINE'])
    ids = [i['id'] if 'id' in i else None for i in items.get('items', [])]
    ids = [{'value': i['value']} if isinstance(i, dict) else None for i in ids]
    ids = [i for i in ids if i]
    if ids:
        k.api('DeleteItems', header=HDR, item_ids=ids)
    print('cleared', len(ids))


def place(lib, ref, x, y, value=None, footprint=None):
    nick, entry = lib.split(':')
    r = k.api('PlaceSymbolFromLibrary', header=HDR,
              lib_id={'library_nickname': nick, 'entry_name': entry},
              position={'x_nm': nm(x), 'y_nm': nm(y)}, reference=ref)
    item = r['item']
    if value or footprint:
        if value:
            item['value_field']['text']['text'] = value
        if footprint:
            item['footprint_field']['text']['text'] = footprint
        u = k.api('UpdateItems', header=HDR, items=[item])
        st = u.get('updated_items', [{}])[0].get('status', {})
        if st and st.get('code') not in (None, 'ISC_OK'):
            print('  update', ref, st)
    pins = {}
    for it in item['definition']['items']:
        p = it['item']
        if 'SchematicPin' not in p['@type']:
            continue
        if it.get('unit', {}).get('unit', 0) not in (0, 1):
            continue
        px = x + int(p['position'].get('x_nm', 0)) / 1e6
        py = y + int(p['position'].get('y_nm', 0)) / 1e6
        pins[p['number']] = (px, py, OUTWARD[p['orientation']], p.get('name', ''))
    print(f'{ref:4} {lib:42} {len(pins)} pins')
    return pins


labels = []


def connect(pins, ref, number, net):
    x, y, out, _ = pins[number]
    if net == 'NC':
        labels.append({'@type': 'type.googleapis.com/kiapi.schematic.types.NoConnectMarker',
                       'position': {'x_nm': nm(x), 'y_nm': nm(y)}})
    elif net in POWER:
        rot = (GND_ROT if net == 'GND' else SUP_ROT)[out]
        k.api('PlaceSymbolFromLibrary', header=HDR,
              lib_id={'library_nickname': 'power', 'entry_name': POWER[net]},
              position={'x_nm': nm(x), 'y_nm': nm(y)}, orientation=rot)
    else:
        labels.append({'@type': 'type.googleapis.com/kiapi.schematic.types.LocalLabel',
                       'position': {'x_nm': nm(x), 'y_nm': nm(y)},
                       'text': {'text': net, 'position': {'x_nm': nm(x), 'y_nm': nm(y)}},
                       'spin_style': SPIN[out]})


def flush_labels():
    global labels
    if labels:
        r = k.api('CreateItems', header=HDR, items=labels)
        bad = [s for s in r.get('created_items', []) if s.get('status', {}).get('code') != 'ISC_OK']
        print('  created', len(labels), 'labels/markers', ('problems: %s' % bad[:2]) if bad else '')
    labels = []


def block(lib, ref, x, y, nets, value=None, footprint=None):
    pins = place(lib, ref, x, y, value, footprint)
    for number, net in nets.items():
        connect(pins, ref, number, net)
    flush_labels()
    return pins


FP_C = 'Capacitor_SMD:C_0805_2012Metric'
FP_R = 'Resistor_SMD:R_0805_2012Metric'
FP_LED = 'LED_SMD:LED_0805_2012Metric'
FP_D = 'Diode_SMD:D_SMA'
FP_SW = 'Button_Switch_SMD:SW_SPST_PTS645Sx43SMTR92'


def main():
    if '--clear' in sys.argv:
        clear_sheet()

    # The module
    block('RF_Module:ESP32-S3-WROOM-1', 'U1', 203.2, 139.7, {
        '1': 'GND', '40': 'GND', '41': 'GND', '2': '+3V3', '3': 'EN', '27': 'IO0',
        '39': 'A0', '38': 'A1', '15': 'A2', '4': 'A3', '12': 'SDA', '17': 'SCL',
        '5': 'D7', '6': 'D6', '7': 'D5', '8': 'D4', '9': 'D3', '10': 'D2',
        '18': 'D10', '19': 'D11', '20': 'D13', '21': 'D12', '22': 'D9', '23': 'D8',
        '37': 'TX', '36': 'RX', '13': 'USB_D-', '14': 'USB_D+',
        '11': 'IO18', '28': 'IO35', '29': 'IO36', '30': 'IO37', '31': 'IO38', '32': 'IO39',
        '33': 'IO40', '34': 'IO41', '35': 'IO42', '26': 'IO45', '16': 'IO46', '24': 'IO47',
        '25': 'IO48'})

    # The Uno shield headers (references and footprints match the Arduino Uno template board)
    sock = 'Connector_PinSocket_2.54mm:PinSocket_1x%02d_P2.54mm_Vertical'
    block('Connector_Generic:Conn_01x08', 'J1', 99.06, 63.5, {
        '1': 'NC', '2': '+3V3', '3': 'EN', '4': '+3V3', '5': '+5V', '6': 'GND', '7': 'GND',
        '8': 'VIN'}, 'Power', sock % 8)
    block('Connector_Generic:Conn_01x06', 'J3', 99.06, 101.6, {
        '1': 'A0', '2': 'A1', '3': 'A2', '4': 'A3', '5': 'SDA', '6': 'SCL'}, 'Analog', sock % 6)
    block('Connector_Generic:Conn_01x10', 'J2', 99.06, 142.24, {
        '1': 'SCL', '2': 'SDA', '3': 'NC', '4': 'GND', '5': 'D13', '6': 'D12', '7': 'D11',
        '8': 'D10', '9': 'D9', '10': 'D8'}, 'Digital/PWM', sock % 10)
    block('Connector_Generic:Conn_01x08', 'J4', 99.06, 185.42, {
        '1': 'D7', '2': 'D6', '3': 'D5', '4': 'D4', '5': 'D3', '6': 'D2', '7': 'TX',
        '8': 'RX'}, 'Digital', sock % 8)
    block('Connector_Generic:Conn_02x08_Odd_Even', 'J5', 299.72, 139.7, {
        '1': '+3V3', '2': 'GND', '3': 'IO0', '4': 'IO18', '5': 'IO35', '6': 'IO36',
        '7': 'IO37', '8': 'IO38', '9': 'IO39', '10': 'IO40', '11': 'IO41', '12': 'IO42',
        '13': 'IO45', '14': 'IO46', '15': 'IO47', '16': 'IO48'}, 'Extra IO',
        'Connector_PinHeader_2.54mm:PinHeader_2x08_P2.54mm_Vertical')

    # Power: USB-B like an Uno, and a DC jack through a 5 V regulator
    block('Connector:USB_B', 'J6', 147.32, 233.68, {
        '1': 'VBUS', '2': 'USB_D-', '3': 'USB_D+', '4': 'GND', 'SH': 'GND'}, 'USB-B',
        'Connector_USB:USB_B_OST_USB-B1HSxx_Horizontal')
    block('Device:Polyfuse', 'F1', 172.72, 226.06, {'1': 'VBUS', '2': 'VBUS_F'}, '500mA',
          'Fuse:Fuse_1206_3216Metric')
    block('Device:D_Schottky', 'D1', 187.96, 220.98, {'2': 'VBUS_F', '1': '+5V'}, 'SS14', FP_D)
    block('Connector:Barrel_Jack', 'J7', 147.32, 261.62, {'1': 'VIN_RAW', '2': 'GND'},
          '7-12V', 'Connector_BarrelJack:BarrelJack_Horizontal')
    block('Device:D_Schottky', 'D2', 172.72, 259.08, {'2': 'VIN_RAW', '1': 'VIN'}, 'SS14', FP_D)
    block('Regulator_Linear:AMS1117-5.0', 'U2', 213.36, 259.08, {
        '3': 'VIN', '2': '+5V', '1': 'GND'})
    block('Device:C', 'C1', 195.58, 264.16, {'1': 'VIN', '2': 'GND'}, '10u', FP_C)
    block('Device:C', 'C2', 231.14, 264.16, {'1': '+5V', '2': 'GND'}, '10u', FP_C)
    block('Regulator_Linear:AMS1117-3.3', 'U3', 264.16, 259.08, {
        '3': '+5V', '2': '+3V3', '1': 'GND'})
    block('Device:C', 'C3', 281.94, 264.16, {'1': '+3V3', '2': 'GND'}, '22u', FP_C)
    block('Device:C', 'C4', 294.64, 264.16, {'1': '+3V3', '2': 'GND'}, '100n', FP_C)
    block('Device:C', 'C5', 307.34, 264.16, {'1': '+3V3', '2': 'GND'}, '10u', FP_C)

    # Reset (EN) and BOOT buttons, LEDs
    block('Device:R', 'R1', 254.0, 50.8, {'1': '+3V3', '2': 'EN'}, '10k', FP_R)
    block('Device:C', 'C6', 254.0, 71.12, {'1': 'EN', '2': 'GND'}, '1u', FP_C)
    block('Switch:SW_Push', 'SW1', 274.32, 60.96, {'1': 'EN', '2': 'GND'}, 'RESET', FP_SW)
    block('Device:R', 'R2', 302.26, 50.8, {'1': '+3V3', '2': 'IO0'}, '10k', FP_R)
    block('Switch:SW_Push', 'SW2', 322.58, 60.96, {'1': 'IO0', '2': 'GND'}, 'BOOT', FP_SW)
    block('Device:R', 'R3', 350.52, 50.8, {'1': '+3V3', '2': 'PWR_LED'}, '1k', FP_R)
    block('Device:LED', 'D3', 350.52, 68.58, {'2': 'PWR_LED', '1': 'GND'}, 'ON', FP_LED)
    block('Device:R', 'R4', 375.92, 50.8, {'1': 'D13', '2': 'L_LED'}, '1k', FP_R)
    block('Device:LED', 'D4', 375.92, 68.58, {'2': 'L_LED', '1': 'GND'}, 'L', FP_LED)


if __name__ == '__main__':
    main()
