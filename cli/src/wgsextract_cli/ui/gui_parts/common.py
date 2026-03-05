import os
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y = (
            self.widget.winfo_rootx() + 20,
            self.widget.winfo_rooty() + self.widget.winfo_height() + 5,
        )
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2b2b2b",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            font=("Arial", "10", "normal"),
            padx=10,
            pady=8,
            wraplength=400,
        ).pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class BaseFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, main_app, key, meta):
        super().__init__(master)
        self.main_app = main_app
        self.key = key
        self.meta = meta
        self.setup_ui()

    def setup_ui(self):
        ctk.CTkLabel(
            self, text=self.meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            self, text=self.meta["help"], font=ctk.CTkFont(size=12, slant="italic")
        ).pack(pady=(0, 10))

    def create_file_selector(self, p, l, iv=""):
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=l, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame)
        entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame, text="Browse", width=80, command=lambda: self.browse_file(entry)
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_dir_selector(self, p, l, iv=""):
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=l, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame)
        entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame, text="Browse", width=80, command=lambda: self.browse_dir(entry)
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_entry(self, p, l):
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f, text=l, width=120, anchor="w").pack(side="left", padx=10)
        e = ctk.CTkEntry(f)
        e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def browse_file(self, e):
        f = filedialog.askopenfilename()
        if f:
            e.delete(0, "end")
            e.insert(0, f)

    def browse_dir(self, e):
        d = filedialog.askdirectory()
        if d:
            e.delete(0, "end")
            e.insert(0, d)
