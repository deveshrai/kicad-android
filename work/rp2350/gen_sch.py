#!/usr/bin/env python3
"""Generate the RP2350A + ILI9341 board schematic from the KiCad 10.0.8 library symbols.

Every pin gets a short wire stub ending in a net label (signals) or power symbol (power nets),
so the netlist below is the whole design. The output is opened, checked and continued in the
Android app (ERC, annotation, PCB update, layout).
"""
import sys, os, uuid, copy
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, dump, find, find1, Str

LIB = '/Users/devesh/projects/KiCadAndroid0/build/kicad-libs-10.0.8/stage-10.0.8/symbols'
PROJECT = 'rp2350_ili9341'
ROOT = str(uuid.uuid4())
POWER_NETS = {'GND': 'power:GND', '+3V3': 'power:+3V3', 'VBUS': 'power:VBUS', '+1V1': 'power:+1V1'}

def uid():
    return Str(str(uuid.uuid4()))

# ---------------------------------------------------------------- library access

_cache = {}

def lib_symbol(lib_id):
    """The library symbol, flattened if it extends a parent."""
    if lib_id in _cache:
        return _cache[lib_id]
    lib, name = lib_id.split(':')
    sym = find1(parse(open(f'{LIB}/{lib}.kicad_symdir/{name}.kicad_sym').read()), 'symbol')
    ext = find1(sym, 'extends')
    if ext:
        parent = copy.deepcopy(lib_symbol(f'{lib}:{ext[1]}'))
        pname = str(parent[1]).split(':')[-1]
        child_props = {p[1]: p for p in find(sym, 'property')}
        flat = [parent[0], Str(name)]
        for c in parent[2:]:
            if isinstance(c, list) and c[0] == 'property' and c[1] in child_props:
                flat.append(child_props.pop(c[1]))
            elif isinstance(c, list) and c[0] == 'symbol':
                c[1] = Str(str(c[1]).replace(pname, name, 1))
                flat.append(c)
            else:
                flat.append(c)
        flat[2:2] = list(child_props.values())
        sym = flat
    _cache[lib_id] = sym
    return sym

def lib_pins(lib_id):
    out = {}
    def walk(n):
        for c in n:
            if isinstance(c, list):
                if c[0] == 'pin':
                    at = find1(c, 'at')
                    out.setdefault(str(find1(c, 'number')[1]), []).append(
                        (float(at[1]), float(at[2]), int(float(at[3]))))
                else:
                    walk(c)
    walk(lib_symbol(lib_id))
    return out

def lib_prop(lib_id, name):
    for p in find(lib_symbol(lib_id), 'property'):
        if p[1] == name:
            return str(p[2])
    return ''

# ---------------------------------------------------------------- schematic building

items = []          # top-level schematic items
used = set()        # lib_ids to embed
pwr_count = [0]
DIRS = {0: (1, 0), 90: (0, -1), 180: (-1, 0), 270: (0, 1)}

def r2(v):
    return round(v, 4)

def effects(hide=False, justify=None):
    e = ['effects', ['font', ['size', '1.27', '1.27']]]
    if justify:
        e.append(['justify'] + justify)
    out = []
    if hide:
        out.append(['hide', 'yes'])
    out.append(e)
    return out

def prop(name, value, x, y, hide=False, rot=0):
    return ['property', Str(name), Str(value), ['at', r2(x), r2(y), rot]] + effects(hide)

def place(lib_id, ref, value, x, y, footprint='', unit=1, in_bom=True, on_board=True):
    used.add(lib_id)
    pins = lib_pins(lib_id)
    ys = [-p[1] for v in pins.values() for p in v] or [0]
    top, bot = y + min(ys) - 3.81, y + max(ys) + 3.81
    if not footprint:
        footprint = lib_prop(lib_id, 'Footprint')
    sym = ['symbol', ['lib_id', Str(lib_id)], ['at', r2(x), r2(y), 0], ['unit', unit],
           ['exclude_from_sim', 'no'], ['in_bom', 'yes' if in_bom else 'no'],
           ['on_board', 'yes' if on_board else 'no'], ['dnp', 'no'], ['uuid', uid()],
           prop('Reference', ref, x, top, hide=ref.startswith('#')),
           prop('Value', value, x, bot, hide=ref.startswith('#')),
           prop('Footprint', footprint, x, y, hide=True),
           prop('Datasheet', lib_prop(lib_id, 'Datasheet'), x, y, hide=True),
           prop('Description', lib_prop(lib_id, 'Description'), x, y, hide=True)]
    for num in sorted(pins):
        sym.append(['pin', Str(num), ['uuid', uid()]])
    sym.append(['instances', ['project', Str(PROJECT),
                ['path', Str('/' + ROOT), ['reference', Str(ref)], ['unit', unit]]]])
    items.append(sym)
    return {'lib_id': lib_id, 'x': x, 'y': y, 'pins': pins, 'ref': ref}

def wire(x1, y1, x2, y2):
    items.append(['wire', ['pts', ['xy', r2(x1), r2(y1)], ['xy', r2(x2), r2(y2)]],
                  ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid()]])

def label(name, x, y, d):
    just = {0: ['left', 'bottom'], 90: ['left', 'bottom'], 180: ['right', 'bottom'], 270: ['right', 'bottom']}[d]
    items.append(['label', Str(name), ['at', r2(x), r2(y), d]] + effects(justify=just) + [['uuid', uid()]])

def power(net, x, y, d):
    lib_id = POWER_NETS[net] if net in POWER_NETS else net
    # GND graphics point down (270), the supply symbols point up (90)
    rot = (d - (270 if net == 'GND' else 90)) % 360
    pwr_count[0] += 1
    ref = f'#PWR{pwr_count[0]:03d}' if lib_id != 'power:PWR_FLAG' else f'#FLG{pwr_count[0]:03d}'
    s = place(lib_id, ref, net if lib_id != 'power:PWR_FLAG' else 'PWR_FLAG', x, y)
    items[-1][3] = ['at', r2(x), r2(y), rot]

def no_connect(x, y):
    items.append(['no_connect', ['at', r2(x), r2(y)], ['uuid', uid()]])

def endpoints(inst, num):
    return [(inst['x'] + px, inst['y'] - py, (ang + 180) % 360) for px, py, ang in inst['pins'][num]]

def connect(inst, num, net, stub=2.54):
    """Stub out from pin `num` and end it in a label or power symbol for `net`."""
    seen = set()
    for ex, ey, d in endpoints(inst, num):
        if (ex, ey) in seen:
            continue        # stacked pins share one connection point
        seen.add((ex, ey))
        if net is None:
            no_connect(ex, ey)
            continue
        dx, dy = DIRS[d]
        sx, sy = ex + dx * stub, ey + dy * stub
        wire(ex, ey, sx, sy)
        if net in POWER_NETS:
            power(net, sx, sy, d)
        else:
            label(net, sx, sy, d)

def two_pin(lib_id, ref, value, x, y, net1, net2, fp):
    inst = place(lib_id, ref, value, x, y, fp)
    connect(inst, '1', net1)
    connect(inst, '2', net2)
    return inst

R_FP = 'Resistor_SMD:R_0603_1608Metric'
C_FP = 'Capacitor_SMD:C_0603_1608Metric'
C_FP_BULK = 'Capacitor_SMD:C_0805_2012Metric'

def R(ref, val, x, y, a, b): return two_pin('Device:R_Small', ref, val, x, y, a, b, R_FP)
def C(ref, val, x, y, a, b, fp=C_FP): return two_pin('Device:C_Small', ref, val, x, y, a, b, fp)

# ---------------------------------------------------------------- the design

# USB-C input
j1 = place('Connector:USB_C_Receptacle_USB2.0_16P', 'J1', 'USB_C', 40.64, 63.5,
           'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12')
for num, net in {'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS', 'A1': 'GND', 'A12': 'GND',
                 'B1': 'GND', 'B12': 'GND', 'SH': 'GND', 'A5': 'CC1', 'B5': 'CC2',
                 'A6': 'USB_CONN_DP', 'B6': 'USB_CONN_DP', 'A7': 'USB_CONN_DM', 'B7': 'USB_CONN_DM',
                 'A8': None, 'B8': None}.items():
    connect(j1, num, net)
R('R1', '5.1k', 78.74, 50.8, 'CC1', 'GND')
R('R2', '5.1k', 86.36, 50.8, 'CC2', 'GND')
R('R3', '27', 93.98, 50.8, 'USB_CONN_DP', 'USB_DP')
R('R4', '27', 101.6, 50.8, 'USB_CONN_DM', 'USB_DM')

# 3.3 V LDO
u2 = place('Regulator_Linear:AP2112K-3.3', 'U2', 'AP2112K-3.3', 50.8, 116.84)
for num, net in {'1': 'VBUS', '3': 'VBUS', '2': 'GND', '5': '+3V3', '4': None}.items():
    connect(u2, num, net)
C('C1', '1u', 73.66, 116.84, 'VBUS', 'GND')
C('C2', '1u', 81.28, 116.84, '+3V3', 'GND')
C('C3', '10u', 88.9, 116.84, '+3V3', 'GND', C_FP_BULK)

# RP2350A
u1 = place('MCU_RaspberryPi:RP2350A', 'U1', 'RP2350A', 203.2, 152.4)
top_pins = {'1': '+3V3', '54': '+3V3', '53': '+3V3', '44': '+3V3', '49': '+3V3', '46': 'VREG_AVDD',
            '48': 'VREG_LX', '50': '+1V1', '6': '+1V1'}
for i, (num, net) in enumerate(top_pins.items()):
    connect(u1, num, net, stub=2.54 if i % 2 == 0 else 7.62)
for num, net in {'61': 'GND', '47': 'GND', '26': 'RUN', '51': 'USB_DM', '52': 'USB_DP',
                 '60': 'QSPI_SS', '56': 'QSPI_SCLK', '57': 'QSPI_SD0', '59': 'QSPI_SD1',
                 '58': 'QSPI_SD2', '55': 'QSPI_SD3', '21': 'XIN', '22': 'XOUT',
                 '24': 'SWCLK', '25': 'SWDIO'}.items():
    connect(u1, num, net, stub=5.08 if num in ('47',) else 2.54)
gpio_pin = {0: '2', 1: '3', 2: '4', 3: '5', 4: '7', 5: '8', 6: '9', 7: '10', 8: '12', 9: '13',
            10: '14', 11: '15', 12: '16', 13: '17', 14: '18', 15: '19', 16: '27', 17: '28',
            18: '29', 19: '31', 20: '32', 21: '33', 22: '34', 23: '35', 24: '36', 25: '37',
            26: '40', 27: '41', 28: '42', 29: '43'}
for g, num in gpio_pin.items():
    connect(u1, num, f'GPIO{g}')

# RP2350A supply decoupling and core regulator
x = 124.46
for i in range(6):
    C(f'C{4 + i}', '100n', x, 45.72, '+3V3', 'GND'); x += 7.62
C('C10', '100n', x, 45.72, '+3V3', 'GND'); x += 7.62      # QSPI_IOVDD
C('C11', '100n', x, 45.72, '+3V3', 'GND'); x += 7.62      # USB_OTP_VDD
C('C12', '100n', x, 45.72, '+3V3', 'GND'); x += 7.62      # ADC_AVDD
C('C13', '4.7u', x, 45.72, '+3V3', 'GND', C_FP_BULK); x += 7.62   # VREG_VIN
R('R5', '33', x, 45.72, '+3V3', 'VREG_AVDD'); x += 7.62
C('C14', '4.7u', x, 45.72, 'VREG_AVDD', 'GND', C_FP_BULK); x += 7.62
two_pin('Device:L_Small', 'L1', '3.3u', x, 45.72, 'VREG_LX', '+1V1',
        'Inductor_SMD:L_Abracon_AOTA-B201610S'); x += 7.62
C('C15', '4.7u', x, 45.72, '+1V1', 'GND', C_FP_BULK); x += 7.62
for i in range(3):
    C(f'C{16 + i}', '100n', x, 45.72, '+1V1', 'GND'); x += 7.62

# QSPI flash
u3 = place('Memory_Flash:W25Q128JVS', 'U3', 'W25Q128JVS', 129.54, 165.1)
for num, net in {'1': 'QSPI_SS', '2': 'QSPI_SD1', '3': 'QSPI_SD2', '4': 'GND', '5': 'QSPI_SD0',
                 '6': 'QSPI_SCLK', '7': 'QSPI_SD3', '8': '+3V3'}.items():
    connect(u3, num, net)
C('C19', '100n', 147.32, 142.24, '+3V3', 'GND')

# 12 MHz crystal
y1 = place('Device:Crystal_GND24_Small', 'Y1', '12MHz', 129.54, 213.36,
           'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
for num, net in {'1': 'XIN', '3': 'XTAL_OUT', '2': 'GND', '4': 'GND'}.items():
    connect(y1, num, net)
R('R6', '1k', 149.86, 213.36, 'XOUT', 'XTAL_OUT')
C('C20', '15p', 116.84, 231.14, 'XIN', 'GND')
C('C21', '15p', 142.24, 231.14, 'XTAL_OUT', 'GND')

# BOOTSEL and RESET
SW_FP = 'Button_Switch_SMD:SW_SPST_TL3342'
R('R7', '1k', 60.96, 160.02, 'QSPI_SS', 'BOOT_SW')
sw = place('Switch:SW_Push', 'SW4', 'BOOTSEL', 60.96, 177.8, SW_FP)
connect(sw, '1', 'BOOT_SW'); connect(sw, '2', 'GND')
R('R8', '10k', 60.96, 195.58, '+3V3', 'RUN')
sw = place('Switch:SW_Push', 'SW5', 'RESET', 60.96, 213.36, SW_FP)
connect(sw, '1', 'RUN'); connect(sw, '2', 'GND')

# User buttons
for i, g in enumerate((10, 11, 12)):
    sw = place('Switch:SW_Push', f'SW{i + 1}', f'BTN{i + 1}', 297.18, 50.8 + i * 15.24, SW_FP)
    connect(sw, '1', f'GPIO{g}'); connect(sw, '2', 'GND')

# RGB LEDs
for i, (g, colour) in enumerate(((6, 'R'), (7, 'G'), (8, 'B'))):
    yy = 106.68 + i * 15.24
    R(f'R{9 + i}', '330', 284.48, yy, f'GPIO{g}', f'LED_{colour}')
    d = place('Device:LED_Small', f'D{i + 1}', {'R': 'Red', 'G': 'Green', 'B': 'Blue'}[colour],
              304.8, yy, 'LED_SMD:LED_0603_1608Metric')
    connect(d, '2', f'LED_{colour}'); connect(d, '1', 'GND')

# ILI9341 2.8" SPI module (14-pin header: VCC GND CS RESET DC SDI SCK LED SDO T_CLK T_CS T_DIN T_DO T_IRQ)
j3 = place('Connector_Generic:Conn_01x14', 'J3', 'ILI9341_SPI', 363.22, 76.2,
           'Connector_PinSocket_2.54mm:PinSocket_1x14_P2.54mm_Vertical')
for num, net in enumerate(['+3V3', 'GND', 'GPIO17', 'GPIO21', 'GPIO20', 'GPIO19', 'GPIO18',
                           'GPIO22', 'GPIO16', 'GPIO18', 'GPIO15', 'GPIO19', 'GPIO16', 'GPIO14'], 1):
    connect(j3, str(num), net)

# 2x20 IO header
j2 = place('Connector_Generic:Conn_02x20_Odd_Even', 'J2', 'IO', 363.22, 182.88,
           'Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical')
header = ['VBUS', '+3V3', 'GND', 'GND'] + [f'GPIO{g}' for g in range(30)] + \
         ['SWCLK', 'SWDIO', 'RUN', 'GND', '+3V3', 'GND']
for num, net in enumerate(header, 1):
    connect(j2, str(num), net)

# Mounting holes
for i in range(4):
    place('Mechanical:MountingHole', f'H{i + 1}', 'MountingHole', 335.28 + i * 15.24, 264.16,
          'MountingHole:MountingHole_2.7mm_M2.5')

# Power flags for nets without a power output pin driving them
for i, (net, xx) in enumerate((('GND', 30.48), ('VBUS', 45.72), ('+1V1', 60.96), ('VREG_AVDD', 76.2))):
    yy = 254.0
    power('power:PWR_FLAG', xx, yy, 90)
    wire(xx, yy, xx, yy + 5.08)
    if net in POWER_NETS:
        power(net, xx, yy + 5.08, 270)
    else:
        label(net, xx, yy + 5.08, 270)

# ---------------------------------------------------------------- write

lib_symbols = ['lib_symbols']
for lib_id in sorted(used):
    s = copy.deepcopy(lib_symbol(lib_id))
    s[1] = Str(lib_id)
    lib_symbols.append(s)

sch = ['kicad_sch', ['version', '20261025'], ['generator', Str('eeschema')],
       ['generator_version', Str('10.99')], ['uuid', Str(ROOT)], ['paper', Str('A3')],
       ['title_block', ['title', Str('RP2350A + ILI9341 board')], ['date', Str('2026-11-01')],
        ['rev', Str('A')], ['comment', 1, Str('Generated from KiCad 10.0.8 library symbols')]],
       lib_symbols] + items + [['sheet_instances', ['path', Str('/'), ['page', Str('1')]]],
                               ['embedded_fonts', 'no']]

out = sys.argv[1] if len(sys.argv) > 1 else f'{PROJECT}.kicad_sch'
open(out, 'w').write(dump(sch) + '\n')
print(f'wrote {out}: {sum(1 for i in items if i[0] == "symbol")} symbols, '
      f'{sum(1 for i in items if i[0] == "label")} labels, {sum(1 for i in items if i[0] == "wire")} wires')
