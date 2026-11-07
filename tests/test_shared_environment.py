"""Offline checks for the shared settings contract and safe world cleanup."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import carla
import yaml

from scripts.check_connection import connect
from scripts.check_world import apply_and_check
from scripts.settings import ROOT, load_settings


class SettingsTests(unittest.TestCase):
    def test_shared_files_are_valid(self):
        cfg = load_settings()
        self.assertEqual(cfg["world"]["map"], "Town03")
        self.assertNotIn("agent", cfg)
        self.assertNotIn("run", cfg)

    def test_invalid_common_settings_are_rejected(self):
        original = yaml.safe_load((ROOT / "config/simulation.yaml").read_text(encoding="utf-8"))
        cases = [("world", "synchronous_mode", False), ("world", "fixed_delta_seconds", .2),
                 ("world", "seed", True), ("server", "port", 65534),
                 ("ego", "spawn_index", -1), ("validation", "frames", 0)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "simulation.yaml"
            for section, key, value in cases:
                with self.subTest(key=key):
                    cfg = copy.deepcopy(original)
                    cfg[section][key] = value
                    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_settings(path)

    def test_sensor_period_must_align_with_simulation_ticks(self):
        sensor = yaml.safe_load((ROOT / "config/sensors.yaml").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sensors.yaml"
            for tick in (.01, .075, float("nan")):
                with self.subTest(sensor_tick=tick):
                    sensor["rgb"]["sensor_tick"] = tick
                    path.write_text(yaml.safe_dump(sensor), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_settings(sensors=path)

    def test_yaml_typo_and_unknown_keys_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "simulation.yaml"
            for text in ("world: [", "unexpected: true"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_settings(path)


class ServerChecksTests(unittest.TestCase):
    def test_version_mismatch_is_rejected_without_world_changes(self):
        client = Mock()
        client.get_client_version.return_value = "0.9.16"
        client.get_server_version.return_value = "0.9.15"
        with patch("scripts.check_connection.carla.Client", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "client=0.9.16, server=0.9.15"):
                connect(load_settings()["server"])
        client.load_world.assert_not_called()

    def make_world(self):
        client, world = Mock(), Mock()
        client.get_world.return_value.get_settings.return_value = carla.WorldSettings()
        client.load_world.return_value = world
        original = carla.WorldSettings()
        applied = carla.WorldSettings(synchronous_mode=True, fixed_delta_seconds=.05)
        world.get_settings.side_effect = [original, carla.WorldSettings(), applied]
        original_weather = carla.WeatherParameters.CloudyNoon
        world.get_weather.side_effect = [original_weather, carla.WeatherParameters.ClearNoon]
        world.get_map.return_value.name = "Carla/Maps/Town03"
        world.get_map.return_value.get_spawn_points.return_value = [carla.Transform()]
        return client, world, original, original_weather

    def test_environment_check_restores_settings_without_spawning_actors(self):
        client, world, original, original_weather = self.make_world()
        report = apply_and_check(client, load_settings())
        self.assertTrue(report["settings_and_weather_restored"])
        self.assertEqual(world.tick.call_count, 10)
        world.apply_settings.assert_called_with(original)
        world.set_weather.assert_called_with(original_weather)
        world.spawn_actor.assert_not_called()
        world.try_spawn_actor.assert_not_called()

    def test_tick_failure_still_restores_settings(self):
        client, world, original, original_weather = self.make_world()
        world.tick.side_effect = RuntimeError("server disconnected")
        with self.assertRaisesRegex(RuntimeError, "server disconnected"):
            apply_and_check(client, load_settings())
        world.apply_settings.assert_called_with(original)
        world.set_weather.assert_called_with(original_weather)

    def test_existing_tick_owner_is_not_disturbed(self):
        client = Mock()
        client.get_world.return_value.get_settings.return_value = carla.WorldSettings(synchronous_mode=True)
        with self.assertRaisesRegex(RuntimeError, "already synchronous"):
            apply_and_check(client, load_settings())
        client.load_world.assert_not_called()


if __name__ == "__main__":
    unittest.main()
