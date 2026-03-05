"""Main entry point for the WGS Extract Graphical User Interface."""

import os
import tkinter as tk
import threading
from typing import Any, Dict, Optional

import customtkinter as ctk

from wgsextract_cli.ui.constants import UI_METADATA
from wgsextract_cli.ui.gui_parts.controller import GUIController
from wgsextract_cli.ui.gui_parts.gen import GenericFrame
from wgsextract_cli.ui.gui_parts.lib import LibFrame
from wgsextract_cli.ui.gui_parts.micro import MicroFrame


class WGSExtractGUI(ctk.CTk):
    """
    The main application window for the WGS Extract GUI.
    Manages navigation, layout, and coordinates between UI components and the controller.
    """

    def __init__(self) -> None:
        """Initialize the GUI application, setting up the layout and components."""
        super().__init__()
        self.title("WGS Extract GUI")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # State management
        self.active_downloads: Dict[str, Any] = {}
        self.vep_cancel_event: Optional[threading.Event] = None
        self.controller = GUIController(self)
        
        # UI Layout
        self._setup_sidebar()
        self._setup_main_content()
        self._setup_output_area()
        self._setup_frames()
        
        # Default view
        self.show_frame("gen")
        
        # Event bindings
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _setup_sidebar(self) -> None:
        """Set up the navigation sidebar."""
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            self.sidebar_frame,
            text="WGS Extract",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        for i, (key, meta) in enumerate(UI_METADATA.items()):
            ctk.CTkButton(
                self.sidebar_frame,
                text=meta["title"],
                command=lambda k=key: self.show_frame(k),
            ).grid(row=i + 1, column=0, padx=20, pady=10)

    def _setup_main_content(self) -> None:
        """Set up the main content area where tab frames are displayed."""
        self.main_content = ctk.CTkFrame(self)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

    def _setup_output_area(self) -> None:
        """Set up the scrollable text output area at the bottom."""
        self.output_text = ctk.CTkTextbox(self, height=200)
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=20, pady=(0, 20))

    def _setup_frames(self) -> None:
        """Initialize all tab frames from UI_METADATA."""
        self.frames: Dict[str, ctk.CTkFrame] = {}
        for key, meta in UI_METADATA.items():
            if key == "lib":
                frame = LibFrame(self.main_content, self, key, meta)
            elif key == "micro":
                frame = MicroFrame(self.main_content, self, key, meta)
            else:
                frame = GenericFrame(self.main_content, self, key, meta)
            self.frames[key] = frame

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel events for scrolling across different widgets."""
        w = event.widget
        delta = event.num == 4 and 1 or event.num == 5 and -1 or event.delta
        curr = w
        while curr:
            if isinstance(curr, (tk.Canvas, tk.Text, ctk.CTkTextbox)):
                if isinstance(curr, tk.Canvas):
                    curr.yview_scroll(
                        int(-1 * (delta / 120)) if event.num not in [4, 5] else -1 * delta,
                        "units",
                    )
                else:
                    curr.yview(
                        tk.SCROLL,
                        int(-1 * (delta / 120)) if event.num not in [4, 5] else -1 * delta,
                        tk.UNITS,
                    )
                break
            try:
                curr = curr.master
            except AttributeError:
                break

    def show_frame(self, name: str) -> None:
        """
        Switch the visible frame in the main content area.

        Args:
            name: The key of the frame to show.
        """
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def log(self, message: str) -> None:
        """
        Append a message to the output text area.

        Args:
            message: The string to log.
        """
        self.output_text.insert("end", message + "\n")
        self.output_text.see("end")

    # Delegate logic methods to controller
    def run_dispatch(self, cmd: str, frame: Any) -> None:
        """Delegate command dispatch to the controller."""
        self.controller.run_dispatch(cmd, frame)

    def run_lib_download(self, gd: dict[str, Any], lib_frame: Any, restart: bool = False) -> None:
        """Delegate library download to the controller."""
        self.controller.run_lib_download(gd, lib_frame, restart)

    def run_lib_delete(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate library deletion to the controller."""
        self.controller.run_lib_delete(group, lib_frame)

    def cancel_lib_download(self, fn: str) -> None:
        """Delegate library download cancellation to the controller."""
        self.controller.cancel_lib_download(fn)

    def cancel_vep_download(self) -> None:
        """Delegate VEP download cancellation to the controller."""
        self.controller.cancel_vep_download()


def main() -> None:
    """Application entry point."""
    app = WGSExtractGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
