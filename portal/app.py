"""Portal web server implementation with zero-dependency standard library fallback."""

from __future__ import annotations

import json
import os
import socketserver
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

from hub.core.database import Database

PORTAL_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PORTAL_DIR / "templates"


def make_handler(db: Database):
    class HubPortalHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                html_file = TEMPLATES_DIR / "index.html"
                self.wfile.write(html_file.read_bytes())
                return

            if self.path == "/api/stats":
                stats = db.get_storage_stats()
                quota = db.get_config("gdrive_storage_quota_bytes", 5 * 1024**4)
                stats["quota_bytes"] = quota
                self._send_json(stats)
                return

            if self.path == "/api/config":
                configs = db.get_all_config()
                self._send_json(configs)
                return

            if self.path.startswith("/api/runs"):
                runs = db.get_recent_runs(limit=30)
                self._send_json(runs)
                return

            if self.path.startswith("/api/errors"):
                errors = db.get_unresolved_errors(limit=50)
                self._send_json(errors)
                return

            self.send_error(404, "Not Found")

        def do_POST(self):
            if self.path == "/api/config":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    payload = json.loads(body.decode("utf-8"))
                    for k, v in payload.items():
                        db.set_config(k, v)
                    self._send_json({"status": "SUCCESS", "message": "Configurations updated"})
                except Exception as e:
                    self._send_json({"status": "ERROR", "error": str(e)}, status_code=400)
                return

            self.send_error(404, "Not Found")

        def _send_json(self, data: Any, status_code: int = 200):
            body = json.dumps(data).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            # Suppress normal access log spam to console
            return

    return HubPortalHandler


def run_portal(db: Database, host: str = "0.0.0.0", port: int = 8080) -> None:
    handler = make_handler(db)
    # On non-Windows platforms, allow reuse address
    if os.name != "nt":
        socketserver.TCPServer.allow_reuse_address = True

    current_port = port
    max_attempts = 20

    for attempt in range(max_attempts):
        try:
            with socketserver.TCPServer((host, current_port), handler) as httpd:
                if current_port != port:
                    print(f"[!] Port {port} was already in use or restricted. Switched to open port {current_port}.")
                print(f"[+] Data Hub Management Portal is live at http://localhost:{current_port} (and http://127.0.0.1:{current_port})")
                try:
                    httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\n[*] Stopping portal server.")
                return
        except (OSError, PermissionError) as e:
            win_err = getattr(e, "winerror", None)
            err_no = getattr(e, "errno", None)
            if win_err in (10048, 10013) or err_no in (48, 98, 13) or isinstance(e, PermissionError):
                current_port += 1
                continue
            raise

    print(f"[X] Could not find an available port in range {port} - {current_port - 1}.")
