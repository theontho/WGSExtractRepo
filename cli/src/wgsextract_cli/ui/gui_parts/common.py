"""Shared UI components and base classes for the WGS Extract GUI."""

import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from wgsextract_cli.ui.constants import BUTTON_FONT


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
        self.cmd_buttons: dict[str, ctk.CTkButton] = {}
        self.running_spinners: dict[str, bool] = {}
        self.info_frame: ctk.CTkFrame | None = None
        self.setup_ui()

    def _animate_spinner(self, cmd_key: str, step: int = 0) -> None:
        """Animate a text-based spinner on a button."""
        if cmd_key not in self.running_spinners or not self.winfo_exists():
            return

        chars = ["|", "/", "-", "\\"]
        char = chars[step % len(chars)]
        btn = self.cmd_buttons.get(cmd_key)
        if btn and btn.winfo_exists():
            btn.configure(text=f"Cancel {char}")
            self.after(200, lambda: self._animate_spinner(cmd_key, step + 1))

    def setup_ui(self) -> None:
        """Set up the basic UI elements for the frame."""
        ctk.CTkLabel(
            self, text=self.meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            self,
            text=self.meta["help"],
            font=ctk.CTkFont(size=12, slant="italic"),
            wraplength=800,
        ).pack(pady=(0, 10))

    def set_button_state(self, cmd_key: str, state: str) -> None:
        """Update button text and color based on execution state."""
        if not self.winfo_exists() or cmd_key not in self.cmd_buttons:
            return

        btn = self.cmd_buttons[cmd_key]
        if state == "running":
            self.running_spinners[cmd_key] = True
            btn.configure(
                text="Cancel |",
                fg_color=("#cfd8dc", "#455a64"),
                hover_color=("#b0bec5", "#37474f"),
                text_color=("#000000", "#ffffff"),
            )
            self._animate_spinner(cmd_key)
        else:
            if cmd_key in self.running_spinners:
                del self.running_spinners[cmd_key]
            # Restore original label and color from meta
            # Handle split commands for 'gen' key
            all_cmds = []
            if self.key == "gen":
                all_cmds = self.meta["info_commands"] + self.meta["bam_commands"]
            else:
                all_cmds = self.meta.get("commands", [])

            # Special case for microarray if not in 'commands' list (it's in meta for micro tab)
            try:
                label = next(c["label"] for c in all_cmds if c["cmd"] == cmd_key)
            except StopIteration:
                # Fallback to current button text if not found in meta
                # or if it's a special button
                return

            is_destructive = cmd_key in ["clear-cache", "unsort", "unindex"]
            orig_color = (
                ("#d32f2f", "#b71c1c") if is_destructive else ("#3a7ebf", "#1f538d")
            )
            orig_hover = "#9a0007" if is_destructive else ("#325882", "#14375e")
            orig_text = "#ffffff"

            btn.configure(
                text=label,
                fg_color=orig_color,
                hover_color=orig_hover,
                text_color=orig_text,
            )

    def handle_button_click(self, cmd_key: str) -> None:
        """Handle button click, either running a new command or cancelling an active one."""
        if cmd_key in self.main_app.controller.active_processes:
            self.main_app.controller.cancel_cmd(cmd_key)
        elif cmd_key == "ref-gene-map" and self.main_app.gene_map_cancel_event:
            self.main_app.controller.cancel_gene_map_download()
        else:
            self.main_app.run_dispatch(cmd_key, self)

    def update_info_display(self, data: Any) -> None:
        """Update the info frame with fast info output (dict or error string)."""
        import os

        if not self.winfo_exists():
            return

        input_path = self.bam_entry.get() if hasattr(self, "bam_entry") else ""

        # Toggle clear-cache button visibility
        if "clear-cache" in self.cmd_buttons:
            out_dir = self.main_app.out_dir_var.get()
            effective_outdir = (
                out_dir if out_dir else os.path.dirname(os.path.abspath(input_path))
            )
            json_cache = ""
            if input_path:
                json_cache = os.path.join(
                    effective_outdir,
                    f"{os.path.basename(input_path)}.wgse_info.json",
                )

            if json_cache and os.path.exists(json_cache):
                self.cmd_buttons["clear-cache"].grid()
            else:
                self.cmd_buttons["clear-cache"].grid_remove()

        if not self.info_frame:
            return
        fstats = data.get("file_stats", {}) if isinstance(data, dict) else {}
        is_sorted = fstats.get("sorted", False)
        is_indexed = fstats.get("indexed", False)
        is_cram = input_path.lower().endswith(".cram")
        is_bam = input_path.lower().endswith(".bam")

        def toggle_btn(cmd: str, show: bool) -> None:
            if cmd in self.cmd_buttons:
                if show:
                    self.cmd_buttons[cmd].grid()
                else:
                    self.cmd_buttons[cmd].grid_remove()

        if self.key == "gen" and input_path:
            toggle_btn("sort", not is_sorted)
            toggle_btn("unsort", is_sorted)
            toggle_btn("index", not is_indexed)
            toggle_btn("unindex", is_indexed)
            toggle_btn("to-bam", is_cram)
            toggle_btn("to-cram", is_bam)
        elif self.key == "gen":
            for c in ["sort", "unsort", "index", "unindex", "to-bam", "to-cram"]:
                toggle_btn(c, False)

        # Clear existing widgets
        for widget in self.info_frame.winfo_children():
            widget.destroy()

        if not data:
            return

        if isinstance(data, str):
            ctk.CTkLabel(
                self.info_frame, text=data, font=ctk.CTkFont(size=12, slant="italic")
            ).pack(side="left")
            return

        # Render dictionary data nicely
        fstats = data.get("file_stats", {})
        stats_str = f"{'Sorted' if fstats.get('sorted') else 'Unsorted'}, {'Indexed' if fstats.get('indexed') else 'Unindexed'}, {fstats.get('size_gb', 0):.1f} GBs"

        items = [
            ("Reference Genome:", data.get("ref_model_str", "Unknown")),
            ("File Stats:", stats_str),
            (
                "Avg Read Length:",
                f"{data.get('avg_read_len', 0):.0f} bp (SD={data.get('std_read_len', 0):.0f} bp), {'Paired-end' if data.get('is_paired') else 'Single-end'}",
            ),
            (
                "Avg Insert Size:",
                f"{data.get('avg_insert_size', 0):.0f} bp (SD={data.get('std_insert_size', 0):.0f} bp)",
            ),
        ]

        if data.get("sequencer"):
            if data["sequencer"] != "Unknown":
                items.append(("Sequencer:", data["sequencer"]))
            elif data.get("first_qname"):
                items.append(("Sequencer:", f"Unknown: {data['first_qname']}"))

        for i, (label, val) in enumerate(items):
            ctk.CTkLabel(
                self.info_frame,
                text=label,
                font=ctk.CTkFont(size=13, weight="bold"),
                width=140,
                anchor="w",
            ).grid(row=i, column=0, sticky="w", padx=(0, 10))
            ctk.CTkLabel(
                self.info_frame, text=val, font=ctk.CTkFont(size=13), anchor="w"
            ).grid(row=i, column=1, sticky="w")

    def create_file_selector(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        iv: str = "",
        variable: ctk.StringVar | None = None,
        on_change: Callable[[str], None] | None = None,
        button_text: str | None = None,
        command: Callable[[], None] | None = None,
        info_text: str | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a file selection row with a label, entry, and browse button.
        Optional action button can be added to the right of Browse.

        Args:
            p: The parent frame.
            label_text: The label text.
            iv: Initial value for the entry (ignored if variable is provided).
            variable: Optional StringVar to bind to the entry.
            on_change: Optional callback when value changes.
            button_text: Optional text for an action button.
            command: Optional command for the action button.
            info_text: Optional tooltip text for an info icon.

        Returns:
            The created CTkEntry widget.
        """
        frame = ctk.CTkFrame(p)

        label_f = ctk.CTkFrame(frame, fg_color="transparent")
        label_f.pack(side="left", padx=10)

        ctk.CTkLabel(label_f, text=label_text, width=120, anchor="w").pack(side="left")

        if info_text:
            i_lbl = ctk.CTkLabel(
                label_f,
                text=" ⓘ",
                font=ctk.CTkFont(size=14),
                text_color="#55aaff",
                cursor="hand2",
            )
            i_lbl.pack(side="left")
            ToolTip(i_lbl, info_text)

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

        # Right-side buttons container
        btn_f = ctk.CTkFrame(frame, fg_color="transparent")
        btn_f.pack(side="right", padx=10)

        ctk.CTkButton(
            btn_f,
            text="Browse",
            width=80,
            command=lambda: self.browse_file(entry, variable, on_change),
            font=BUTTON_FONT,
        ).pack(side="left", padx=5)

        if button_text:
            btn = ctk.CTkButton(
                btn_f, text=button_text, width=120, command=command, font=BUTTON_FONT
            )
            btn.pack(side="left", padx=5)
            entry.action_button = btn

        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_dir_selector(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        iv: str = "",
        variable: ctk.StringVar | None = None,
        info_text: str | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a directory selection row with a label, entry, and browse button.

        Args:
            p: The parent frame.
            label_text: The label text.
            iv: Initial value for the entry (ignored if variable is provided).
            variable: Optional StringVar to bind to the entry.
            info_text: Optional tooltip text for an info icon.

        Returns:
            The created CTkEntry widget.
        """
        frame = ctk.CTkFrame(p)

        label_f = ctk.CTkFrame(frame, fg_color="transparent")
        label_f.pack(side="left", padx=10)

        ctk.CTkLabel(label_f, text=label_text, width=120, anchor="w").pack(side="left")

        if info_text:
            i_lbl = ctk.CTkLabel(
                label_f,
                text=" ⓘ",
                font=ctk.CTkFont(size=14),
                text_color="#55aaff",
                cursor="hand2",
            )
            i_lbl.pack(side="left")
            ToolTip(i_lbl, info_text)

        entry = ctk.CTkEntry(frame, textvariable=variable)
        if not variable:
            entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame,
            text="Browse",
            width=80,
            command=lambda: self.browse_dir(entry, variable),
            font=BUTTON_FONT,
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_entry(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        button_text: str | None = None,
        command: Callable[[], None] | None = None,
        info_text: str | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a simple entry row with a label and entry, and an optional action button.

        Args:
            p: The parent frame.
            label_text: The label text.
            button_text: Optional text for an action button.
            command: Optional command for the action button.
            info_text: Optional tooltip text for an info icon.

        Returns:
            The created CTkEntry widget.
        """
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)

        label_f = ctk.CTkFrame(f, fg_color="transparent")
        label_f.pack(side="left", padx=10)

        ctk.CTkLabel(label_f, text=label_text, width=120, anchor="w").pack(side="left")

        if info_text:
            i_lbl = ctk.CTkLabel(
                label_f,
                text=" ⓘ",
                font=ctk.CTkFont(size=14),
                text_color="#55aaff",
                cursor="hand2",
            )
            i_lbl.pack(side="left")
            ToolTip(i_lbl, info_text)

        e = ctk.CTkEntry(f)
        if button_text:
            e.pack(side="left", fill="x", expand=True, padx=10)
            btn = ctk.CTkButton(
                f, text=button_text, width=120, command=command, font=BUTTON_FONT
            )
            btn.pack(side="right", padx=10)
            # Store button on entry so it can be accessed if needed (e.g. for tooltips)
            e.action_button = btn
        else:
            e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def create_entry_with_info(
        self, p: ctk.CTkFrame, label_text: str, info_text: str
    ) -> ctk.CTkEntry:
        """
        Create a simple entry row with a label, an info icon with tooltip, and entry.

        Args:
            p: The parent frame.
            label_text: The label text.
            info_text: The tooltip text for the info icon.

        Returns:
            The created CTkEntry widget.
        """
        return self.create_entry(p, label_text, info_text=info_text)

    def create_read_only_entry(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        variable: ctk.StringVar,
        button_text: str | None = None,
        command: Callable[[], None] | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a read-only entry row with a label and entry, and an optional action button.

        Args:
            p: The parent frame.
            label_text: The label text.
            variable: The StringVar to bind to the entry.
            button_text: Optional text for an action button.
            command: Optional command for the action button.

        Returns:
            The created CTkEntry widget.
        """
        return self.create_read_only_entry_with_info(
            p, label_text, variable, "", button_text, command
        )

    def create_read_only_entry_with_info(
        self,
        p: ctk.CTkFrame,
        label_text: str,
        variable: ctk.StringVar,
        info_text: str,
        button_text: str | None = None,
        command: Callable[[], None] | None = None,
    ) -> ctk.CTkEntry:
        """
        Create a read-only entry row with a label, info icon with tooltip, and entry.

        Args:
            p: The parent frame.
            label_text: The label text.
            variable: The StringVar to bind to the entry.
            info_text: The tooltip text for the info icon.
            button_text: Optional text for an action button.
            command: Optional command for the action button.

        Returns:
            The created CTkEntry widget.
        """
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)

        label_f = ctk.CTkFrame(f, fg_color="transparent")
        label_f.pack(side="left", padx=10)

        ctk.CTkLabel(label_f, text=label_text, width=120, anchor="w").pack(side="left")

        if info_text:
            i_lbl = ctk.CTkLabel(
                label_f,
                text=" ⓘ",
                font=ctk.CTkFont(size=14),
                text_color="#55aaff",
                cursor="hand2",
            )
            i_lbl.pack(side="left")
            ToolTip(i_lbl, info_text)

        e = ctk.CTkEntry(f, textvariable=variable, state="readonly")
        if button_text:
            e.pack(side="left", fill="x", expand=True, padx=10)
            btn = ctk.CTkButton(
                f, text=button_text, width=120, command=command, font=BUTTON_FONT
            )
            btn.pack(side="right", padx=10)
            e.action_button = btn
        else:
            e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def create_checkbox_with_info(
        self,
        p: ctk.CTkFrame,
        text: str,
        variable: ctk.Variable,
        info_text: str,
    ) -> ctk.CTkCheckBox:
        """
        Create a checkbox with an info icon and tooltip.

        Args:
            p: The parent frame.
            text: The checkbox label text.
            variable: The variable to bind to the checkbox.
            info_text: The tooltip text for the info icon.

        Returns:
            The created CTkCheckBox widget.
        """
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=2)

        cb = ctk.CTkCheckBox(
            f,
            text=text,
            variable=variable,
            font=ctk.CTkFont(size=12),
        )
        cb.pack(side="left", padx=10)

        i_lbl = ctk.CTkLabel(
            f,
            text=" ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#55aaff",
            cursor="hand2",
        )
        i_lbl.pack(side="left")
        ToolTip(i_lbl, info_text)

        return cb

    def create_section_title(
        self, p: ctk.CTkFrame, text: str, info_text: str | None = None
    ) -> None:
        """Create a section title with an optional info icon and tooltip."""
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(pady=(15, 5))

        lbl = ctk.CTkLabel(f, text=text, font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(side="left")

        if info_text:
            i_lbl = ctk.CTkLabel(
                f,
                text=" ⓘ",
                font=ctk.CTkFont(size=14),
                text_color="#55aaff",
                cursor="hand2",
            )
            i_lbl.pack(side="left")
            ToolTip(i_lbl, info_text)

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
