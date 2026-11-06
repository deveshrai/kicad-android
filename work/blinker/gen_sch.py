#!/usr/bin/env python3
"""Generate the 555 LED blinker schematic (CR2032, ICM7555, 5 mm LED) from the KiCad 10.0.8 symbols.

Every pin gets a short wire stub ending in a net label (signals) or power symbol (power nets),
so the netlist below is the whole design. The output is opened, checked and continued in the
Android app (ERC, annotation, PCB update, layout).
"""
import sys, os, uuid, copy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../rp2350'))
from sexpr import parse, dump, find, find1, Str

LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../build/kicad-libs-10.0.8/stage-10.0.8/symbols')
PROJECT = 'blinker'
ROOT = str(uuid.uuid4())
POWER_NETS = {'GND': 'power:GND', 'VCC': 'power:VCC'}

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

# Purchasing info for the BOM: (Manufacturer, MPN), by (library symbol, value)
PARTS = {
    ('Device:R_Small', '5.1k'): ('Yageo', 'RC0603FR-075K1L', 'Resistor 5.1k 1% 1/10W 0603'),
    ('Device:R_Small', '27'): ('Yageo', 'RC0603FR-0727RL', 'Resistor 27R 1% 1/10W 0603'),
    ('Device:R_Small', '33'): ('Yageo', 'RC0603FR-0733RL', 'Resistor 33R 1% 1/10W 0603'),
    ('Device:R_Small', '330'): ('Yageo', 'RC0603FR-07330RL', 'Resistor 330R 1% 1/10W 0603'),
    ('Device:R_Small', '1k'): ('Yageo', 'RC0603FR-071KL', 'Resistor 1k 1% 1/10W 0603'),
    ('Device:R_Small', '10k'): ('Yageo', 'RC0603FR-0710KL', 'Resistor 10k 1% 1/10W 0603'),
    ('Device:C_Small', '100n'): ('Samsung', 'CL10B104KB8NNNC', 'Capacitor 100nF 50V X7R 10% 0603'),
    ('Device:C_Small', '1u'): ('Samsung', 'CL10A105KB8NNNC', 'Capacitor 1uF 50V X5R 10% 0603'),
    ('Device:C_Small', '15p'): ('Samsung', 'CL10C150JB8NNNC', 'Capacitor 15pF 50V C0G 5% 0603'),
    ('Device:C_Small', '4.7u'): ('Samsung', 'CL21A475KAQNNNE', 'Capacitor 4.7uF 25V X5R 10% 0805'),
    ('Device:C_Small', '10u'): ('Samsung', 'CL21A106KAYNNNE', 'Capacitor 10uF 25V X5R 10% 0805'),
    ('Device:L_Small', '3.3u'): ('Abracon', 'AOTA-B201610S3R3-101-T', 'Power inductor 3.3uH 2016 (RP2350 core regulator)'),
    ('Device:Crystal_GND24_Small', '12MHz'): ('Abracon', 'ABM8-272-T3', 'Crystal 12MHz 10pF 3225 4-pad'),
    ('Device:LED_Small', 'Red'): ('Kingbright', 'APT1608EC', 'LED red 0603'),
    ('Device:LED_Small', 'Green'): ('Kingbright', 'APT1608SGC', 'LED green 0603'),
    ('Device:LED_Small', 'Blue'): ('Kingbright', 'APT1608QBC/D', 'LED blue 0603'),
    ('MCU_RaspberryPi:RP2350A', 'RP2350A'): ('Raspberry Pi', 'RP2350A', 'MCU RP2350A dual Cortex-M33/Hazard3 150MHz 520KB SRAM QFN-60 7x7'),
    ('Regulator_Linear:AP2112K-3.3', 'AP2112K-3.3'): ('Diodes Inc', 'AP2112K-3.3TRG1', 'LDO regulator 3.3V 600mA SOT-23-5'),
    ('Memory_Flash:W25Q128JVS', 'W25Q128JVS'): ('Winbond', 'W25Q128JVSIQ', 'QSPI NOR flash 128Mbit (16MB) SOIC-8 208mil'),
    ('Connector:USB_C_Receptacle_USB2.0_16P', 'USB_C'): ('HRO', 'TYPE-C-31-M-12', 'USB-C receptacle USB 2.0 16-pin SMD'),
    ('Switch:SW_Push', None): ('E-Switch', 'TL3342F160QG', 'Tactile switch SPST 4.2x3.2mm SMD 160gf'),
    ('Connector_Generic:Conn_01x14', 'ILI9341_SPI'): ('Sullins', 'PPTC141LFBN-RC', 'Female header 1x14 2.54mm vertical (ILI9341 2.8in module)'),
    ('Connector_Generic:Conn_02x20_Odd_Even', 'IO'): ('Sullins', 'PRPC020DAAN-RC', 'Male header 2x20 2.54mm vertical'),
}

def place(lib_id, ref, value, x, y, footprint='', unit=1, in_bom=True, on_board=True):
    if lib_id == 'Mechanical:MountingHole':
        in_bom = False          # a hole in the board, nothing to buy
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
    mfr = PARTS.get((lib_id, value)) or PARTS.get((lib_id, None))
    if mfr and not ref.startswith('#'):
        sym += [prop('Manufacturer', mfr[0], x, y, hide=True), prop('MPN', mfr[1], x, y, hide=True)]
        for f in sym:
            if isinstance(f, list) and f[0] == 'property' and f[1] == 'Description':
                f[2] = Str(mfr[2])
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
# Astable CMOS 555 (ICM7555, runs from 2 V) on a CR2032: f = 1.44 / ((R1 + 2 R2) C1) ~ 1.5 Hz
R_THT = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
C_DISC = 'Capacitor_THT:C_Disc_D3.0mm_W1.6mm_P2.50mm'

# CR2032 cell and on/off switch
bt = place('Device:Battery_Cell', 'BT1', 'CR2032', 40.64, 76.2, 'Battery:BatteryHolder_Keystone_103_1x20mm')
connect(bt, '1', 'VBAT')
connect(bt, '2', 'GND')
sw = place('Switch:SW_SPST', 'SW1', 'ON/OFF', 60.96, 50.8, 'Button_Switch_THT:SW_DIP_SPSTx01_Slide_9.78x4.72mm_W7.62mm_P2.54mm')
connect(sw, '1', 'VBAT')
connect(sw, '2', 'VCC')
# VCC only comes through the (passive) switch: flag it where the switch output ends
(ex, ey, d), = endpoints(sw, '2')[:1]
dx, dy = DIRS[d]
power('power:PWR_FLAG', ex + dx * 2.54, ey + dy * 2.54, 90)

# The timer
u = place('Timer:ICM7555xP', 'U1', 'ICM7555', 116.84, 76.2, 'Package_DIP:DIP-8_W7.62mm')
for pin, net in (('1', 'GND'), ('2', 'THR'), ('3', 'OUT'), ('4', 'VCC'), ('5', 'CV'),
                 ('6', 'THR'), ('7', 'DIS'), ('8', 'VCC')):
    connect(u, pin, net)

# Timing network
two_pin('Device:R', 'R1', '1k', 154.94, 55.88, 'VCC', 'DIS', R_THT)
two_pin('Device:R', 'R2', '47k', 154.94, 76.2, 'DIS', 'THR', R_THT)
two_pin('Device:C_Polarized', 'C1', '10u', 154.94, 99.06, 'THR', 'GND', 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm')
two_pin('Device:C', 'C2', '10n', 91.44, 104.14, 'CV', 'GND', C_DISC)
two_pin('Device:C', 'C3', '100n', 76.2, 50.8, 'VCC', 'GND', C_DISC)

# LED and its resistor (5 mm red LED, about 5 mA from 3 V)
two_pin('Device:R', 'R3', '220', 185.42, 66.04, 'OUT', 'LED_A', R_THT)
two_pin('Device:LED', 'D1', 'Red 5mm', 185.42, 88.9, 'GND', 'LED_A', 'LED_THT:LED_D5.0mm')

# Power flag: GND comes from the cell, which has no power output pin
for i, (net, xx) in enumerate((('GND', 30.48),)):
    yy = 116.84
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
       ['generator_version', Str('10.99')], ['uuid', Str(ROOT)], ['paper', Str('A4')],
       ['title_block', ['title', Str('555 LED blinker')], ['date', Str('2026-11-06')],
        ['rev', Str('A')], ['comment', 1, Str('Generated from KiCad 10.0.8 library symbols')]],
       lib_symbols] + items + [['sheet_instances', ['path', Str('/'), ['page', Str('1')]]],
                               ['embedded_fonts', 'no']]

out = sys.argv[1] if len(sys.argv) > 1 else f'{PROJECT}.kicad_sch'
open(out, 'w').write(dump(sch) + '\n')
print(f'wrote {out}: {sum(1 for i in items if i[0] == "symbol")} symbols, '
      f'{sum(1 for i in items if i[0] == "label")} labels, {sum(1 for i in items if i[0] == "wire")} wires')
