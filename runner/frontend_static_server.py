"""Small HTTP static server for the frontend with dev-friendly cache headers.

Browsers aggressively cache ES modules and images during local iteration. Disabling cache
for JS/HTML/CSS/JSON and common image types avoids stale modules and "wrong facing" art
after PNG edits (304 + old body).
"""

from __future__ import annotations

import functools
import http.server
import posixpath
import socketserver
import threading
from urllib.parse import unquote, urlsplit
from pathlib import Path


class FrontendRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, protocol_root: str | None = None, **kwargs):
        self.protocol_root = Path(protocol_root).resolve() if protocol_root else None
        super().__init__(*args, directory=directory, **kwargs)

    def translate_path(self, path: str) -> str:
        url_path = posixpath.normpath(unquote(urlsplit(path).path))
        if self.protocol_root is not None and (url_path == "/protocol" or url_path.startswith("/protocol/")):
            rel_path = url_path.removeprefix("/protocol").lstrip("/")
            return str((self.protocol_root / rel_path).resolve())
        return super().translate_path(path)

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


def start_frontend_http_server(port: int, root: Path, protocol_root: Path | None = None):
    handler = functools.partial(
        FrontendRequestHandler,
        directory=str(root.resolve()),
        protocol_root=str(protocol_root.resolve()) if protocol_root else None,
    )
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[HTTP] Serving {root} at http://localhost:{port}")
    return httpd
