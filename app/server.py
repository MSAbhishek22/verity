"""Local dev server for Verity — Python stdlib only.

Usage:
    python3 app/server.py            # http://127.0.0.1:8080
    PORT=9000 python3 app/server.py

Delegates every request to service.handle, the same handler the Vercel
adapter uses, so local behaviour matches production.
"""

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import service  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _dispatch(self, method):
        split = urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else None
        query = parse_qs(split.query)
        try:
            status, content_type, payload = service.handle(
                method, split.path, query, body)
        except Exception as exc:  # never leak a stack trace to the client
            payload = (
                b'{"error": "internal_error", "message": "Unexpected server '
                b'error."}'
            )
            status, content_type = 500, "application/json"
            print(f"ERROR {method} {split.path}: {exc!r}", file=sys.stderr)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Verity dev server: http://127.0.0.1:{port} (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
