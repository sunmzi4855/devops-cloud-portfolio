"""Simple dependency-free application for DevOps CI/CD demonstration."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            status, data = 200, {'status': 'healthy', 'service': 'cloud-devops-demo'}
        elif self.path == '/':
            status, data = 200, {'message': 'Cloud DevOps Demo', 'health': '/health'}
        else:
            status, data = 404, {'error': 'not found'}
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8080'))), Handler).serve_forever()
