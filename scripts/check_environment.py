"""Validate the local Python environment and YAML without starting a server."""
import argparse
from contextlib import ExitStack
from importlib.metadata import version
import json
import socket
import sys

from scripts.settings import CARLA_VERSION, PYTHON_VERSION, load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-ports", action="store_true", help="Probe server ports; CARLA must be stopped")
    args = parser.parse_args()
    try:
        cfg = load_settings()
        if sys.version_info[:2] != PYTHON_VERSION or sys.prefix == sys.base_prefix:
            raise RuntimeError("Use a project virtual environment created with Python 3.11 x64")
        if sys.maxsize <= 2**32:
            raise RuntimeError("Use 64-bit Python")
        installed = version("carla")
        if installed != CARLA_VERSION:
            raise RuntimeError(f"Expected carla=={CARLA_VERSION}; installed={installed}")
        import carla  # Verify native API import; no controls or actors are created.
        result = {"python": sys.version.split()[0], "executable": sys.executable,
                  "carla": installed, "PyYAML": version("PyYAML"),
                  "configuration": "valid", "configured_map": cfg["world"]["map"]}
        if args.check_ports:
            ports = list(range(cfg["server"]["port"], cfg["server"]["port"] + 3))
            with ExitStack() as stack:
                for port in ports:
                    sock = stack.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
                    sock.bind(("0.0.0.0", port))
                    sock.listen(128)
            result["port_probe"] = {"status": "passed", "ports": ports}
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(f"Environment check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
