"""Check versions and query the current map without modifying the world."""
import json
import sys

import carla
from scripts.settings import CARLA_VERSION, load_settings


def connect(server):
    client = carla.Client(server["host"], server["port"])
    client.set_timeout(server["timeout_seconds"])
    local, remote = client.get_client_version(), client.get_server_version()
    if local != CARLA_VERSION or remote != CARLA_VERSION:
        raise RuntimeError(f"Expected CARLA {CARLA_VERSION}; client={local}, server={remote}")
    return client


def main():
    try:
        cfg = load_settings()
        client = connect(cfg["server"])
        print(json.dumps({"client_version": client.get_client_version(),
                          "server_version": client.get_server_version(),
                          "current_map": client.get_world().get_map().name}, indent=2))
        print("Connection OK. No map was loaded and no simulation tick was requested.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Connection check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
