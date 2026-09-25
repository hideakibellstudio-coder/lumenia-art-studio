"""Config migration and preservation across incompatible application versions."""

import json
import pytest
from ui.infrastructure.config.manager import ConfigManager


def test_legacy_settings_migrate_without_losing_neighbors(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"version": "2.0", "render": {"profile_id": "srgb",
                    "low_latency": False, "deep_color": "false", "undo_limit_mb": -2},
                    "dock": {"speed": "Fast", "hover_delay": "Long (800ms)"}}))
    config = ConfigManager(str(path))
    assert config.get("render", "profile_id") == 0
    assert config.get("render", "low_latency") is False
    assert config.get("render", "deep_color") is False
    assert config.get("render", "undo_limit_mb") == 512
    assert config.get("dock", "speed") == "Rápido"
    assert config.get("dock", "hover_delay") == "Longo (800ms)"
    assert config.save()
    saved = json.loads(path.read_text())
    assert saved["schema_version"] == 1
    assert saved["render"]["profile_id"] == 0


def test_future_configuration_is_never_overwritten(tmp_path):
    path = tmp_path / "config.json"
    original = json.dumps({"schema_version": 99, "future": {"unknown": 123}})
    path.write_text(original)
    config = ConfigManager(str(path))
    errors = []
    config.persistenceFailed.connect(errors.append)
    config.set("theme", "active", "changed")
    config.reset_to_defaults()
    assert not config.save()
    assert errors
    assert path.read_text() == original
    assert not path.with_suffix(".json.bak").exists()


@pytest.mark.parametrize("key,value", [("profile_id", True), ("profile_id", 99),
                                      ("deep_color", "false"), ("undo_limit_mb", 0)])
def test_invalid_render_updates_are_atomic(tmp_path, key, value):
    config = ConfigManager(str(tmp_path / "config.json"))
    before = config.get_section("render")
    with pytest.raises(ValueError):
        config.set_section("render", {"low_latency": not before["low_latency"], key: value})
    assert config.get_section("render") == before
