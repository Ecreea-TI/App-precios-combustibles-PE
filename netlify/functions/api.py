from http.server import BaseHTTPRequestHandler
from main import app
from mangum import Mangum

handler = Mangum(app)

class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = handler

    def handle_request(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return self.handler(self.path, None)

    def do_GET(self):
        return self.handle_request()

    def do_POST(self):
        return self.handle_request()

    def do_OPTIONS(self):
        return self.handle_request()