
import json
from typing import Any

from zalo_ai.paths import PROJECT_ROOT, TARGETS_FILE as DEFAULT_TARGETS_FILE


TARGETS_FILE = DEFAULT_TARGETS_FILE


def ensure_targets_file() -> None:
    """Create an empty target store when the project has none yet."""
    if TARGETS_FILE.exists():
        return

    TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGETS_FILE.write_text(
        '{"targets": []}\n',
        encoding="utf-8",
    )


def _read_data() -> dict[str, Any]:
    """Read the target JSON document."""
    with TARGETS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("The JSON root must be an object.")

    if not isinstance(data.get("targets"), list):
        raise ValueError("'targets' must be a list.")

    return data


def _write_data(data: dict[str, Any]) -> None:
    """Write the target JSON document."""
    with TARGETS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _validate_target(target: Any, index: int) -> None:
    """Validate one target entry."""
    if not isinstance(target, dict):
        raise ValueError(f"Target at index {index} must be an object.")

    if not isinstance(target.get("id"), str) or not target["id"].strip():
        raise ValueError(
            f"Target at index {index} must have a non-empty string 'id'."
        )

    if not isinstance(target.get("name"), str) or not target["name"].strip():
        raise ValueError(
            f"Target at index {index} must have a non-empty string 'name'."
        )

    if not isinstance(target.get("enabled"), bool):
        raise ValueError(
            f"Target at index {index} must have a boolean 'enabled'."
        )
    groups = target.get("groups", [])
    if not isinstance(groups, list) or not all(
        isinstance(group_id, str) for group_id in groups
    ):
        raise ValueError(
            f"Target at index {index} must have a list of group IDs."
        )


def load_targets() -> list[dict[str, Any]]:
    """Load and validate target configurations."""
    targets = _read_data()["targets"]
    seen_ids: set[str] = set()

    for index, target in enumerate(targets):
        _validate_target(target, index)
        target_id = target["id"].strip()

        if target_id in seen_ids:
            raise ValueError(f"Duplicate target ID '{target_id}'.")

        seen_ids.add(target_id)

    return targets


def get_enabled_targets(
    group_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return enabled targets, optionally limited to one group."""
    if group_id is not None:
        from .group_store import load_groups

        if group_id not in {group["id"] for group in load_groups()}:
            raise ValueError(f"Group '{group_id}' was not found.")
    return [
        target
        for target in load_targets()
        if target["enabled"] is True
        and (
            group_id is None
            or group_id in target.get("groups", [])
        )
    ]


def set_target_groups(target_id: str, group_ids: list[str]) -> None:
    """Replace a target's group assignments."""
    from .group_store import load_groups

    known_ids = {group["id"] for group in load_groups()}
    if any(group_id not in known_ids for group_id in group_ids):
        raise ValueError("One or more selected groups no longer exist.")
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("A target cannot be assigned to a group twice.")
    data = _read_data()
    for target in data["targets"]:
        if target.get("id") == target_id:
            target["groups"] = group_ids.copy()
            _write_data(data)
            return
    raise ValueError(f"Target '{target_id}' was not found.")


def add_target(target: dict[str, Any]) -> None:
    """Add a target unless its ID already exists."""
    _validate_target(target, 0)
    data = _read_data()

    existing_ids = {
        item["id"]
        for item in data["targets"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    if target["id"] in existing_ids:
        return

    data["targets"].append(target.copy())
    _write_data(data)


def set_target_enabled(target_id: str, enabled: bool) -> None:
    """Enable or disable an existing target."""
    if not isinstance(enabled, bool):
        raise ValueError("'enabled' must be a boolean.")

    data = _read_data()

    for target in data["targets"]:
        if target.get("id") == target_id:
            target["enabled"] = enabled
            _write_data(data)
            return

    raise ValueError(f"Target '{target_id}' was not found.")


def add_selected_targets(
    conversations: list[dict[str, str]],
) -> int:
    """Add discovered conversations without duplicating existing targets."""
    data = _read_data()
    targets = data["targets"]
    targets_by_id = {
        target["id"]: target
        for target in targets
        if isinstance(target, dict) and isinstance(target.get("id"), str)
    }

    added_count = 0

    for conversation in conversations:
        target_id = conversation.get("id", "").strip()
        name = conversation.get("name", "").strip()

        if not target_id or not name:
            continue

        if target_id in targets_by_id:
            # Refresh the name without changing the enabled setting.
            targets_by_id[target_id]["name"] = name
            continue

        target = {
            "id": target_id,
            "name": name,
            "enabled": True,
        }
        targets.append(target)
        targets_by_id[target_id] = target
        added_count += 1

    _write_data(data)
    return added_count
