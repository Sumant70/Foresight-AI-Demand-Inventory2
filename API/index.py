from http.server import BaseHTTPRequestHandler
import json


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        response = {
            "service": "FORESIGHT Scoring Service",
            "status": "running",
            "endpoints": [
                "/health",
                "/score/{sku_id}",
                "/forecast/{sku_id}",
                "POST /score/batch"
            ]
        }

        body = json.dumps(response).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

        self.wfile.write(body)