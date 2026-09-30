"""Open the website in your browser over a local address: python serve.py
This avoids the restrictions browsers put on pages opened straight from a folder. Press Ctrl+C to stop."""
import http.server
import socketserver
import threading
import webbrowser
from functools import partial
from pathlib import Path

PORT = 8770
SITE = Path(__file__).resolve().parent / "site"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


if __name__ == "__main__":
    handler = partial(Quiet, directory=str(SITE))
    with socketserver.TCPServer(("127.0.0.1", PORT), handler) as server:
        url = f"http://localhost:{PORT}/"
        print(f"Argos Monitor is at {url}  (Ctrl+C to stop)")
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Stopped.")
