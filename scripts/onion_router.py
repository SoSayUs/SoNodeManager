

import os
import time
import socket
import platform
import shutil
from stem.control import Controller
from stem.process import launch_tor_with_config

def find_free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def find_tor_binary():
    tor_path = shutil.which("tor")
    if tor_path:
        return tor_path

    system = platform.system()
    candidates = []

    if system == "Darwin":
        candidates = [
            "/opt/homebrew/bin/tor",
            "/usr/local/bin/tor"
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/tor",
            "/usr/local/bin/tor"
        ]

    for path in candidates:
        if os.path.exists(path):
            return path

    raise RuntimeError("Tor binary not found. Please install tor and ensure it is accessible.")

TOR_BINARY = find_tor_binary()

BASE_DIR = os.path.abspath("../.data/tor_instance")
DATA_DIR = os.path.join(BASE_DIR, "data")
HS_DIR = os.path.join(BASE_DIR, "hidden_service")
RELAY_NICKNAME = "SonetRelay"

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(HS_DIR, exist_ok=True)
    os.chmod(HS_DIR, 0o700)  # required by Tor


def start_tor():
    ensure_dirs()

    SOCKS_PORT = "19050"
    CONTROL_PORT = "19051"
    HS_LOCAL_PORT = "9909"

    tor_process = launch_tor_with_config(
        tor_cmd=TOR_BINARY,
        config={
            "SocksPort": SOCKS_PORT,
            "ControlPort": CONTROL_PORT,
            "DataDirectory": DATA_DIR,
            "Log": "notice stdout",

            "ORPort": "0",
            "Nickname": RELAY_NICKNAME,
            "ExitPolicy": "reject *:*",

            "HiddenServiceDir": HS_DIR,
            "HiddenServicePort": f"80 127.0.0.1:{HS_LOCAL_PORT}",
            "HiddenServiceVersion": "3",
        },
        take_ownership=True
    )

    print(f"Tor started using {TOR_BINARY}")
    print(f"SOCKS={SOCKS_PORT}, CONTROL={CONTROL_PORT}, HS_LOCAL={HS_LOCAL_PORT}")
    return tor_process, CONTROL_PORT, HS_LOCAL_PORT, SOCKS_PORT

# ---------------- Monitor Tor ----------------
def onion_to_peer_uri(onion_address: str, socks_port: str, virtual_port: int = 8001) -> str:
    return f"socks://127.0.0.1:{socks_port}/{onion_address}:{virtual_port}"

def monitor_tor():
    while True:
        try:
            tor_process, control_port, hs_local_port, socks_port = start_tor()

            with Controller.from_port(port=int(control_port)) as controller:
                controller.authenticate()

                onion_address = None
                print("Waiting for hidden service to be ready...")
                while onion_address is None:
                    hostname_path = os.path.join(HS_DIR, "hostname")
                    if os.path.exists(hostname_path):
                        with open(hostname_path, "r") as f:
                            onion_address = f.read().strip()
                    time.sleep(2)

                print("Hidden service available at:", onion_address)
                print("Tor running. Monitoring... Press Ctrl+C to stop.")
                print(f"Use SOCKS proxy on port {socks_port} to connect to other nodes.")

                tor_process.wait()

        except KeyboardInterrupt:
            print("Stopping Tor...")
            try:
                controller.signal("SHUTDOWN")
            except Exception:
                pass
            break

        except Exception as e:
            print("Tor crashed or failed:", e)

        print("Restarting Tor in 5 seconds...")
        time.sleep(5)

def run_http_server(port):
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import threading

    def server_thread():
        server = HTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
        print(f"HTTP server running on 127.0.0.1:{port}")
        server.serve_forever()

    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

if __name__ == "__main__":
    monitor_tor()
