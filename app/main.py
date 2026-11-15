"""Dependency-free HTTP service for the DevOps portfolio demo."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REQUEST_COUNT = {}
COUNTER_LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        with COUNTER_LOCK:
            REQUEST_COUNT[path] = REQUEST_COUNT.get(path, 0) + 1

        if path == "/metrics":
            with COUNTER_LOCK:
                counts = dict(REQUEST_COUNT)
            lines = [
                "# HELP devops_http_requests_total Total HTTP requests by path.",
                "# TYPE devops_http_requests_total counter",
            ]
            for endpoint, count in sorted(counts.items()):
                safe = endpoint.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                lines.append(f'devops_http_requests_total{{path="{safe}"}} {count}')
            body = ("\n".join(lines) + "\n").encode()
            content_type = "text/plain; version=0.0.4; charset=utf-8"
            status = 200
        else:
            if path == "/health":
                status, data = 200, {"status": "healthy", "service": "cloud-devops-demo"}
            elif path == "/":
                status, data = 200, {"message": "Cloud DevOps Demo", "health": "/health", "metrics": "/metrics"}
            else:
                status, data = 404, {"error": "not found"}
            body = json.dumps(data).encode()
            content_type = "application/json"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
