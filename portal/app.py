"""Portal web server implementation with zero-dependency standard library fallback."""

from __future__ import annotations

import json
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
    with socketserver.TCPServer((host, port), handler) as httpd:
        print(f"[+] Data Hub Management Portal is live at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Stopping portal server.")
