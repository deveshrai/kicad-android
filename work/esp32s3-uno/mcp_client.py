#!/usr/bin/env python3
"""A small MCP client for KiCad's built-in MCP server (Streamable HTTP, JSON responses).

Every request and response is appended to mcp-log.jsonl next to this file, so a design session
driven through MCP leaves a full record.

    from mcp_client import KiCad
    k = KiCad()                       # token from $KICAD_MCP_TOKEN or ../../build/.mcp-token
    k.tool("kicad_status")
    k.api("GetNets", board=...)
"""
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, 'mcp-log.jsonl')


class McpError(Exception):
    pass


class KiCad:
    def __init__(self, url='http://127.0.0.1:27880/mcp', token=None):
        self.url = url
        self.token = token or os.environ.get('KICAD_MCP_TOKEN') or open(
            os.path.join(HERE, '../../build/.mcp-token')).read().strip()
        self.next_id = 1
        init = self.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                                       'clientInfo': {'name': 'esp32s3-uno-builder',
                                                      'version': '1'}})
        self.server = init['serverInfo']
        self.rpc('notifications/initialized', None, notify=True)

    def rpc(self, method, params, notify=False, timeout=900):
        msg = {'jsonrpc': '2.0', 'method': method}
        if params is not None:
            msg['params'] = params
        if not notify:
            msg['id'] = self.next_id
            self.next_id += 1
        req = urllib.request.Request(self.url, data=json.dumps(msg).encode(), method='POST',
                                     headers={'Authorization': 'Bearer ' + self.token,
                                              'Content-Type': 'application/json',
                                              'Accept': 'application/json, text/event-stream'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
        reply = json.loads(body) if body else None
        with open(LOG, 'a') as f:
            f.write(json.dumps({'t': round(t0, 3), 'ms': int((time.time() - t0) * 1000),
                                'request': msg, 'reply': reply}) + '\n')
        if reply and 'error' in reply:
            raise McpError(reply['error'])
        return reply['result'] if reply else None

    def tool(self, name, **args):
        """Call a tool; returns its text output parsed as JSON when it is JSON."""
        r = self.rpc('tools/call', {'name': name, 'arguments': args})
        text = '\n'.join(c.get('text', '') for c in r['content'] if c['type'] == 'text')
        if r.get('isError'):
            raise McpError(f'{name}: {text}')
        try:
            return json.loads(text)
        except ValueError:
            return text

    def api(self, command, **args):
        """Run an IPC API command through kicad_api."""
        return self.tool('kicad_api', command=command, args=args)
