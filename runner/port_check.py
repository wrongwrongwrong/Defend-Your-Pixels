"""Local port availability checks before starting HTTP/WS servers."""

from __future__ import annotations

import socket

# Default HTTP port for all local frontends (override with --http-port if bind fails).
DEFAULT_HTTP_PORT = 8080


def _bind_probe(host: str, port: int) -> tuple[bool, str | None]:
    """Try the same bind the servers use; catches reserved/unbindable ports."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True, None
        except PermissionError:
            return False, (
                "permission denied — try another port with --http-port <port>"
            )
        except OSError as exc:
            if exc.errno in (98, 10048):  # Address already in use (Linux / Windows)
                return False, "already in use by another process"
            return False, str(exc)


def ensure_ports_available(
    *,
    http_port: int,
    ws_port: int,
    ws_host: str = "localhost",
    runtime_name: str = "runtime",
) -> None:
    """Fail fast with a clear message when HTTP/WS ports cannot be bound."""
    ws_bind_host = "127.0.0.1" if ws_host == "localhost" else ws_host
    problems: list[str] = []

    http_ok, http_err = _bind_probe("", http_port)
    if not http_ok:
        problems.append(f"HTTP :{http_port} — {http_err}")

    ws_ok, ws_err = _bind_probe(ws_bind_host, ws_port)
    if not ws_ok:
        problems.append(f"WebSocket :{ws_port} — {ws_err}")

    if not problems:
        return

    detail = "\n".join(f"  - {item}" for item in problems)
    hints = (
        "Stop any other Python backend (live tracker, manual play, demo) "
        "before starting this one. If the HTTP port cannot bind, pass --http-port <port>."
    )

    raise RuntimeError(f"{runtime_name} cannot start:\n{detail}\n\n{hints}")
