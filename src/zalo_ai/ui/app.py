import logging
import queue
import threading
from collections.abc import Callable
from datetime import datetime
from threading import Event
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from zalo_ai.cancellation import CancellationRequested
from zalo_ai.config.logging_config import setup_logging
from zalo_ai.targets.json_store import ensure_targets_file, load_targets
from zalo_ai.workflows import (
    discover_target_conversations,
    run_summarization,
)
from .prompt_tab import PromptTab
from .summarize_tab import SummarizeTab
from .targets_tab import TargetsTab
from .theme import Theme, style_text_widget


Job = Callable[[Callable[[str], None], Event], object]


class ZaloSummarizerUI:
    """Desktop shell coordinating the summarizer tabs and backend jobs."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Zalo AI Summarizer")
        self.root.geometry("960x760")
        self.root.minsize(820, 640)
        self.colors = Theme.configure_dark_theme(root)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        self.cancel_event: Event | None = None
        self.action_buttons: list[ttk.Button] = []

        ensure_targets_file()
        self._build_ui()
        self.root.after(100, self._drain_events)

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

        status_row = ttk.Frame(container)
        status_row.pack(fill="x", pady=(0, 10))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(
            status_row,
            textvariable=self.status,
            relief="groove",
            padding=(8, 5),
        ).pack(side="left", fill="x", expand=True)

        self.cancel_button = ttk.Button(
            status_row,
            text="Cancel",
            command=self._cancel_active_job,
            state="disabled",
        )
        self.cancel_button.pack(side="left", padx=(8, 0))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self.summarize_tab = SummarizeTab(
            notebook,
            self.colors,
            on_start=self._start_summarization,
            on_status=self._set_status,
        )
        notebook.add(self.summarize_tab, text="Summarize")

        self.targets_tab = TargetsTab(
            notebook,
            self.colors,
            on_refresh=self._start_discovery,
            on_status=self._set_status,
            log=self._log,
        )
        notebook.add(self.targets_tab, text="Targets")

        self.prompt_tab = PromptTab(
            notebook,
            self.colors,
            on_status=self._set_status,
            log=self._log,
        )
        notebook.add(self.prompt_tab, text="Prompt")

        self.action_buttons = (
            self.summarize_tab.action_buttons
            + self.targets_tab.action_buttons
            + self.prompt_tab.action_buttons
        )

        ttk.Label(container, text="Activity").pack(anchor="w", pady=(10, 3))
        self.activity = ScrolledText(
            container,
            height=5,
            wrap="word",
            font=("Consolas", 9),
        )
        self.activity.pack(fill="x", expand=False)
        style_text_widget(self.activity, self.colors)
        self.activity.configure(state="disabled")

    def _set_status(self, message: str) -> None:
        self.status.set(message)

    def _log(self, message: str) -> None:
        self.activity.configure(state="normal")
        self.activity.insert("end", message + "\n")
        self.activity.see("end")
        self.activity.configure(state="disabled")

    def _cancel_active_job(self) -> None:
        if not self.busy or self.cancel_event is None:
            return

        if not self.cancel_event.is_set():
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled")
            self.status.set(
                "Cancellation requested; waiting for the current step."
            )
            self._log("Cancellation requested.")

    def _start_job(self, kind: str, label: str, job: Job) -> None:
        if self.busy:
            return

        self.busy = True
        cancel_event = threading.Event()
        self.cancel_event = cancel_event
        self.status.set(label)
        self.cancel_button.configure(state="normal")
        for button in self.action_buttons:
            button.configure(state="disabled")

        def report(message: str) -> None:
            if not cancel_event.is_set():
                self.events.put(("status", message))

        def worker() -> None:
            try:
                result = job(report, cancel_event)
            except CancellationRequested as exc:
                self.events.put(("cancelled", (kind, exc)))
            except Exception as exc:
                logging.getLogger(__name__).exception(
                    "Background UI action failed."
                )
                self.events.put(("error", (kind, exc)))
            else:
                self.events.put(("result", (kind, result)))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_job_controls(self) -> None:
        self.busy = False
        self.cancel_event = None
        self.cancel_button.configure(state="disabled")
        for button in self.action_buttons:
            button.configure(state="normal")

    def _drain_events(self) -> None:
        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "status":
                if self.cancel_event is None or not self.cancel_event.is_set():
                    message = str(payload)
                    self.status.set(message)
                    self._log(message)
            elif event == "error":
                kind, exc = payload
                self._finish_job_controls()
                message = f"{type(exc).__name__}: {exc}"
                self.status.set(f"{kind.title()} failed")
                self._log(message)
                if kind == "summarize":
                    self.summarize_tab.set_results_text(
                        "Summarization failed.\n\n" + message
                    )
            elif event == "cancelled":
                kind, _exc = payload
                self._finish_job_controls()
                label = (
                    "Summarization cancelled"
                    if kind == "summarize"
                    else "Target refresh cancelled"
                )
                self.status.set(label)
                self._log(label + ".")
                if kind == "summarize":
                    self.summarize_tab.set_results_text(
                        "Summarization was cancelled before it finished."
                    )
            elif event == "result":
                kind, result = payload
                self._finish_job_controls()
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

            self.summarize_tab.show_summaries(summaries, names)
            self.status.set("Summarization complete")
            self._log(
                f"Displayed summaries for {len(summaries)} conversation(s)."
            )
            return

        if kind == "discover":
            self.targets_tab.set_discoveries(result)

    def _start_summarization(self, cutoff: datetime) -> None:
        self._start_job(
            "summarize",
            "Starting summarization",
            lambda report, cancel_event: run_summarization(
                cutoff,
                on_status=report,
                cancel_event=cancel_event,
            ),
        )

    def _start_discovery(self) -> None:
        self._start_job(
            "discover",
            "Opening Zalo to refresh targets",
            lambda report, cancel_event: discover_target_conversations(
                on_status=report,
                cancel_event=cancel_event,
            ),
        )


def main() -> None:
    setup_logging()
    root = tk.Tk()
    ZaloSummarizerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
