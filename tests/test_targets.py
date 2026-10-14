
from zalo_ai.targets.json_store import (
    load_targets,
    get_enabled_targets,
)


def test_load_targets():
    targets = load_targets()

    assert len(targets) >= 1
    assert targets[0]["id"] == "example_group_001"
    assert targets[0]["name"] == "Example Zalo Group"


def test_get_enabled_targets():
    targets = get_enabled_targets()

    assert all(target["enabled"] is True for target in targets)


def test_disabled_targets_are_excluded():
    targets = load_targets()
    enabled_targets = get_enabled_targets()

    disabled_ids = {
        target["id"]
        for target in targets
        if not target["enabled"]
    }

    assert all(
        target["id"] not in disabled_ids
        for target in enabled_targets
    )


import json

import pytest

from zalo_ai.targets import json_store


def test_load_targets_rejects_duplicate_ids(tmp_path, monkeypatch):
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        json.dumps({
            "targets": [
                {
                    "id": "group_001",
                    "name": "Group A",
                    "enabled": True,
                },
                {
                    "id": "group_001",
                    "name": "Group B",
                    "enabled": True,
                },
            ]
        }),
        encoding="utf-8",
    )

    monkeypatch.setattr(json_store, "TARGETS_FILE", targets_file)

    with pytest.raises(ValueError, match="Duplicate target ID"):
        json_store.load_targets()