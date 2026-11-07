"""Temporarily validate shared world settings. Does not spawn or drive actors."""
import argparse
import json
import math
import random
import sys

import carla
from scripts.check_connection import connect
from scripts.settings import load_settings


def apply_and_check(client, cfg):
    spec = cfg["world"]
    preset = getattr(carla.WeatherParameters, spec["weather"], None)
    if not isinstance(preset, carla.WeatherParameters):
        raise ValueError(f"Unknown weather preset: {spec['weather']}")
    if client.get_world().get_settings().synchronous_mode:
        raise RuntimeError("Server is already synchronous; stop its tick owner before this check")
    world = client.load_world(spec["map"])
    original_settings, original_weather = world.get_settings(), world.get_weather()
    try:
        blueprints = world.get_blueprint_library()
        blueprints.find(cfg["ego"]["blueprint"])
        blueprints.find("sensor.camera.rgb")
        spawn_count = len(world.get_map().get_spawn_points())
        if cfg["ego"]["spawn_index"] >= spawn_count:
            raise ValueError(f"spawn_index out of range; map has {spawn_count} spawn points")
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = spec["fixed_delta_seconds"]
        settings.substepping = True
        settings.max_substep_delta_time = .01
        settings.max_substeps = 10
        world.apply_settings(settings)
        world.set_weather(preset)
        world.set_pedestrians_seed(spec["seed"])
        random.seed(spec["seed"])
        for _ in range(cfg["validation"]["frames"]):
            world.tick(cfg["server"]["timeout_seconds"])
        actual = world.get_settings()
        if (not actual.synchronous_mode or actual.fixed_delta_seconds is None
                or not math.isclose(actual.fixed_delta_seconds, spec["fixed_delta_seconds"])):
            raise RuntimeError("Server did not apply the configured synchronous timestep")
        if world.get_map().name.split("/")[-1] != spec["map"]:
            raise RuntimeError("Server map does not match the configured map")
        weather = world.get_weather()
        if any(not math.isclose(getattr(weather, key), getattr(preset, key), abs_tol=1e-5)
               for key in ("cloudiness", "precipitation", "sun_altitude_angle")):
            raise RuntimeError("Server weather does not match the configured preset")
        report = {"map": world.get_map().name, "weather": spec["weather"],
                  "synchronous_mode_during_check": actual.synchronous_mode,
                  "fixed_delta_seconds": actual.fixed_delta_seconds,
                  "seed": spec["seed"], "frames_checked": cfg["validation"]["frames"],
                  "ego_blueprint_available": cfg["ego"]["blueprint"],
                  "actors_spawned": 0}
    finally:
        try:
            world.set_weather(original_weather)
        finally:
            world.apply_settings(original_settings)
    return {**report, "settings_and_weather_restored": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", required=True,
                        help="Confirm map reload; existing actors on this local server will be removed")
    parser.parse_args()
    try:
        cfg = load_settings()
        report = apply_and_check(connect(cfg["server"]), cfg)
        print(json.dumps(report, indent=2))
        print("World check OK. Map remains loaded; temporary settings and weather were restored.")
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"World check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
