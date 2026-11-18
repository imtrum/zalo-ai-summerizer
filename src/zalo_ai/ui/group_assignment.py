"""Assign saved conversations to any number of prompt groups."""

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from zalo_ai.targets.json_store import set_target_groups
from zalo_ai.targets.group_store import load_groups


class GroupAssignmentPanel(ttk.LabelFrame):
    """Choose groups for the currently selected saved conversations."""

    def __init__(
        self,
        parent: tk.Misc,
        target_tree: ttk.Treeview,
        colors: dict[str, str],
        on_status: Callable[[str], None],
        on_updated: Callable[[], None],
    ) -> None:
        super().__init__(parent, text="Prompt groups", padding=8)
        self.target_tree = target_tree
        self.on_status = on_status
        self.on_updated = on_updated
        self.group_ids: list[str] = []
        self.group_list = tk.Listbox(
            self, selectmode=tk.EXTENDED, height=3, exportselection=False
        )
        self.group_list.pack(side="left", fill="x", expand=True)
        self._style_list(self.group_list, colors)
        ttk.Button(
            self,
            text="Set groups for selected conversations",
            command=self._assign,
        ).pack(side="left", padx=(8, 0))
        self.refresh_groups()

    @staticmethod
    def _style_list(widget: tk.Listbox, colors: dict[str, str]) -> None:
        widget.configure(
            background=colors["field"],
            foreground=colors["text"],
            selectbackground=colors["selection"],
            selectforeground="#ffffff",
            highlightthickness=0,
            relief="flat",
            borderwidth=0,
        )

    def refresh_groups(self) -> None:
        groups = load_groups()
        self.group_ids = [group["id"] for group in groups]
        self.group_list.delete(0, "end")
        for group in groups:
            self.group_list.insert("end", group["name"])

    def _assign(self) -> None:
        target_ids = self.target_tree.selection()
        if not target_ids:
            self.on_status("Select one or more saved targets first.")
            return
        group_ids = [
            self.group_ids[index]
            for index in self.group_list.curselection()
        ]
        try:
            for target_id in target_ids:
                set_target_groups(target_id, group_ids)
        except Exception as exc:
            self.on_status(f"Could not update group assignments: {exc}")
            return
        self.on_updated()
        self.on_status(
            f"Set {len(target_ids)} selected conversation(s) to "
            f"{len(group_ids)} group(s)."
        )
