"""Local HTTP server that serves the Three.js viewer with generated STL files.

Files are read into memory at startup to avoid filesystem issues.
Handles port cleanup to prevent zombie server processes.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_VIEWER_TEMPLATE = _TEMPLATE_DIR / "viewer.html"

# Module-level storage so all handler instances can access them
_server_html: bytes = b""
_server_stl: dict[str, bytes] = {}


class _ViewerHandler(BaseHTTPRequestHandler):
    """Serves viewer HTML and STL files from in-memory buffers."""

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve(_server_html, "text/html; charset=utf-8")
        else:
            name = self.path.lstrip("/")
            if name in _server_stl:
                self._serve(_server_stl[name], "application/octet-stream")
            else:
                self.send_error(404, f"Not found: {self.path}")

    def _serve(self, data: bytes, content_type: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"  [viewer] {fmt % args}", flush=True)


def _kill_port(port: int) -> None:
    """Kill any process currently listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        pids_to_kill = set()
        for line in result.stdout.splitlines():
            if f"127.0.0.1:{port}" in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    try:
                        pids_to_kill.add(int(parts[-1]))
                    except ValueError:
                        pass
        for pid in pids_to_kill:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True, timeout=5,
                )
                print(f"  Killed stale server process (PID {pid})", flush=True)
            except Exception:
                pass
    except Exception:
        pass


def _build_viewer_html(stl_files: list[dict]) -> str:
    template = _VIEWER_TEMPLATE.read_text(encoding="utf-8")
    stl_json = json.dumps(stl_files)
    return template.replace("/*STL_FILES_JSON*/[]", stl_json)


def launch_viewer(output_dir: str | Path, *, port: int = 8765, open_browser: bool = True) -> None:
    """Start a local HTTP server to display the ring model in the browser."""
    global _server_html, _server_stl

    out = Path(output_dir)

    stl_entries: list[dict] = []
    stl_data: dict[str, bytes] = {}

    for f in sorted(out.glob("*.stl")):
        try:
            data = f.read_bytes()
            stl_entries.append({"name": f.name, "url": f"/{f.name}"})
            stl_data[f.name] = data
            print(f"  Loaded {f.name} ({len(data):,} bytes)", flush=True)
        except Exception as exc:
            print(f"  Warning: could not read {f.name}: {exc}", flush=True)

    if not stl_entries:
        print(f"  No STL files found in {out}", flush=True)
        return

    _server_html = _build_viewer_html(stl_entries).encode("utf-8")
    _server_stl = stl_data

    # Kill any old servers on this port before starting
    _kill_port(port)

    # Explicitly create the socket to prevent SO_REUSEADDR surprises on Windows
    server = HTTPServer(("127.0.0.1", port), _ViewerHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)

    url = f"http://127.0.0.1:{port}"
    print(f"\n  3D Viewer running at: {url}", flush=True)
    print("  Press Ctrl+C to stop.\n", flush=True)

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Viewer stopped.", flush=True)
    finally:
        server.server_close()
