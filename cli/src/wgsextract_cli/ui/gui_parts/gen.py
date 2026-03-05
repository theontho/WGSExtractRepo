"""Generic tab frame for various CLI commands."""

import os
from typing import Any

import customtkinter as ctk

from .common import BaseFrame, ToolTip


class GenericFrame(BaseFrame):
    """
    A generic frame that can handle multiple command types based on metadata.
    Used for General, BAM, Extract, Ancestry, QC, and VCF tabs.
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the generic frame."""
        super().setup_ui()
        key = self.key
        meta = self.meta

        # Common Input Field
        if key in ["gen", "bam", "ext", "anc", "vcf", "fastq"]:
            cb = self.on_input_change if key == "gen" else None
            self.input_entry = self.create_file_selector(
                self, "Input:", os.environ.get("WGSE_INPUT", ""), on_change=cb
            )

        # Info Display area (for General tab)
        if key == "gen":
            self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.info_frame.pack(fill="x", padx=30, pady=5)

        # Common Reference Field
        if key in ["gen", "bam", "vcf", "fastq"]:
            self.ref_entry = self.create_file_selector(
                self, "Reference:", os.environ.get("WGSE_REF", "")
            )

        # Tab-Specific Fields
        if key == "gen":
            self.region_entry = self.create_entry(self, "Region (e.g. chrM):")
        elif key == "fastq":
            self.align_r1 = self.create_file_selector(self, "FASTQ R1 (for Align):")
            self.align_r2 = self.create_file_selector(self, "FASTQ R2 (optional):")
        elif key == "bam":
            self.extra_entry = self.create_entry(self, "Extra (Fraction/Region):")
        elif key == "ext":
            self.out_dir = self.create_dir_selector(
                self, "Out Dir:", os.environ.get("WGSE_OUTDIR", "")
            )
            self.region_entry = self.create_entry(self, "Custom Region:")
        elif key == "anc":
            self.yleaf_path = self.create_file_selector(self, "Yleaf Path:")
            self.yleaf_pos = self.create_file_selector(self, "Pos File:")
            self.haplogrep_path = self.create_file_selector(self, "Haplogrep Path:")
        elif key == "vcf":
            self.vcf_e1 = self.create_file_selector(self, "Mother/Ann VCF:")
            self.vcf_e2 = self.create_file_selector(self, "Father/Filter Expr:")
            self.vcf_e3 = self.create_entry(self, "Gene/Region:")
            self.vcf_vep_cache = self.create_dir_selector(
                self, "VEP Cache:", os.path.expanduser("~/.vep")
            )
            self.vcf_vep_args = self.create_entry(self, "Extra VEP Args:")

        # Action Buttons Grid
        grid_f = ctk.CTkFrame(self, fg_color="transparent")
        grid_f.pack(fill="x", padx=20, pady=10)
        self.cmd_buttons = {}
        for i, cmd_m in enumerate(meta["commands"]):
            r, c = divmod(i, 3)
            grid_f.grid_columnconfigure(c, weight=1)
            
            # Special styling for destructive commands
            is_destructive = cmd_m["cmd"] in ["clear-cache", "unsort", "unindex"]
            btn_color = ("#d32f2f", "#b71c1c") if is_destructive else None
            
            btn = ctk.CTkButton(
                grid_f,
                text=cmd_m["label"],
                fg_color=btn_color,
                hover_color="#9a0007" if is_destructive else None,
                command=lambda cc=cmd_m["cmd"]: self.handle_button_click(cc),
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cmd_m["help"])
            self.cmd_buttons[cmd_m["cmd"]] = btn
            
            # Hide clear-cache by default
            if cmd_m["cmd"] == "clear-cache":
                btn.grid_remove()

        # Auto-trigger if initial value exists
        if key == "gen" and self.input_entry.get():
            self.on_input_change(self.input_entry.get())

    def on_input_change(self, value: str) -> None:
        """Called when the input file path changes."""
        if value.lower().endswith((".bam", ".cram")):
            self.main_app.controller.get_info_fast(value, self)
        else:
            self.update_info_display(None)

    def update_info_display(self, data: Any) -> None:
        """Update the info frame with fast info output (dict or error string)."""
        # Toggle clear-cache button visibility
        if "clear-cache" in self.cmd_buttons:
            input_path = self.input_entry.get()
            json_cache = ""
            if input_path:
                outdir = os.path.dirname(os.path.abspath(input_path))
                json_cache = os.path.join(outdir, f"{os.path.basename(input_path)}.wgse_info.json")
            
            if json_cache and os.path.exists(json_cache):
                self.cmd_buttons["clear-cache"].grid()
            else:
                self.cmd_buttons["clear-cache"].grid_remove()

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
            ("Avg Read Length:", f"{data.get('avg_read_len', 0):.0f} bp, {data.get('std_read_len', 0):.0f} σ, {'Paired-end' if data.get('is_paired') else 'Single-end'}"),
            ("Avg Insert Size:", f"{data.get('avg_insert_size', 0):.0f} bp, {data.get('std_insert_size', 0):.0f} σ"),
        ]
        
        if data.get("sequencer") and data.get("sequencer") != "Unknown":
            items.append(("Sequencer:", data.get("sequencer")))

        for i, (label, val) in enumerate(items):
            ctk.CTkLabel(
                self.info_frame, text=label, font=ctk.CTkFont(size=13, weight="bold"), width=140, anchor="w"
            ).grid(row=i, column=0, sticky="w", padx=(0, 10))
            ctk.CTkLabel(
                self.info_frame, text=val, font=ctk.CTkFont(size=13), anchor="w"
            ).grid(row=i, column=1, sticky="w")

    def handle_button_click(self, cmd_key: str) -> None:
        """Handle button click, either running a new command or cancelling an active one."""
        if cmd_key in self.main_app.controller.active_processes:
            self.main_app.controller.cancel_cmd(cmd_key)
        else:
            self.main_app.run_dispatch(cmd_key, self)

    def set_button_state(self, cmd_key: str, state: str) -> None:
        """Update button text and color based on execution state."""
        if cmd_key not in self.cmd_buttons:
            return

        btn = self.cmd_buttons[cmd_key]
        if state == "running":
            btn.configure(
                text="Cancel", fg_color=("#cfd8dc", "#455a64"), hover_color=("#b0bec5", "#37474f"), text_color=("#000000", "#ffffff")
            )
        else:
            # Restore original label and color from meta
            label = next(c["label"] for c in self.meta["commands"] if c["cmd"] == cmd_key)
            is_destructive = cmd_key in ["clear-cache", "unsort", "unindex"]
            orig_color = ("#d32f2f", "#b71c1c") if is_destructive else ("#3a7ebf", "#1f538d")
            orig_hover = "#9a0007" if is_destructive else ("#325882", "#14375e")
            orig_text = "#ffffff"

            btn.configure(text=label, fg_color=orig_color, hover_color=orig_hover, text_color=orig_text)
