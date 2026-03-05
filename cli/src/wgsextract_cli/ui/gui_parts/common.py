"""Shared UI components and base classes for the WGS Extract GUI."""

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog
from typing import Any

import customtkinter as ctk


class ToolTip:
    """A tooltip widget that displays text when hovering over another widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        """
        Initialize the ToolTip.

        Args:
            widget: The widget to attach the tooltip to.
            text: The text to display in the tooltip.
        """
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event: tk.Event | None = None) -> None:
        """Display the tooltip window."""
        if self.tip_window or not self.text:
            return
        x, y = (
            self.widget.winfo_rootx() + 20,
            self.widget.winfo_rooty() + self.widget.winfo_height() + 5,
        )
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2b2b2b",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            font=("Arial", 10, "normal"),
            padx=10,
            pady=8,
            wraplength=400,
        ).pack()

    def hide_tip(self, event: tk.Event | None = None) -> None:
        """Hide the tooltip window."""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class BaseFrame(ctk.CTkScrollableFrame):
    """Base class for all GUI tab frames, providing common UI utilities."""

    def __init__(
        self, master: Any, main_app: Any, key: str, meta: dict[str, Any]
    ) -> None:
        """
        Initialize the base frame.

        Args:
            master: The parent widget.
            main_app: The main application instance (WGSExtractGUI).
            key: The unique key for this frame.
            meta: Metadata for this frame from UI_METADATA.
        """
        super().__init__(master)
        self.main_app = main_app
        self.key = key
        self.meta = meta
        self.setup_ui()

    def setup_ui(self) -> None:
        """Set up the basic UI elements for the frame."""
        ctk.CTkLabel(
            self, text=self.meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            self, text=self.meta["help"], font=ctk.CTkFont(size=12, slant="italic")
        ).pack(pady=(0, 10))

    def create_file_selector(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        iv: str = "",
        variable: ctk.StringVar | None = None,
        on_change: Callable[[str], None] | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a file selection row with a label, entry, and browse button.

        Args:
            p: The parent frame.
            label_text: The label text.
            iv: Initial value for the entry (ignored if variable is provided).
            variable: Optional StringVar to bind to the entry.
            on_change: Optional callback when value changes.

        Returns:
            The created CTkEntry widget.
        """
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=label_text, width=120, anchor="w").pack(
            side="left", padx=10
        )
        entry = ctk.CTkEntry(frame, textvariable=variable)
        if not variable:
            entry.insert(0, iv)

        if on_change:
            if variable:
                variable.trace_add("write", lambda *args: on_change(variable.get()))
            else:
                entry.bind("<FocusOut>", lambda e: on_change(entry.get()))
                entry.bind("<Return>", lambda e: on_change(entry.get()))

        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame,
            text="Browse",
            width=80,
            command=lambda: self.browse_file(entry, variable, on_change),
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_dir_selector(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        iv: str = "",
        variable: ctk.StringVar | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a directory selection row with a label, entry, and browse button.

        Args:
            p: The parent frame.
            label_text: The label text.
            iv: Initial value for the entry (ignored if variable is provided).
            variable: Optional StringVar to bind to the entry.

        Returns:
            The created CTkEntry widget.
        """
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=label_text, width=120, anchor="w").pack(
            side="left", padx=10
        )
        entry = ctk.CTkEntry(frame, textvariable=variable)
        if not variable:
            entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame,
            text="Browse",
            width=80,
            command=lambda: self.browse_dir(entry, variable),
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_entry(self, p: ctk.CTkFrame, label_text: str) -> ctk.CTkEntry:
        """
        Create a simple entry row with a label and entry.

        Args:
            p: The parent frame.
            label_text: The label text.

        Returns:
            The created CTkEntry widget.
        """
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f, text=label_text, width=120, anchor="w").pack(
            side="left", padx=10
        )
        e = ctk.CTkEntry(f)
        e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def create_read_only_entry(
        self, p: ctk.CTkFrame, label_text: str, variable: ctk.StringVar
    ) -> ctk.CTkEntry:
        """
        Create a read-only entry row with a label and entry.

        Args:
            p: The parent frame.
            label_text: The label text.
            variable: The StringVar to bind to the entry.

        Returns:
            The created CTkEntry widget.
        """
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f, text=label_text, width=120, anchor="w").pack(
            side="left", padx=10
        )
        e = ctk.CTkEntry(f, textvariable=variable, state="readonly")
        e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def browse_file(
        self,
        e: ctk.CTkEntry,
        variable: ctk.StringVar | None = None,
        on_change: Callable[[str], None] | None = None,
    ) -> None:
        """Open a file dialog and update the entry."""
        f = filedialog.askopenfilename()
        if f:
            if variable:
                variable.set(f)
            else:
                e.delete(0, "end")
                e.insert(0, f)
                if on_change:
                    on_change(f)

    def browse_dir(
        self, e: ctk.CTkEntry, variable: ctk.StringVar | None = None
    ) -> None:
        """Open a directory dialog and update the entry."""
        d = filedialog.askdirectory()
        if d:
            if variable:
                variable.set(d)
            else:
                e.delete(0, "end")
                e.insert(0, d)
