import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8081
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "dijizu_agent_new"
HTML_FILE = ROOT_DIR / "scripts" / "agent_editor.html"

class AgentEditorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            if HTML_FILE.exists():
                with open(HTML_FILE, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b"agent_editor.html not found.")
            return

        elif self.path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-type", "application/json; charset=utf-8")
            self.end_headers()
            
            # List all json files in DATA_DIR
            files = []
            if DATA_DIR.exists():
                for f in DATA_DIR.glob("*.json"):
                    files.append(f.name)
            self.wfile.write(json.dumps(files, ensure_ascii=False).encode("utf-8"))
            return

        elif self.path.startswith("/api/agents/"):
            filename = urllib.parse.unquote(self.path.split("/")[-1])
            filepath = DATA_DIR / filename
            if filepath.exists() and filepath.is_file():
                self.send_response(200)
                self.send_header("Content-type", "application/json; charset=utf-8")
                self.end_headers()
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, f"File not found: {filename}")
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        if self.path.startswith("/api/agents/"):
            filename = urllib.parse.unquote(self.path.split("/")[-1])
            # Ensure safe filename
            if "/" in filename or "\\" in filename:
                self.send_error(400, "Invalid filename")
                return

            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                # Validate JSON before saving
                parsed = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON data")
                return

            filepath = DATA_DIR / filename
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"Saved {filename}"}).encode("utf-8"))
            return

        self.send_error(404, "Not found")

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, AgentEditorHandler)
    print(f"Agent Editor Server running at http://localhost:{PORT}")
    print(f"Serving data from: {DATA_DIR}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
