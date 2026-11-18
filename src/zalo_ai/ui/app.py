from datetime import datetime
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from zalo_ai.config.logging_config import setup_logging
from zalo_ai.targets.json_store import ensure_targets_file, load_targets
from zalo_ai.workflows import discover_target_conversations, run_summarization
from .job_runner import Job, JobRunner
from .prompt_tab import PromptTab
from .summarize_tab import SummarizeTab
from .targets_tab import TargetsTab
from .theme import Theme, style_text_widget


class ZaloSummarizerUI:
    """Desktop shell coordinating the summarizer tabs and backend jobs."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Zalo AI Summarizer")
        self.root.geometry("960x760")
        self.root.minsize(820, 640)
        self.colors = Theme.configure_dark_theme(root)
        self.action_buttons: list[ttk.Button] = []
        self.busy = False
        self.cancel_button: ttk.Button
        self.status: tk.StringVar
        self.activity: ScrolledText
        ensure_targets_file()
        self._build_ui()
        self.job_runner = JobRunner(
            self._set_status, self._log, self._show_result, self._job_error,
            self._job_cancelled, self._set_busy,
            lambda callback: self.root.after(100, callback),
        )
        self.root.after(100, self.job_runner.drain)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=14)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="Zalo AI Summarizer", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(container, text=("Summarize selected group conversations, refresh targets, "
            "and save your own prompt.")).pack(anchor="w", pady=(2, 10))
        status_row = ttk.Frame(container)
        status_row.pack(fill="x", pady=(0, 10))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(status_row, textvariable=self.status, relief="groove", padding=(8, 5)).pack(side="left", fill="x", expand=True)
        self.cancel_button = ttk.Button(status_row, text="Cancel", command=self._cancel_active_job, state="disabled")
        self.cancel_button.pack(side="left", padx=(8, 0))
        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)
        self.summarize_tab = SummarizeTab(notebook, self.colors, on_start=self._start_summarization, on_status=self._set_status)
        notebook.add(self.summarize_tab, text="Summarize")
        self.targets_tab = TargetsTab(notebook, self.colors, on_refresh=self._start_discovery, on_status=self._set_status, log=self._log)
        notebook.add(self.targets_tab, text="Targets")
        self.prompt_tab = PromptTab(notebook, self.colors, on_status=self._set_status, log=self._log)
        notebook.add(self.prompt_tab, text="Prompt")
        self.action_buttons = (self.summarize_tab.action_buttons + self.targets_tab.action_buttons + self.prompt_tab.action_buttons)
        ttk.Label(container, text="Activity").pack(anchor="w", pady=(10, 3))
        self.activity = ScrolledText(container, height=5, wrap="word", font=("Consolas", 9))
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

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        cancelled = self.job_runner.cancel_event is not None and self.job_runner.cancel_event.is_set()
        self.cancel_button.configure(state="normal" if busy and not cancelled else "disabled")
        for button in self.action_buttons:
            button.configure(state="disabled" if busy else "normal")

    def _cancel_active_job(self) -> None:
        self.job_runner.cancel()

    def _job_error(self, kind: str, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        self._set_status(f"{kind.title()} failed")
        self._log(message)
        if kind == "summarize":
            self.summarize_tab.set_results_text("Summarization failed.\n\n" + message)

    def _job_cancelled(self, kind: str, _error: Exception) -> None:
        label = "Summarization cancelled" if kind == "summarize" else "Target refresh cancelled"
        self._set_status(label)
        self._log(label + ".")
        if kind == "summarize":
            self.summarize_tab.set_results_text("Summarization was cancelled before it finished.")

    def _show_result(self, kind: str, result: object) -> None:
        if kind == "summarize":
            try:
                names = {target["id"]: target["name"] for target in load_targets()}
            except Exception:
                names = {}
            self.summarize_tab.show_summaries(result, names)
            self._set_status("Summarization complete")
            self._log(f"Displayed summaries for {len(result)} conversation(s).")
        elif kind == "discover":
            self.targets_tab.set_discoveries(result)

    def _start_job(self, kind: str, label: str, job: Job) -> None:
        self.job_runner.start(kind, label, job)

    def _start_summarization(self, cutoff: datetime) -> None:
        self._start_job("summarize", "Starting summarization", lambda report, event: run_summarization(cutoff, on_status=report, cancel_event=event))

    def _start_discovery(self) -> None:
        self._start_job("discover", "Opening Zalo to refresh targets", lambda report, event: discover_target_conversations(on_status=report, cancel_event=event))


def main() -> None:
    setup_logging()
    root = tk.Tk()
    ZaloSummarizerUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
