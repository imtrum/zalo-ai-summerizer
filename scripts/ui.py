import logging
import queue
import threading
import tkinter as tk
from datetime import datetime, timedelta, timezone
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from zalo_ai.config.logging_config import setup_logging
from zalo_ai.summarizer.prompt_store import (
    DEFAULT_PROMPT,
    load_prompt,
    save_prompt,
)
from zalo_ai.targets.json_store import (
    ensure_targets_file,
    load_targets,
    set_target_enabled,
)
from zalo_ai.workflows import (
    discover_target_conversations,
    run_summarization,
    save_discovered_targets,
)


VN_TZ = timezone(timedelta(hours=7))


class ZaloSummarizerUI:
    """Small local desktop UI for the Zalo summarization workflows."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Zalo AI Summarizer")
        self.root.geometry("960x760")
        self.root.minsize(820, 640)
        self._configure_dark_theme()

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        self.discovered_conversations: list[dict[str, str]] = []
        self.action_buttons: list[ttk.Button] = []

        ensure_targets_file()
        self._build_ui()
        self._refresh_saved_targets()
        self.root.after(100, self._drain_events)

    def _configure_dark_theme(self) -> None:
        """Apply a consistent dark palette to ttk and classic Tk widgets."""
        colors = {
            "background": "#171923",
            "surface": "#222633",
            "surface_hover": "#303747",
            "field": "#11141d",
            "text": "#e7eaf0",
            "muted": "#a7afbf",
            "accent": "#6c8cff",
            "border": "#3a4152",
            "selection": "#405b9b",
        }

        self.root.configure(background=colors["background"])
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            ".",
            background=colors["background"],
            foreground=colors["text"],
            font=("Segoe UI", 10),
        )
        style.configure("TFrame", background=colors["background"])
        style.configure(
            "TLabel",
            background=colors["background"],
            foreground=colors["text"],
        )
        style.configure(
            "TLabelframe",
            background=colors["background"],
            foreground=colors["text"],
            bordercolor=colors["border"],
        )
        style.configure(
            "TLabelframe.Label",
            background=colors["background"],
            foreground=colors["muted"],
        )
        style.configure(
            "TButton",
            background=colors["surface"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            padding=(12, 7),
        )
        style.map(
            "TButton",
            background=[
                ("disabled", colors["surface"]),
                ("pressed", colors["selection"]),
                ("active", colors["surface_hover"]),
            ],
            foreground=[
                ("disabled", colors["muted"]),
                ("!disabled", colors["text"]),
            ],
        )
        style.configure(
            "TEntry",
            fieldbackground=colors["field"],
            foreground=colors["text"],
            insertcolor=colors["text"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            padding=7,
        )
        style.configure(
            "TNotebook",
            background=colors["background"],
            bordercolor=colors["border"],
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=colors["surface"],
            foreground=colors["muted"],
            padding=(16, 9),
            bordercolor=colors["border"],
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", colors["background"]),
                ("active", colors["surface_hover"]),
            ],
            foreground=[
                ("selected", colors["text"]),
                ("active", colors["text"]),
            ],
        )
        style.configure(
            "Treeview",
            background=colors["field"],
            fieldbackground=colors["field"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            rowheight=28,
        )
        style.map(
            "Treeview",
            background=[("selected", colors["selection"])],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Treeview.Heading",
            background=colors["surface"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            padding=(8, 6),
        )
        style.map(
            "Treeview.Heading",
            background=[("active", colors["surface_hover"])],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=colors["surface"],
            troughcolor=colors["background"],
            bordercolor=colors["background"],
            arrowcolor=colors["muted"],
        )

        self._dark_colors = colors

    def _style_text_widget(self, widget: tk.Text | tk.Listbox) -> None:
        """Apply the dark palette to classic Tk text and list widgets."""
        colors = self._dark_colors
        widget.configure(
            background=colors["field"],
            foreground=colors["text"],
            insertbackground=colors["text"],
            selectbackground=colors["selection"],
            selectforeground="#ffffff",
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
            highlightthickness=1,
            relief="flat",
            borderwidth=0,
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Zalo AI Summarizer",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            container,
            text=(
                "Summarize selected group conversations, refresh targets, "
                "and save your own prompt."
            ),
        ).pack(anchor="w", pady=(2, 10))

        self.status = tk.StringVar(value="Ready")
        ttk.Label(
            container,
            textvariable=self.status,
            relief="groove",
            padding=(8, 5),
        ).pack(fill="x", pady=(0, 10))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self._build_summarize_tab(notebook)
        self._build_targets_tab(notebook)
        self._build_prompt_tab(notebook)

        ttk.Label(container, text="Activity").pack(anchor="w", pady=(10, 3))
        self.activity = ScrolledText(
            container,
            height=9,
            wrap="word",
            font=("Consolas", 9),
        )
        self.activity.pack(fill="both", expand=False)
        self._style_text_widget(self.activity)
        self.activity.configure(state="disabled")

    def _build_summarize_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text="Summarize")

        ttk.Label(
            tab,
            text="Cutoff time (Vietnam time, YYYY-MM-DD HH:MM)",
        ).grid(row=0, column=0, sticky="w")

        self.cutoff = tk.StringVar()
        ttk.Entry(tab, textvariable=self.cutoff, width=28).grid(
            row=1,
            column=0,
            sticky="w",
            pady=(5, 4),
        )
        ttk.Label(
            tab,
            text="Only messages at or after this time will be collected.",
        ).grid(row=2, column=0, sticky="w", pady=(0, 12))

        self.summarize_button = ttk.Button(
            tab,
            text="Start summarization",
            command=self._start_summarization,
        )
        self.summarize_button.grid(row=3, column=0, sticky="w")
        self.action_buttons.append(self.summarize_button)

        ttk.Label(
            tab,
            text=(
                "Zalo opens in a separate browser window. If asked, sign in "
                "there; this window will show progress."
            ),
            wraplength=760,
        ).grid(row=4, column=0, sticky="w", pady=(14, 0))

    def _build_targets_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text="Targets")

        discovery = ttk.LabelFrame(
            tab,
            text="Discover and add conversations",
            padding=10,
        )
        discovery.pack(fill="both", expand=True)

        self.discover_button = ttk.Button(
            discovery,
            text="Refresh conversation list",
            command=self._start_discovery,
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
        self._style_text_widget(self.discovered_list)

        self.add_targets_button = ttk.Button(
            discovery,
            text="Add selected conversations",
            command=self._save_selected_discoveries,
        )
        self.add_targets_button.pack(anchor="w", pady=(8, 0))
        self.action_buttons.append(self.add_targets_button)

        saved = ttk.LabelFrame(
            tab,
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

        self.toggle_targets_button = ttk.Button(
            saved,
            text="Enable / disable selected",
            command=self._toggle_selected_targets,
        )
        self.toggle_targets_button.pack(anchor="w", pady=(8, 0))
        self.action_buttons.append(self.toggle_targets_button)

    def _build_prompt_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, padding=14)
        notebook.add(tab, text="Prompt")

        ttk.Label(
            tab,
            text=(
                "Edit the instructions Gemini should follow. Conversation "
                "IDs and messages are added automatically."
            ),
            wraplength=800,
        ).pack(anchor="w", pady=(0, 8))

        self.prompt_editor = ScrolledText(
            tab,
            height=18,
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.prompt_editor.pack(fill="both", expand=True)
        self._style_text_widget(self.prompt_editor)
        self.prompt_editor.insert("1.0", load_prompt())

        controls = ttk.Frame(tab)
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

    def _log(self, message: str) -> None:
        self.activity.configure(state="normal")
        self.activity.insert("end", message + "\n")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def _start_job(self, kind: str, label: str, job) -> None:
        if self.busy:
            return

        self.busy = True
        self.status.set(label)
        for button in self.action_buttons:
            button.configure(state="disabled")

        def report(message: str) -> None:
            self.events.put(("status", message))

        def worker() -> None:
            try:
                result = job(report)
            except Exception as exc:
                logging.getLogger(__name__).exception(
                    "Background UI action failed."
                )
                self.events.put(("error", (kind, exc)))
            else:
                self.events.put(("result", (kind, result)))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "status":
                message = str(payload)
                self.status.set(message)
                self._log(message)
            elif event == "error":
                kind, exc = payload
                self.busy = False
                for button in self.action_buttons:
                    button.configure(state="normal")
                message = f"{type(exc).__name__}: {exc}"
                self.status.set(f"{kind.title()} failed")
                self._log(message)
            elif event == "result":
                kind, result = payload
                self.busy = False
                for button in self.action_buttons:
                    button.configure(state="normal")
                self._show_result(kind, result)

        self.root.after(100, self._drain_events)

    def _show_result(self, kind: str, result: object) -> None:
        if kind == "summarize":
            summaries = result
            try:
                names = {
                    target["id"]: target["name"]
                    for target in load_targets()
                }
            except Exception:
                names = {}

            for target_id, summary in summaries.items():
                name = names.get(target_id, target_id)
                self._log(f"Summary for {name}:")
                self._log(summary)
                self._log("")
            self.status.set("Summarization complete")
            return

        if kind == "discover":
            self.discovered_conversations = result
            self.discovered_list.delete(0, "end")
            for conversation in self.discovered_conversations:
                self.discovered_list.insert("end", conversation["name"])
            self.status.set(
                f"Found {len(self.discovered_conversations)} conversations"
            )
            self._log(
                f"Discovered {len(self.discovered_conversations)} "
                "conversations."
            )

    def _start_summarization(self) -> None:
        cutoff_text = self.cutoff.get().strip()
        try:
            cutoff = datetime.strptime(
                cutoff_text,
                "%Y-%m-%d %H:%M",
            ).replace(tzinfo=VN_TZ)
        except ValueError:
            self.status.set("Enter the cutoff as YYYY-MM-DD HH:MM.")
            return

        self._start_job(
            "summarize",
            "Starting summarization",
            lambda report: run_summarization(
                cutoff,
                on_status=report,
            ),
        )

    def _start_discovery(self) -> None:
        self._start_job(
            "discover",
            "Opening Zalo to refresh targets",
            lambda report: discover_target_conversations(
                on_status=report,
            ),
        )

    def _save_selected_discoveries(self) -> None:
        selected = self.discovered_list.curselection()
        if not selected:
            self.status.set("Select one or more discovered conversations.")
            return

        conversations = [
            self.discovered_conversations[index]
            for index in selected
        ]

        try:
            added_count = save_discovered_targets(conversations)
            self._refresh_saved_targets()
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Could not save selected targets."
            )
            self.status.set(f"Could not save targets: {exc}")
            return

        self.status.set(f"Saved selection; added {added_count} new targets.")
        self._log(
            f"Saved {len(conversations)} selected conversations; "
            f"added {added_count} new targets."
        )

    def _refresh_saved_targets(self) -> None:
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)

        try:
            targets = load_targets()
        except Exception as exc:
            self.status.set(f"Could not load targets: {exc}")
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

    def _toggle_selected_targets(self) -> None:
        selected = self.target_tree.selection()
        if not selected:
            self.status.set("Select one or more saved targets first.")
            return

        try:
            for target_id in selected:
                enabled = self.target_tree.set(
                    target_id,
                    "enabled",
                ) == "Yes"
                set_target_enabled(target_id, not enabled)
            self._refresh_saved_targets()
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Could not update target settings."
            )
            self.status.set(f"Could not update targets: {exc}")
            return

        self.status.set(f"Updated {len(selected)} target settings.")
        self._log(f"Updated {len(selected)} target settings.")

    def _save_prompt(self) -> None:
        prompt = self.prompt_editor.get("1.0", "end").strip()
        try:
            save_prompt(prompt)
        except Exception as exc:
            self.status.set(f"Could not save prompt: {exc}")
            return

        self.status.set("Prompt saved for future summaries.")
        self._log("Saved the custom summarization prompt.")

    def _restore_default_prompt(self) -> None:
        self.prompt_editor.delete("1.0", "end")
        self.prompt_editor.insert("1.0", DEFAULT_PROMPT)
        self.status.set("Default prompt loaded. Select Save prompt to keep it.")


def main() -> None:
    setup_logging()
    root = tk.Tk()
    ZaloSummarizerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
