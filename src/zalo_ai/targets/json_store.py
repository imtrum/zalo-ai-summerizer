
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TARGETS_FILE = PROJECT_ROOT / "data" / "targets.json"


def load_targets() -> list[dict[str, Any]]:
    """Load and validate target configurations."""
    with TARGETS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("The JSON root must be an object.")

    targets = data.get("targets")

    if not isinstance(targets, list):
        raise ValueError("'targets' must be a list.")

    seen_ids: set[str] = set()

    for index, target in enumerate(targets):
        
        target_id = target["id"].strip()

        if target_id in seen_ids:
            raise ValueError(
                f"Duplicate target ID '{target_id}' at index {index}."
            )

        seen_ids.add(target_id)

        if not isinstance(target, dict):
            raise ValueError(f"Target at index {index} must be an object.")

        if not isinstance(target.get("id"), str) or not target["id"].strip():
            raise ValueError(f"Target at index {index} must have a non-empty string 'id'.")

        if not isinstance(target.get("name"), str) or not target["name"].strip():
            raise ValueError(f"Target at index {index} must have a non-empty string 'name'.")

        if not isinstance(target.get("enabled"), bool):
            raise ValueError(f"Target at index {index} must have a boolean 'enabled'.")

    return targets


def get_enabled_targets() -> list[dict[str, Any]]:
    """Return only enabled targets."""
    return [
        target
        for target in load_targets()
        if target["enabled"] is True
    ]