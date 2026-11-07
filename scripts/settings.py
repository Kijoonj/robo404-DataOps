"""Read the shared environment contract without importing CARLA."""
import math
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CARLA_VERSION = "0.9.16"
PYTHON_VERSION = (3, 11)


def _keys(value, template, name="config"):
    if not isinstance(value, dict) or set(value) != set(template):
        raise ValueError(f"{name} must contain exactly: {', '.join(template)}")
    for key, nested in template.items():
        if isinstance(nested, dict):
            _keys(value[key], nested, f"{name}.{key}")


def _number(value, name, lower, upper, integer=False):
    expected = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, expected):
        raise ValueError(f"{name} must be {'an integer' if integer else 'a number'}")
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")


def load_settings(simulation=None, sensors=None):
    paths = [Path(simulation or ROOT / "config/simulation.yaml"),
             Path(sensors or ROOT / "config/sensors.yaml")]
    try:
        cfg, sensor = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in paths]
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc
    _keys(cfg, {"server": dict.fromkeys(["host", "port", "timeout_seconds"]),
                "world": dict.fromkeys(["map", "synchronous_mode", "fixed_delta_seconds", "seed", "weather"]),
                "ego": dict.fromkeys(["blueprint", "spawn_index"]),
                "validation": dict.fromkeys(["frames"])})
    _keys(sensor, {"rgb": {**dict.fromkeys(["width", "height", "fov", "sensor_tick"]),
                           "transform": dict.fromkeys(["x", "y", "z", "pitch", "yaw", "roll"])}})
    for section, key in [("server", "host"), ("world", "map"), ("world", "weather"), ("ego", "blueprint")]:
        value = cfg[section][key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{section}.{key} must be a nonempty string")
    for section, key, lo, hi, integer in [
        ("server", "port", 1, 65533, True), ("server", "timeout_seconds", 1, 300, False),
        ("world", "fixed_delta_seconds", .001, .1, False), ("world", "seed", 0, 2**31-1, True),
        ("ego", "spawn_index", 0, 100000, True), ("validation", "frames", 1, 100, True),
    ]:
        _number(cfg[section][key], f"{section}.{key}", lo, hi, integer)
    if cfg["world"]["synchronous_mode"] is not True:
        raise ValueError("The shared environment requires synchronous_mode: true")
    rgb = sensor["rgb"]
    for key, lo, hi, integer in [("width", 16, 4096, True), ("height", 16, 4096, True),
                                ("fov", 1, 179, False), ("sensor_tick", 0, 10, False)]:
        _number(rgb[key], f"rgb.{key}", lo, hi, integer)
    ratio = rgb["sensor_tick"] / cfg["world"]["fixed_delta_seconds"]
    if rgb["sensor_tick"] != 0 and (ratio < 1 or not math.isclose(ratio, round(ratio), abs_tol=1e-8)):
        raise ValueError("rgb.sensor_tick must be zero or a positive multiple of fixed_delta_seconds")
    for key, value in rgb["transform"].items():
        _number(value, f"rgb.transform.{key}", -10000, 10000)
    return {**cfg, "sensors": sensor}
