"""Manage named conversation groups and their prompts."""

from uuid import uuid4

from .json_store import _read_data, _write_data

ALL_GROUP_NAME = "All enabled conversations"


def load_groups() -> list[dict[str, str]]:
    """Load and validate saved groups."""
    groups = _read_data().get("groups", [])
    if not isinstance(groups, list):
        raise ValueError("'groups' must be a list.")
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for index, group in enumerate(groups):
        if not isinstance(group, dict) or not all(
            isinstance(group.get(key), str) and group[key].strip()
            for key in ("id", "name", "prompt")
        ):
            raise ValueError(
                f"Group at index {index} requires an ID, name, and prompt."
            )
        group_id = group["id"].strip()
        name = group["name"].strip().casefold()
        if group_id in seen_ids or name in seen_names:
            raise ValueError("Group IDs and names must be unique.")
        seen_ids.add(group_id)
        seen_names.add(name)
    return groups


def get_group_prompt(group_id: str) -> str:
    """Return a group's saved prompt."""
    for group in load_groups():
        if group["id"] == group_id:
            return group["prompt"]
    raise ValueError(f"Group '{group_id}' was not found.")


def create_group(name: str, prompt: str) -> dict[str, str]:
    """Create a group with a non-empty name and prompt."""
    name = name.strip() if isinstance(name, str) else ""
    prompt = prompt.strip() if isinstance(prompt, str) else ""
    if not name:
        raise ValueError("Group name must not be empty.")
    if name.casefold() == ALL_GROUP_NAME.casefold():
        raise ValueError(f"'{ALL_GROUP_NAME}' is reserved.")
    if not prompt:
        raise ValueError("Group prompt must not be empty.")
    data = _read_data()
    groups = data.setdefault("groups", [])
    if any(group["name"].casefold() == name.casefold() for group in groups):
        raise ValueError(f"A group named '{name}' already exists.")
    group = {"id": uuid4().hex, "name": name, "prompt": prompt}
    groups.append(group)
    _write_data(data)
    return group


def save_group_prompt(group_id: str, prompt: str) -> None:
    """Update a group's prompt."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must not be empty.")
    data = _read_data()
    for group in data.get("groups", []):
        if group.get("id") == group_id:
            group["prompt"] = prompt.strip()
            _write_data(data)
            return
    raise ValueError(f"Group '{group_id}' was not found.")


def rename_group(group_id: str, name: str) -> None:
    """Rename a group and preserve its prompt and membership."""
    name = name.strip() if isinstance(name, str) else ""
    if not name:
        raise ValueError("Group name must not be empty.")
    if name.casefold() == ALL_GROUP_NAME.casefold():
        raise ValueError(f"'{ALL_GROUP_NAME}' is reserved.")
    data = _read_data()
    groups = data.get("groups", [])
    if any(
        group.get("id") != group_id
        and group.get("name", "").casefold() == name.casefold()
        for group in groups
    ):
        raise ValueError(f"A group named '{name}' already exists.")
    for group in groups:
        if group.get("id") == group_id:
            group["name"] = name
            _write_data(data)
            return
    raise ValueError(f"Group '{group_id}' was not found.")


def delete_group(group_id: str) -> None:
    """Delete a group and remove its memberships."""
    data = _read_data()
    groups = data.get("groups", [])
    remaining = [group for group in groups if group.get("id") != group_id]
    if len(remaining) == len(groups):
        raise ValueError(f"Group '{group_id}' was not found.")
    data["groups"] = remaining
    for target in data["targets"]:
        target["groups"] = [
            value for value in target.get("groups", [])
            if value != group_id
        ]
    _write_data(data)
