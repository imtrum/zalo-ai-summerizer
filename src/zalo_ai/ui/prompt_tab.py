from collections.abc import Callable
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .prompt_groups import PromptGroups
from zalo_ai.summarizer.prompt_store import (
    DEFAULT_PROMPT,
    load_prompt,
    save_prompt,
)
from .theme import Theme


class PromptTab(PromptGroups, Theme):
    """Edit and save the prompt used for future summaries."""

    def __init__(
        self,
        parent: ttk.Notebook,
        colors: dict[str, str],
        on_status: Callable[[str], None],
        log: Callable[[str], None],
        on_groups_changed: Callable[[], None],
    ) -> None:
        super().__init__(parent, colors=colors, padding=14)
        self.on_status = on_status
        self.log = log
        self.on_groups_changed = on_groups_changed
        self.group_ids: dict[str, str] = {}
        self.group_value = tk.StringVar()
        self.action_buttons: list[ttk.Button] = []
        self._build()

    def _build(self) -> None:
        group_controls = ttk.Frame(self)
        group_controls.pack(fill="x", pady=(0, 8))
        ttk.Label(group_controls, text="Prompt group").pack(side="left")
        self.group_value.set("All enabled conversations")
        self.group_selector = ttk.Combobox(
            group_controls,
            textvariable=self.group_value,
            state="readonly",
            width=30,
        )
        self.group_selector.pack(side="left", padx=(8, 10))
        self.group_selector.bind("<<ComboboxSelected>>", self._select_group)
        self.new_group_button = ttk.Button(
            group_controls, text="New group", command=self._new_group
        )
        self.new_group_button.pack(side="left")
        self.rename_group_button = ttk.Button(
            group_controls, text="Rename", command=self._rename_group
        )
        self.rename_group_button.pack(side="left", padx=(6, 0))
        self.delete_group_button = ttk.Button(
            group_controls, text="Delete", command=self._delete_group
        )
        self.delete_group_button.pack(side="left", padx=(6, 0))
        ttk.Label(
            self,
            text=(
                "Create prompt groups and edit their instructions. "
                "Conversations can belong to multiple groups."
            ),
            wraplength=800,
        ).pack(anchor="w", pady=(0, 8))

        self.prompt_editor = ScrolledText(
            self,
            height=18,
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.prompt_editor.pack(fill="both", expand=True)
        self.style_text_widget(self.prompt_editor)
        self.prompt_editor.insert("1.0", load_prompt())

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(8, 0))

        self.save_prompt_button = ttk.Button(
            controls,
            text="Save prompt",
            command=self._save_prompt,
        )
        self.save_prompt_button.pack(side="left")
        self.action_buttons.append(self.save_prompt_button)

        self.reset_prompt_button = ttk.Button(
            controls,
            text="Restore default",
            command=self._restore_default_prompt,
        )
        self.reset_prompt_button.pack(side="left", padx=(8, 0))
        self.action_buttons.append(self.reset_prompt_button)
        self.refresh_groups()

    def _save_prompt(self) -> None:
        prompt = self.prompt_editor.get("1.0", "end").strip()
        try:
            group_id = self.selected_group_id()
            if group_id:
                save_group_prompt(group_id, prompt)
            else:
                save_prompt(prompt)
        except Exception as exc:
            self.on_status(f"Could not save prompt: {exc}")
            return

        self.on_status("Prompt saved for future summaries.")
        self.log("Saved the custom summarization prompt.")

    def _restore_default_prompt(self) -> None:
        self.prompt_editor.delete("1.0", "end")
        self.prompt_editor.insert("1.0", DEFAULT_PROMPT)
        self.on_status("Default prompt loaded. Select Save prompt to keep it.")
