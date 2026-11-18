import tkinter as tk
from tkinter import ttk


class Theme(ttk.Frame):
    """Shared dark theme and base frame inherited by every UI tab."""

    COLORS = {
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

    def __init__(
        self,
        parent: tk.Misc,
        colors: dict[str, str] | None = None,
        padding: int = 14,
    ) -> None:
        super().__init__(parent, padding=padding)
        self.colors = (colors or self.COLORS).copy()

    @classmethod
    def configure_dark_theme(cls, root: tk.Tk) -> dict[str, str]:
        """Apply the shared palette to ttk widgets and return its colors."""
        colors = cls.COLORS.copy()
        root.configure(background=colors["background"])
        style = ttk.Style(root)
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
            "TSpinbox",
            fieldbackground=colors["field"],
            foreground=colors["text"],
            insertcolor=colors["text"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            arrowcolor=colors["muted"],
            padding=5,
        )
        style.map(
            "TSpinbox",
            fieldbackground=[("readonly", colors["field"])],
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
        return colors

    def style_text_widget(self, widget: tk.Text | tk.Listbox) -> None:
        """Apply this tab's shared dark colors to classic Tk widgets."""
        style_text_widget(widget, self.colors)


# Retain the prior palette and helper functions for existing imports.
COLORS = Theme.COLORS


def configure_dark_theme(root: tk.Tk) -> dict[str, str]:
    """Backward-compatible function for applying the shared dark theme."""
    return Theme.configure_dark_theme(root)


def style_text_widget(
    widget: tk.Text | tk.Listbox,
    colors: dict[str, str],
) -> None:
    """Apply the dark palette to classic Tk text and list widgets."""
    widget.configure(
        background=colors["field"],
        foreground=colors["text"],
        selectbackground=colors["selection"],
        selectforeground="#ffffff",
        highlightbackground=colors["border"],
        highlightcolor=colors["accent"],
        highlightthickness=1,
        relief="flat",
        borderwidth=0,
    )
    if isinstance(widget, tk.Text):
        widget.configure(insertbackground=colors["text"])
