import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sexpr import parse, find, find1
LIB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../build/kicad-libs-10.0.8/stage-10.0.8/symbols')
def load(lib, name):
    tree = parse(open(f'{LIB}/{lib}.kicad_symdir/{name}.kicad_sym').read())
    return find1(tree, 'symbol')
def pins(sym):
    out = []
    def walk(n):
        for c in n:
            if isinstance(c, list):
                if c and c[0] == 'pin':
                    at = find1(c, 'at'); nm = find1(c, 'name'); num = find1(c, 'number'); ln = find1(c, 'length')
                    out.append((num[1], nm[1], c[1], float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0, float(ln[1])))
                else:
                    walk(c)
    walk(sym)
    return out
if __name__ == '__main__':
    for spec in sys.argv[1:]:
        lib, name = spec.split(':')
        s = load(lib, name)
        ext = find1(s, 'extends')
        print('==', spec, 'extends', ext[1] if ext else None)
        for p in pins(s): print('  ', p)
