#!/usr/bin/env python3
"""
Eval Viewer — local server
Usage:
    python3 server.py path/to/results.json
    python3 server.py path/to/results.json --port 8765

Opens the viewer in your browser. All saves write directly to the JSON file.
"""

import sys
import json
import os
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ── Args ──────────────────────────────────────────────────────────────────────
args = sys.argv[1:]
if not args or args[0].startswith('--'):
    print("Usage: python3 server.py <results.json> [--port 8765]")
    sys.exit(1)

JSON_PATH = os.path.abspath(args[0])
PORT = 8765
for i, a in enumerate(args):
    if a == '--port' and i + 1 < len(args):
        PORT = int(args[i + 1])

if not os.path.exists(JSON_PATH):
    print(f"File not found: {JSON_PATH}")
    sys.exit(1)

VIEWER_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"  File : {JSON_PATH}")
print(f"  Port : {PORT}")
print(f"  URL  : http://localhost:{PORT}")
print(f"\nPress Ctrl+C to stop.\n")

# ── Request handler ───────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *a):
        pass  # suppress default access logs

    def send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, mime):
        with open(path, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self.send_file(os.path.join(VIEWER_DIR, 'viewer.html'), 'text/html; charset=utf-8')

        elif path == '/api/data':
            try:
                with open(JSON_PATH, 'r', encoding='utf-8') as f:
                    raw = json.load(f)
                # Normalize annotation fields
                for item in raw:
                    item.setdefault('_status', None)
                    item.setdefault('_tags', [])
                    item.setdefault('_notes', '')
                self.send_json({'ok': True, 'data': raw, 'filename': os.path.basename(JSON_PATH)})
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)}, 500)

        elif path == '/api/filename':
            self.send_json({'filename': os.path.basename(JSON_PATH)})

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/save':
            try:
                length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(length)
                payload = json.loads(body)
                # Write the full array back to disk
                with open(JSON_PATH, 'w', encoding='utf-8') as f:
                    json.dump(payload['data'], f, indent=2, ensure_ascii=False)
                print(f"  ✓ Saved entry #{payload.get('id', '?')} → {os.path.basename(JSON_PATH)}")
                self.send_json({'ok': True})
            except Exception as e:
                print(f"  ✗ Save error: {e}")
                self.send_json({'ok': False, 'error': str(e)}, 500)
        else:
            self.send_response(404)
            self.end_headers()

# ── Start ─────────────────────────────────────────────────────────────────────
server = HTTPServer(('localhost', PORT), Handler)
threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{PORT}')).start()
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServer stopped.")
