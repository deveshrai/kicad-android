"""Minimal KiCad S-expression reader/writer (strings keep their quotes distinct from atoms)."""
import re

class Str(str):
    """A quoted string token (written back with quotes)."""

TOKEN = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)', re.S)

def parse(text):
    stack = [[]]
    for m in TOKEN.finditer(text):
        t = m.group(1)
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(Str(bytes(t[1:-1], 'utf-8').decode('unicode_escape') if '\\' in t else t[1:-1]))
        else:
            stack[-1].append(t)
    return stack[0][0]

def esc(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'

def dump(node, indent=0):
    if isinstance(node, Str):
        return esc(node)
    if not isinstance(node, list):
        return str(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(dump(c) for c in node) + ')'
    pad = '\t' * (indent + 1)
    out = '(' + ' '.join(dump(c) for c in node if not isinstance(c, list))
    for c in node:
        if isinstance(c, list):
            out += '\n' + pad + dump(c, indent + 1)
    return out + '\n' + '\t' * indent + ')'

def find(node, head):
    return [c for c in node if isinstance(c, list) and c and c[0] == head]

def find1(node, head):
    r = find(node, head)
    return r[0] if r else None
