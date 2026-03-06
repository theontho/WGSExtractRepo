"""Main entry point for the WGS Extract Graphical User Interface."""

import os
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

import customtkinter as ctk
from PIL import Image

from wgsextract_cli.ui.constants import BUTTON_FONT, UI_METADATA
from wgsextract_cli.ui.gui_parts.controller import GUIController
from wgsextract_cli.ui.gui_parts.flow import FlowFrame
from wgsextract_cli.ui.gui_parts.gen import GenericFrame
from wgsextract_cli.ui.gui_parts.lib import LibFrame
from wgsextract_cli.ui.gui_parts.micro import MicroFrame


class InfoWindow(ctk.CTkToplevel):
    """A separate window to display detailed BAM/CRAM information."""

    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.geometry("900x700")

        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                img = tk.PhotoImage(file=icon_path)
                self.iconphoto(False, img)
            except Exception:
                pass

        # Use a textbox for scrollable, monospace text
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Courier", size=13))
        self.textbox.pack(fill="both", expand=True, padx=20, pady=20)
        self.textbox.insert("0.0", text)
        self.textbox.configure(state="disabled")  # Read-only


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

        # Load assets
        self.icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
        self.logo_image: ctk.CTkImage | None = None
        if os.path.exists(self.icon_path):
            try:
                # Set window icon
                img = tk.PhotoImage(file=self.icon_path)
                self.iconphoto(True, img)

                # Load for sidebar
                pil_img = Image.open(self.icon_path)
                self.logo_image = ctk.CTkImage(
                    light_image=pil_img, dark_image=pil_img, size=(100, 100)
                )
            except Exception:
                pass

        # State management
        self.active_downloads: dict[str, Any] = {}
        self.vep_cancel_event: threading.Event | None = None
        self.gene_map_cancel_event: threading.Event | None = None
        self.controller = GUIController(self)

        # Shared variables for synchronization across tabs
        self.bam_path_var = ctk.StringVar(value=os.environ.get("WGSE_INPUT", ""))
        self.vcf_path_var = ctk.StringVar()
        self.fastq_path_var = ctk.StringVar()
        self.ref_path_var = ctk.StringVar(value=os.environ.get("WGSE_REF", ""))
        self.out_dir_var = ctk.StringVar(value=os.environ.get("WGSE_OUTDIR", ""))
        self.vep_cache_var = ctk.StringVar()
        self.vcf_exclude_gaps_var = ctk.BooleanVar(value=False)

        # Handle initial VCF value if WGSE_INPUT looks like VCF
        init_input = os.environ.get("WGSE_INPUT", "")
        if init_input.lower().endswith((".vcf", ".vcf.gz", ".bcf")):
            self.vcf_path_var.set(init_input)
            self.bam_path_var.set("")
        elif init_input.lower().endswith((".fastq", ".fq", ".fastq.gz", ".fq.gz")):
            self.fastq_path_var.set(init_input)
            self.bam_path_var.set("")

        def ensure_dir_exists(var: ctk.StringVar) -> None:
            path = var.get()
            if path:
                # Don't create if it looks like a file path
                if path.lower().endswith(
                    (
                        ".fa",
                        ".fasta",
                        ".fna",
                        ".bam",
                        ".cram",
                        ".vcf",
                        ".fastq",
                        ".fq",
                        ".gz",
                    )
                ):
                    return
                try:
                    if not os.path.exists(path):
                        os.makedirs(path, exist_ok=True)
                except Exception:
                    pass

        # Initial creation for env vars
        ensure_dir_exists(self.out_dir_var)
        ensure_dir_exists(self.ref_path_var)

        # Trace for out_dir_var to ensure it exists when changed in GUI
        self.out_dir_var.trace_add(
            "write", lambda *args: ensure_dir_exists(self.out_dir_var)
        )

        def update_vep_cache(*args):
            ref = self.ref_path_var.get()
            if ref and os.path.isdir(ref):
                self.vep_cache_var.set(os.path.join(ref, "vep"))
            else:
                self.vep_cache_var.set(os.path.expanduser("~/.vep"))

        self.ref_path_var.trace_add("write", update_vep_cache)
        update_vep_cache()  # Initial call

        # UI Layout
        self._setup_sidebar()
        self._setup_main_content()
        self._setup_output_area()
        self._setup_frames()

        # Default view
        self.show_frame("flow")

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

        # Logo/Icon in Sidebar
        if self.logo_image:
            self.logo_label = ctk.CTkLabel(
                self.sidebar_frame,
                text="",
                image=self.logo_image,
            )
            self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 0))

        ctk.CTkLabel(
            self.sidebar_frame,
            text="WGS Extract",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=1, column=0, padx=20, pady=(10, 20))

        for i, (key, meta) in enumerate(UI_METADATA.items()):
            ctk.CTkButton(
                self.sidebar_frame,
                text=meta["title"],
                command=lambda k=key: self.show_frame(k),
                font=BUTTON_FONT,
            ).grid(row=i + 2, column=0, padx=20, pady=10)

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
        self.frames: dict[str, ctk.CTkFrame] = {}
        for key, meta in UI_METADATA.items():
            if key == "lib":
                frame = LibFrame(self.main_content, self, key, meta)
            elif key == "micro":
                frame = MicroFrame(self.main_content, self, key, meta)
            elif key == "flow":
                frame = FlowFrame(self.main_content, self, key, meta)
            else:
                frame = GenericFrame(self.main_content, self, key, meta)
            self.frames[key] = frame

    def _on_mousewheel(self, event: tk.Event) -> None:
        """Handle mouse wheel events for scrolling across different widgets."""
        w = event.widget
        delta = event.num == 4 and 1 or event.num == 5 and -1 or event.delta
        curr = w
        while curr:
            if isinstance(curr, tk.Canvas | tk.Text | ctk.CTkTextbox):
                # Skip scrolling for the workflow graph canvas
                if (
                    isinstance(curr, tk.Canvas)
                    and "flow" in self.frames
                    and hasattr(self.frames["flow"], "canvas")
                    and curr == self.frames["flow"].canvas
                ):
                    break

                if isinstance(curr, tk.Canvas):
                    curr.yview_scroll(
                        int(-1 * (delta / 120))
                        if event.num not in [4, 5]
                        else -1 * delta,
                        "units",
                    )
                else:
                    curr.yview(
                        tk.SCROLL,
                        int(-1 * (delta / 120))
                        if event.num not in [4, 5]
                        else -1 * delta,
                        tk.UNITS,
                    )
                break
            try:
                master = curr.master
                if master is None:
                    break
                curr = master
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
        Append a message to the output text area and print to stdout.

        Args:
            message: The string to log.
        """
        print(message)  # Also print to terminal for easier debugging
        self.output_text.insert("end", message + "\n")
        self.output_text.see("end")

    def show_error(self, title: str, message: str) -> None:
        """Show an error message box."""
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str) -> None:
        """Show an information message box."""
        messagebox.showinfo(title, message)

    # Delegate logic methods to controller
    def run_dispatch(self, cmd: str, frame: Any) -> None:
        """Delegate command dispatch to the controller."""
        self.controller.run_dispatch(cmd, frame)

    def run_lib_download(
        self, gd: dict[str, Any], lib_frame: Any, restart: bool = False
    ) -> None:
        """Delegate library download to the controller."""
        self.controller.run_lib_download(gd, lib_frame, restart)

    def run_lib_delete(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate library deletion to the controller."""
        self.controller.run_lib_delete(group, lib_frame)

    def run_ref_index(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate reference indexing to the controller."""
        self.controller.run_ref_index(group, lib_frame)

    def run_ref_unindex(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate reference unindexing to the controller."""
        self.controller.run_ref_unindex(group, lib_frame)

    def run_ref_verify(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate reference verification to the controller."""
        self.controller.run_ref_verify(group, lib_frame)

    def run_ref_count_ns(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate reference N-counting to the controller."""
        self.controller.run_ref_count_ns(group, lib_frame)

    def run_ref_del_ns(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delegate reference N-count deletion to the controller."""
        self.controller.run_ref_del_ns(group, lib_frame)

    def cancel_lib_download(self, fn: str) -> None:
        """Delegate library download cancellation to the controller."""
        self.controller.cancel_lib_download(fn)

    def cancel_vep_download(self) -> None:
        """Delegate VEP download cancellation to the controller."""
        self.controller.cancel_vep_download()

    def cancel_gene_map_download(self) -> None:
        """Delegate gene map download cancellation to the controller."""
        self.controller.cancel_gene_map_download()

    def show_info_window(self, title: str, text: str) -> None:
        """Open a separate window to show detailed info."""
        InfoWindow(self, title, text)


def main() -> None:
    """Application entry point."""
    app = WGSExtractGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
