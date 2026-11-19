"""Refresh saved target rows and their prompt group labels."""

from zalo_ai.targets.group_store import load_groups
from zalo_ai.targets.json_store import load_targets


class TargetGroups:
    """Target table callbacks shared with the group assignment panel."""

    def refresh_saved_targets(self) -> None:
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)
        try:
            targets = load_targets()
            groups = {group["id"]: group["name"] for group in load_groups()}
        except Exception as exc:
            self.on_status(f"Could not load targets: {exc}")
            return
        for target in targets:
            group_names = [
                groups[group_id]
                for group_id in target.get("groups", [])
                if group_id in groups
            ]
            self.target_tree.insert(
                "",
                "end",
                iid=target["id"],
                values=(
                    target["name"],
                    ", ".join(group_names) or "—",
                    "Yes" if target["enabled"] else "No",
                ),
            )

    def refresh_groups(self) -> None:
        self.group_panel.refresh_groups()
        self.refresh_saved_targets()
