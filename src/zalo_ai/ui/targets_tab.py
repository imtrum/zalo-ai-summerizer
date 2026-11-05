import logging
from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from zalo_ai.targets.json_store import (
    load_targets,
    set_target_enabled,
)
from zalo_ai.workflows import save_discovered_targets
from .theme import Theme


class TargetsTab(Theme):
    """Discover conversations and manage saved targets."""

    def __init__(
        self,
        parent: ttk.Notebook,
        colors: dict[str, str],
        on_refresh: Callable[[], None],
        on_status: Callable[[str], None],
        log: Callable[[str], None],
    ) -> None:
        super().__init__(parent, colors=colors, padding=14)
        self.on_refresh = on_refresh
        self.on_status = on_status
        self.log = log
        self.discovered_conversations: list[dict[str, str]] = []
        self.action_buttons: list[ttk.Button] = []
        self._build()
        self.refresh_saved_targets()

    def _build(self) -> None:
        discovery = ttk.LabelFrame(
            self,
            text="Discover and add conversations",
            padding=10,
        )
        discovery.pack(fill="both", expand=True)

        self.discover_button = ttk.Button(
            discovery,
            text="Refresh conversation list",
            command=self.on_refresh,
        )
        self.discover_button.pack(anchor="w", pady=(0, 8))
        self.action_buttons.append(self.discover_button)

        self.discovered_list = tk.Listbox(
            discovery,
            selectmode=tk.EXTENDED,
            height=8,
            exportselection=False,
        )
        self.discovered_list.pack(fill="both", expand=True)
        self.style_text_widget(self.discovered_list)

        self.add_targets_button = ttk.Button(
            discovery,
            text="Add selected conversations",
            command=self._save_selected_discoveries,
        )
        self.add_targets_button.pack(anchor="w", pady=(8, 0))
        self.action_buttons.append(self.add_targets_button)

        saved = ttk.LabelFrame(
            self,
            text="Saved targets",
            padding=10,
        )
        saved.pack(fill="both", expand=True, pady=(12, 0))

        self.target_tree = ttk.Treeview(
            saved,
            columns=("name", "enabled"),
            show="headings",
            selectmode="extended",
            height=7,
        )
        self.target_tree.heading("name", text="Conversation")
        self.target_tree.heading("enabled", text="Enabled")
        self.target_tree.column("name", width=540, anchor="w")
        self.target_tree.column("enabled", width=100, anchor="center")
        self.target_tree.pack(fill="both", expand=True)

        controls = ttk.Frame(saved)
        controls.pack(anchor="w", pady=(8, 0))

        self.enable_targets_button = ttk.Button(
            controls,
            text="Enable selected",
            command=self._enable_selected_targets,
        )
        self.enable_targets_button.pack(side="left")
        self.action_buttons.append(self.enable_targets_button)

        self.disable_targets_button = ttk.Button(
            controls,
            text="Disable selected",
            command=self._disable_selected_targets,
        )
        self.disable_targets_button.pack(side="left", padx=(8, 0))
        self.action_buttons.append(self.disable_targets_button)

    def set_discoveries(
        self,
        conversations: list[dict[str, str]],
    ) -> None:
        self.discovered_conversations = conversations
        self.discovered_list.delete(0, "end")
        for conversation in conversations:
            self.discovered_list.insert("end", conversation["name"])
        self.on_status(f"Found {len(conversations)} conversations")
        self.log(
            f"Discovered {len(conversations)} conversations."
        )

    def _save_selected_discoveries(self) -> None:
        selected = self.discovered_list.curselection()
        if not selected:
            self.on_status("Select one or more discovered conversations.")
            return

        conversations = [
            self.discovered_conversations[index]
            for index in selected
        ]

        try:
            added_count = save_discovered_targets(conversations)
            self.refresh_saved_targets()
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Could not save selected targets."
            )
            self.on_status(f"Could not save targets: {exc}")
            return

        self.on_status(f"Saved selection; added {added_count} new targets.")
        self.log(
            f"Saved {len(conversations)} selected conversations; "
            f"added {added_count} new targets."
        )

    def refresh_saved_targets(self) -> None:
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)

        try:
            targets = load_targets()
        except Exception as exc:
            self.on_status(f"Could not load targets: {exc}")
            return

        for target in targets:
            self.target_tree.insert(
                "",
                "end",
                iid=target["id"],
                values=(
                    target["name"],
                    "Yes" if target["enabled"] else "No",
                ),
            )

    def _enable_selected_targets(self) -> None:
        self._set_selected_targets_enabled(True)

    def _disable_selected_targets(self) -> None:
        self._set_selected_targets_enabled(False)

    def _set_selected_targets_enabled(self, enabled: bool) -> None:
        selected = self.target_tree.selection()
        if not selected:
            self.on_status("Select one or more saved targets first.")
            return

        try:
            for target_id in selected:
                current_enabled = (
                    self.target_tree.set(target_id, "enabled") == "Yes"
                )
                if current_enabled != enabled:
                    set_target_enabled(target_id, enabled)
            self.refresh_saved_targets()
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Could not update target settings."
            )
            self.on_status(f"Could not update targets: {exc}")
            return

        state = "enabled" if enabled else "disabled"
        self.on_status(
            f"Set {len(selected)} selected target(s) to {state}."
        )
        self.log(
            f"Set {len(selected)} selected target(s) to {state}."
        )
