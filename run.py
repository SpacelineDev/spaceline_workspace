from __future__ import annotations

import socket
import threading
import time
import webbrowser

import uvicorn

# Import the app directly so frozen-executable analysis sees the ASGI entry point.
from app.main import app
from app.version import APP_VERSION

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_SCAN_END = 8799


def choose_port(start_port: int = DEFAULT_PORT, end_port: int = PORT_SCAN_END, host: str = HOST) -> int:
    """Return the first available loopback port so an older Spaceline process cannot be mistaken for this one."""
    if not (1 <= int(start_port) <= int(end_port) <= 65535):
        raise ValueError("Port range must be between 1 and 65535, with start_port <= end_port.")
    for port in range(int(start_port), int(end_port) + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No available local port in range {start_port}-{end_port}. Close an old Spaceline instance or another local service, then restart.")


if __name__ == "__main__":
    port = choose_port()
    url = f"http://{HOST}:{port}"
    print(f"Spaceline {APP_VERSION} is starting at {url}", flush=True)

    def open_browser() -> None:
        time.sleep(1.4)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=port, reload=False, log_level="warning")
