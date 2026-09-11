"""Serve the temporal converter on loopback only, using Python's standard library."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = {"/": "index.html", "/index.html": "index.html",
          "/app.js": "app.js", "/converter.js": "converter.js"}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] not in ASSETS:
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if self.path.split("?", 1)[0] not in ASSETS:
            self.send_error(404)
            return
        super().do_HEAD()

    def translate_path(self, path):
        return str(ROOT / ASSETS.get(path.split("?", 1)[0], "index.html"))

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError as error:
        parser.exit(1, f"Could not start local server: {error}. Try --port 8001.\n")
    print(f"Open http://127.0.0.1:{args.port}/", flush=True)
    print("Press Ctrl+C to stop. Reports are processed in your browser.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
