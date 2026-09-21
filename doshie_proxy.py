#!/usr/bin/env python3
import http.server
import socketserver
import urllib.request
import sys

PORT = 8080
TARGET_PORT = 5000

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_HEAD(self):
        self._proxy()

    def do_OPTIONS(self):
        self._proxy()

    def _proxy(self):
        target_url = f"http://127.0.0.1:{TARGET_PORT}{self.path}"
        headers = {k: v for k, v in self.headers.items() if k.lower() != 'host'}
        headers['Host'] = f"127.0.0.1:{TARGET_PORT}"

        body = None
        if 'Content-Length' in self.headers:
            length = int(self.headers['Content-Length'])
            body = self.rfile.read(length)

        req = urllib.request.Request(target_url, data=body, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ['transfer-encoding', 'content-encoding']:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ['transfer-encoding', 'content-encoding']:
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
    print(f"Starting Doshie Port 8080 Proxy (Targeting localhost:{TARGET_PORT})...")
    with ThreadedHTTPServer(("0.0.0.0", PORT), ProxyHandler) as httpd:
        httpd.serve_forever()
