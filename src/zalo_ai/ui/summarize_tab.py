from collections.abc import Callable
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from .theme import style_text_widget


VN_TZ = timezone(timedelta(hours=7))


class SummarizeTab(ttk.Frame):
    """Cutoff controls and result display for the summarization workflow."""

    def __init__(
        self,
        parent: ttk.Notebook,
        colors: dict[str, str],
        on_start: Callable[[datetime], None],
        on_status: Callable[[str], None],
    ) -> None:
        super().__init__(parent, padding=14)
        self.colors = colors
        self.on_start = on_start
        self.on_status = on_status
        self.action_buttons: list[ttk.Button] = []
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self,
            text="Cutoff time (Vietnam time)",
        ).grid(row=0, column=0, sticky="w")

        now = datetime.now(VN_TZ).replace(hour=0, minute=0)
        fields = ttk.Frame(self)
        fields.grid(row=1, column=0, sticky="w", pady=(7, 4))

        self.cutoff_day = tk.IntVar(value=now.day)
        self.cutoff_month = tk.IntVar(value=now.month)
        self.cutoff_year = tk.IntVar(value=now.year)
        self.cutoff_hour = tk.IntVar(value=now.hour)
        self.cutoff_minute = tk.IntVar(value=now.minute)

        selectors = (
            ("Day", self.cutoff_day, 1, 31, 5),
            ("Month", self.cutoff_month, 1, 12, 5),
            ("Year", self.cutoff_year, 2000, 2100, 7),
            ("Hour", self.cutoff_hour, 0, 23, 5),
            ("Minute", self.cutoff_minute, 0, 59, 5),
        )
        for column, (label, variable, minimum, maximum, width) in enumerate(
            selectors
        ):
            field = ttk.Frame(fields)
            field.grid(row=0, column=column, sticky="w", padx=(0, 12))
            ttk.Label(field, text=label).pack(anchor="w")
            ttk.Spinbox(
                field,
                from_=minimum,
                to=maximum,
                textvariable=variable,
                width=width,
                wrap=True,
                justify="center",
            ).pack(anchor="w", pady=(3, 0))

        ttk.Label(
            self,
            text="Only messages at or after this time will be collected.",
        ).grid(row=2, column=0, sticky="w", pady=(0, 12))

        self.summarize_button = ttk.Button(
            self,
            text="Start summarization",
            command=self._start,
        )
        self.summarize_button.grid(row=3, column=0, sticky="w")
        self.action_buttons.append(self.summarize_button)

        ttk.Label(
            self,
            text=(
                "Zalo runs in the background. A browser window opens "
                "only if you need to sign in."
            ),
            wraplength=760,
        ).grid(row=4, column=0, sticky="w", pady=(14, 0))

        results_frame = ttk.LabelFrame(
            self,
            text="Summarization results",
            padding=8,
        )
        results_frame.grid(
            row=5,
            column=0,
            sticky="nsew",
            pady=(14, 0),
        )
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        self.results = ScrolledText(
            results_frame,
            height=12,
            wrap="word",
            font=("Segoe UI", 10),
        )
        self.results.pack(fill="both", expand=True)
        style_text_widget(self.results, self.colors)
        self.set_results_text(
            "Summaries will appear here after a run completes."
        )

    def _start(self) -> None:
        try:
            cutoff = datetime(
                year=self.cutoff_year.get(),
                month=self.cutoff_month.get(),
                day=self.cutoff_day.get(),
                hour=self.cutoff_hour.get(),
                minute=self.cutoff_minute.get(),
                tzinfo=VN_TZ,
            )
        except (ValueError, tk.TclError):
            self.on_status("Enter a valid date and time.")
            return

        self.set_results_text(
            "Summarization is running. Results will appear here when "
            "processing finishes."
        )
        self.on_start(cutoff)

    def set_results_text(self, text: str) -> None:
        self.results.configure(state="normal")
        self.results.delete("1.0", "end")
        self.results.insert("1.0", text)
        self.results.configure(state="disabled")

    def show_summaries(
        self,
        summaries: dict[str, str],
        names: dict[str, str],
    ) -> None:
        text = "\n\n".join(
            f"Summary for {names.get(target_id, target_id)}\n{summary}"
            for target_id, summary in summaries.items()
        )
        self.set_results_text(text or "The workflow returned no summaries.")
