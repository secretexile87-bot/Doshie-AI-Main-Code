#!/usr/bin/env python3
"""
doshie_node.py - Lightweight Technician Node Agent for Doshie Fleet Management
Runs on remote nodes (Windows or Linux) to provide authorized remote execution,
file reading, file writing, and hardware health checks over Tailscale.
Default port: 5055.
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("DOSHIE_NODE_PORT", "5055"))
HOST = os.environ.get("DOSHIE_NODE_HOST", "0.0.0.0")


class DoshieNodeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep logging concise
        sys.stderr.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {args[0]} {args[1]}\n")

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            import platform
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                data = {
                    "status": "online",
                    "hostname": platform.node(),
                    "os": platform.system().lower(),
                    "cpu_percent": cpu,
                    "ram_used_gb": round(mem.used / (1024**3), 2),
                    "ram_total_gb": round(mem.total / (1024**3), 2),
                    "ram_percent": mem.percent
                }
            except Exception:
                data = {
                    "status": "online",
                    "hostname": platform.node(),
                    "os": platform.system().lower()
                }
            return self._send_json(200, data)
        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            payload = {}

        if self.path == "/api/exec":
            cmd = str(payload.get("command") or "").strip()
            timeout = int(payload.get("timeout") or 60)
            if not cmd:
                return self._send_json(400, {"ok": False, "error": "No command provided."})
            try:
                p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                return self._send_json(200, {
                    "ok": p.returncode == 0,
                    "exit_code": p.returncode,
                    "stdout": p.stdout,
                    "stderr": p.stderr
                })
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        elif self.path == "/api/file/read":
            path_str = str(payload.get("path") or "").strip()
            start = max(int(payload.get("start_line") or 1), 1)
            count = min(max(int(payload.get("line_count") or 150), 1), 500)
            p = Path(path_str).expanduser()
            if not p.exists() or not p.is_file():
                return self._send_json(404, {"ok": False, "error": f"File not found: {path_str}"})
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                end = min(start + count - 1, len(lines))
                slice_lines = lines[start - 1:end]
                numbered = "".join(f"{i + start}: {line}" for i, line in enumerate(slice_lines))
                return self._send_json(200, {
                    "ok": True,
                    "path": str(p),
                    "start_line": start,
                    "end_line": end,
                    "total_lines": len(lines),
                    "content": numbered
                })
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        elif self.path == "/api/file/write":
            path_str = str(payload.get("path") or "").strip()
            content = str(payload.get("content") or "")
            overwrite = bool(payload.get("overwrite", True))
            p = Path(path_str).expanduser()
            if p.exists() and not overwrite:
                return self._send_json(400, {"ok": False, "error": "File exists and overwrite is False."})
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content, encoding="utf-8")
                return self._send_json(200, {
                    "ok": True,
                    "path": str(p),
                    "bytes_written": len(content.encode("utf-8"))
                })
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        elif self.path == "/api/file/replace":
            path_str = str(payload.get("path") or "").strip()
            target = str(payload.get("target_content") or "")
            repl = str(payload.get("replacement_content") or "")
            p = Path(path_str).expanduser()
            if not p.exists() or not p.is_file():
                return self._send_json(404, {"ok": False, "error": f"File not found: {path_str}"})
            try:
                content = p.read_text(encoding="utf-8")
                cnt = content.count(target)
                if cnt == 0:
                    return self._send_json(400, {"ok": False, "error": "Target content not found in file."})
                if cnt > 1:
                    return self._send_json(400, {"ok": False, "error": f"Target content occurs {cnt} times. Provide a more unique chunk."})
                p.write_text(content.replace(target, repl, 1), encoding="utf-8")
                return self._send_json(200, {
                    "ok": True,
                    "path": str(p),
                    "message": "Successfully replaced target content."
                })
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        self._send_json(404, {"error": "Endpoint not found"})


def main():
    server = HTTPServer((HOST, PORT), DoshieNodeHandler)
    print(f"🚀 Doshie Node Agent listening on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")


if __name__ == "__main__":
    main()
