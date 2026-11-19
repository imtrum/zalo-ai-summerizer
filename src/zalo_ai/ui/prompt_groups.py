"""Group management callbacks for the prompt editor."""

from tkinter import messagebox, simpledialog

from zalo_ai.targets.group_store import (
    create_group,
    delete_group,
    get_group_prompt,
    load_groups,
    rename_group,
)
from zalo_ai.summarizer.prompt_store import load_prompt


class PromptGroups:
    """Manage group selection and group details in a prompt tab."""

    def selected_group_id(self) -> str | None:
        """Return the selected custom group, or None for the shared prompt."""
        return self.group_ids.get(self.group_value.get())

    def refresh_groups(self, selected_id: str | None = None) -> None:
        groups = load_groups()
        self.group_ids = {group["name"]: group["id"] for group in groups}
        values = ["All enabled conversations", *self.group_ids]
        self.group_selector.configure(values=values)
        selected_name = next(
            (group["name"] for group in groups if group["id"] == selected_id),
            None,
        )
        current_id = self.selected_group_id()
        if selected_name:
            self.group_value.set(selected_name)
        elif current_id not in {group["id"] for group in groups}:
            self.group_value.set(values[0])
        self._load_selected_prompt()
        is_custom = self.selected_group_id() is not None
        self.rename_group_button.configure(
            state="normal" if is_custom else "disabled"
        )
        self.delete_group_button.configure(
            state="normal" if is_custom else "disabled"
        )

    def _select_group(self, _event=None) -> None:
        self.refresh_groups(self.selected_group_id())

    def _load_selected_prompt(self) -> None:
        group_id = self.selected_group_id()
        prompt = get_group_prompt(group_id) if group_id else load_prompt()
        self.prompt_editor.delete("1.0", "end")
        self.prompt_editor.insert("1.0", prompt)

    def _new_group(self) -> None:
        name = simpledialog.askstring("New group", "Group name:", parent=self)
        if name is None:
            return
        prompt = self.prompt_editor.get("1.0", "end").strip() or load_prompt()
        try:
            group = create_group(name, prompt)
        except Exception as exc:
            self.on_status(f"Could not create group: {exc}")
            return
        self.refresh_groups(group["id"])
        self.on_groups_changed()
        self.on_status(f"Created prompt group '{group['name']}'.")

    def _rename_group(self) -> None:
        group_id = self.selected_group_id()
        if not group_id:
            return
        current = self.group_value.get()
        name = simpledialog.askstring(
            "Rename group", "Group name:", initialvalue=current, parent=self
        )
        if name is None:
            return
        try:
            rename_group(group_id, name)
        except Exception as exc:
            self.on_status(f"Could not rename group: {exc}")
            return
        self.refresh_groups(group_id)
        self.on_groups_changed()
        self.on_status(f"Renamed prompt group to '{name.strip()}'.")

    def _delete_group(self) -> None:
        group_id = self.selected_group_id()
        if not group_id:
            return
        name = self.group_value.get()
        if not messagebox.askyesno(
            "Delete group",
            f"Delete '{name}' and remove its conversation assignments?",
            parent=self,
        ):
            return
        try:
            delete_group(group_id)
        except Exception as exc:
            self.on_status(f"Could not delete group: {exc}")
            return
        self.refresh_groups()
        self.on_groups_changed()
        self.on_status(f"Deleted prompt group '{name}'.")
