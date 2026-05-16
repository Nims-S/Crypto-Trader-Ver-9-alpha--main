from __future__ import annotations

from pathlib import Path

from ver9 import registry



def test_registry_recovers_from_trailing_corruption(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    registry_path.write_text(
        '{"created_at":"x","updated_at":"x","entries":{"a":{"strategy_id":"a"}}} trailing-data',
        encoding="utf-8",
    )

    payload = registry.load_registry()

    assert payload["entries"]
    assert registry_path.exists()
    backups = list(tmp_path.glob("*.bak"))
    assert backups



def test_registry_recovers_from_invalid_json(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    registry_path.write_text('{"broken": ', encoding="utf-8")

    payload = registry.load_registry()

    assert payload["entries"] == {}
    assert registry_path.exists()
    backups = list(tmp_path.glob("*.bak"))
    assert backups



def test_registry_atomic_save(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(registry, "REGISTRY_PATH", registry_path)

    registry.save_registry(
        {
            "entries": {
                "alpha": {
                    "strategy_id": "alpha",
                    "status": "validated",
                }
            }
        }
    )

    payload = registry.load_registry()
    assert payload["entries"]["alpha"]["status"] == "validated"
