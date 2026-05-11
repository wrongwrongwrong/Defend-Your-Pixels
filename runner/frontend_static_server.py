"""Small HTTP static server for yu_test3 with dev-friendly cache headers.

Browsers aggressively cache ES modules and images during local iteration. Disabling cache
for JS/HTML/CSS/JSON and common image types avoids stale modules and "wrong facing" art
after PNG edits (304 + old body).
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from pathlib import Path


class FrontendRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        path_only = self.path.partition("?")[0].lower()
        if path_only.endswith(
            (
                ".js",
                ".mjs",
                ".html",
                ".css",
                ".json",
                ".png",
                ".webp",
                ".jpg",
                ".jpeg",
                ".gif",
                ".ico",
                ".svg",
            )
        ):
            self.send_header("Cache-Control", "no-store, max-age=0, must-revalidate")
        super().end_headers()


def start_frontend_http_server(port: int, root: Path):
    handler = functools.partial(FrontendRequestHandler, directory=str(root.resolve()))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[HTTP] Serving {root} at http://localhost:{port}")
    return httpd
