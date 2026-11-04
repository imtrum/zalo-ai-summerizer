import logging
from collections.abc import Callable
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from zalo_ai.summarizer.prompt_store import (
    DEFAULT_PROMPT,
    load_prompt,
    save_prompt,
)
from .theme import style_text_widget


class PromptTab(ttk.Frame):
    """Edit and save the prompt used for future summaries."""

    def __init__(
        self,
        parent: ttk.Notebook,
        colors: dict[str, str],
        on_status: Callable[[str], None],
        log: Callable[[str], None],
    ) -> None:
        super().__init__(parent, padding=14)
        self.colors = colors
        self.on_status = on_status
        self.log = log
        self.action_buttons: list[ttk.Button] = []
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self,
            text=(
                "Edit the instructions Gemini should follow. Conversation "
                "IDs and messages are added automatically."
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
        style_text_widget(self.prompt_editor, self.colors)
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

    def _save_prompt(self) -> None:
        prompt = self.prompt_editor.get("1.0", "end").strip()
        try:
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
