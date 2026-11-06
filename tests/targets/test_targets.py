
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


def test_load_targets(tmp_path, monkeypatch):
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        """
        {
            "targets": [
                {
                    "id": "example_group_001",
                    "name": "Example Zalo Group",
                    "enabled": true
                }
            ]
        }
        """,
        encoding="utf-8",
    )

    from zalo_ai.targets import json_store

    monkeypatch.setattr(json_store, "TARGETS_FILE", targets_file)

    targets = load_targets()

    assert len(targets) == 1
    assert targets[0]["id"] == "example_group_001"
    assert targets[0]["name"] == "Example Zalo Group"



def test_add_target(tmp_path, monkeypatch):
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        '{"targets": []}',
        encoding="utf-8",
    )
    monkeypatch.setattr(json_store, "TARGETS_FILE", targets_file)

    json_store.add_target(
        {"id": "group_001", "name": "Group A", "enabled": True}
    )

    assert json_store.load_targets() == [
        {"id": "group_001", "name": "Group A", "enabled": True}
    ]


def test_add_existing_target_does_not_duplicate(tmp_path, monkeypatch):
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        '{"targets": [{"id": "group_001", "name": "Group A", "enabled": true}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(json_store, "TARGETS_FILE", targets_file)

    json_store.add_target(
        {"id": "group_001", "name": "Group A", "enabled": True}
    )

    assert len(json_store.load_targets()) == 1


def test_set_target_enabled(tmp_path, monkeypatch):
    targets_file = tmp_path / "targets.json"
    targets_file.write_text(
        '{"targets": [{"id": "group_001", "name": "Group A", "enabled": true}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(json_store, "TARGETS_FILE", targets_file)

    json_store.set_target_enabled("group_001", False)

    assert json_store.load_targets() == [
        {"id": "group_001", "name": "Group A", "enabled": False}
    ]
