# Picalor dev server
# 2022-10-26 Ulrich Lukas
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

if os.name == "nt":
    BASE_DIR = r"D:\mysrc\Picalor\picalor_gui\uibuilder"
else:
    BASE_DIR = os.path.expanduser("~/mysrc/Picalor/picalor_gui/uibuilder")

APP_SUBDIR = "/app/src"
VENDOR_SUBDIR = "/node_modules"

APP_PATH = "/app"
VENDOR_PATH = "/uibuilder/vendor"

INDEX = "/app/index.html"

HOST = "localhost"
PORT = 1880

class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        if (not self.path.startswith(APP_PATH)
            and not self.path.startswith(VENDOR_PATH)
            ):
            self.send_response(301)
            self.send_header('Location', INDEX)
            self.end_headers()
        else:
            super().do_GET()

    def translate_path(self, path: str) -> str:
        if path.startswith(APP_PATH):
            tail = path[len(APP_PATH):]
            trans_path = f"{APP_SUBDIR}{tail}"
        elif path.startswith(VENDOR_PATH):
            tail = path[len(VENDOR_PATH):]
            trans_path = f"{VENDOR_SUBDIR}{tail}"
        supertrans = super().translate_path(trans_path.replace("\\", "/"))
        print(f"Serving file: {supertrans}\n")
        return supertrans

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

def main():
    print(f"Picalor HTTP dev server running on socket:  http://{HOST}:{PORT}\n"
          "Press CTRL-C to exit!"
          )
    httpd = HTTPServer((HOST, PORT), StaticHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("User exit...")

if __name__ == "__main__":
    main()
