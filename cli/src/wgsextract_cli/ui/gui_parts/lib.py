"""Library management tab frame for reference genomes and VEP cache."""

import os
import re
from typing import Any

import customtkinter as ctk

from .common import BaseFrame, ToolTip


class LibFrame(BaseFrame):
    """
    A frame for managing reference genomes (downloading, deleting, indexing)
    and VEP (Variant Effect Predictor) caches.
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the library frame."""
        from wgsextract_cli.core.ref_library import (
            get_genome_size,
            get_genome_status,
            get_grouped_genomes,
        )

        # Clear existing widgets if refreshing
        for widget in self.winfo_children():
            widget.destroy()

        super().setup_ui()
        meta = self.meta

        # Directory and Basic Selectors
        ldf = ctk.CTkFrame(self)
        ldf.pack(fill="x", padx=20, pady=5)
        self.lib_dest = self.create_dir_selector(
            ldf, "Library Dir:", os.environ.get("WGSE_REF", "")
        )
        ctk.CTkButton(ldf, text="Refresh List", width=100, command=self.setup_ui).pack(
            side="right", padx=10
        )

        self.input_entry = self.create_file_selector(
            self, "Input:", os.environ.get("WGSE_INPUT", "")
        )
        ref_val = os.environ.get("WGSE_REF", "")
        self.ref_entry = self.create_file_selector(self, "Reference:", ref_val)

        # 1. Reference Management Section
        if meta["commands"]:
            self._setup_ref_mgmt_section(meta["commands"])

        # 2. VEP Management Section
        self._setup_vep_mgmt_section(meta["vep_commands"], ref_val)

        # 3. Reference Genome List Section
        self._setup_ref_list_section(
            get_grouped_genomes, get_genome_status, get_genome_size
        )

    def _setup_ref_mgmt_section(self, commands: list[dict[str, Any]]) -> None:
        """Set up the action buttons for general reference management."""
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            bf,
            text="Reference Management",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(0, 5))
        gf = ctk.CTkFrame(self, fg_color="transparent")
        gf.pack(fill="x", padx=20)
        for i, cm in enumerate(commands):
            r, c = divmod(i, 3)
            gf.grid_columnconfigure(c, weight=1)
            btn = ctk.CTkButton(
                gf,
                text=cm["label"],
                command=lambda cc=cm["cmd"]: self.main_app.run_dispatch(cc, self),
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cm["help"])

    def _setup_vep_mgmt_section(
        self, vep_commands: list[dict[str, Any]], ref_val: str
    ) -> None:
        """Set up the VEP cache management controls and progress bars."""
        vep_f = ctk.CTkFrame(self, fg_color="transparent")
        vep_f.pack(fill="x", padx=20, pady=(20, 10))
        vep_h = ctk.CTkFrame(vep_f, fg_color="transparent")
        vep_h.pack(fill="x")
        ctk.CTkLabel(
            vep_h, text="VEP Cache Management", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        v_info = ctk.CTkLabel(
            vep_h,
            text=" ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#55aaff",
            cursor="hand2",
        )
        v_info.pack(side="left", padx=5)
        ToolTip(
            v_info,
            "VEP (Variant Effect Predictor) uses a large cache of genomic data to determine how variants (SNPs/InDels) might affect genes and proteins.",
        )

        dv = (
            os.path.join(ref_val, "vep")
            if ref_val and os.path.isdir(ref_val)
            else os.path.expanduser("~/.vep")
        )
        self.vep_cache = self.create_dir_selector(self, "VEP Cache Path:", dv)

        vep_btn_f = ctk.CTkFrame(self, fg_color="transparent")
        vep_btn_f.pack(fill="x", padx=20)
        for i, cm in enumerate(vep_commands):
            vep_btn_f.grid_columnconfigure(i, weight=1)
            btn = ctk.CTkButton(
                vep_btn_f,
                text=cm["label"],
                command=lambda cc=cm["cmd"]: self.main_app.run_dispatch(cc, self),
            )
            btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cm["help"])

        # VEP Progress UI
        self.vep_prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.vep_prog_var = ctk.DoubleVar(value=0)
        self.vep_stat_var = ctk.StringVar(value="")
        self.vep_pbar = ctk.CTkProgressBar(
            self.vep_prog_frame, variable=self.vep_prog_var, width=300
        )
        self.vep_stat_lbl = ctk.CTkLabel(
            self.vep_prog_frame,
            textvariable=self.vep_stat_var,
            font=ctk.CTkFont(size=11),
        )
        self.vep_cancel_btn = ctk.CTkButton(
            self.vep_prog_frame,
            text="Cancel",
            width=60,
            fg_color="#666666",
            command=self.main_app.cancel_vep_download,
        )

    def _setup_ref_list_section(
        self, get_grouped_genomes: Any, get_genome_status: Any, get_genome_size: Any
    ) -> None:
        """Set up the interactive list of available reference genomes."""
        hf = ctk.CTkFrame(self, fg_color="transparent")
        hf.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            hf, text="Reference Genomes", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        ii = ctk.CTkLabel(
            hf,
            text=" ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#55aaff",
            cursor="hand2",
        )
        ii.pack(side="left", padx=5)
        ToolTip(ii, "Baseline DNA sequences used for comparison during analysis.")

        dest = self.lib_dest.get()
        grouped = get_grouped_genomes()
        for group in grouped:
            self._create_genome_row(group, dest, get_genome_status, get_genome_size)

    def _create_genome_row(
        self,
        group: dict[str, Any],
        dest: str,
        get_genome_status: Any,
        get_genome_size: Any,
    ) -> None:
        """Create a single row for a reference genome in the list."""
        row = ctk.CTkFrame(self)
        row.pack(fill="x", padx=20, pady=5)
        fn = group["final"]
        lt = group["label"]
        s = get_genome_status(fn, dest)
        sz = get_genome_size(fn, dest)
        sl = f" ({sz})" if sz else ""

        # Tags processing
        tags = []
        if "(Rec)" in lt:
            tags.append(("Recommended", "#228822"))
            lt = lt.replace("(Rec)", "").strip()
        lt = re.sub(r"\s+", " ", lt).strip(" -_")

        ctk.CTkLabel(
            row, text=f"{lt}{sl}", anchor="w", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=10)

        for tt, tc in tags:
            ctk.CTkLabel(
                row,
                text=tt,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=tc,
                text_color="white",
                corner_radius=10,
                padx=6,
                pady=0,
                height=16,
            ).pack(side="left", padx=2)

        if fn in self.main_app.active_downloads:
            self._add_download_status(row, fn)
        elif s == "installed":
            self._add_installed_controls(row, group)
        elif s == "incomplete":
            self._add_incomplete_controls(row, group)
        else:
            self._add_available_controls(row, group)

    def _add_download_status(self, row: ctk.CTkFrame, fn: str) -> None:
        di = self.main_app.active_downloads[fn]
        dc = ctk.CTkFrame(row, fg_color="transparent")
        dc.pack(side="right", padx=10)
        ctk.CTkProgressBar(dc, variable=di["progress_var"], width=150).pack(
            side="left", padx=5
        )
        ctk.CTkLabel(dc, textvariable=di["status_var"], font=ctk.CTkFont(size=10)).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            dc,
            text="Cancel",
            width=60,
            fg_color="#666666",
            hover_color="#888888",
            command=lambda f=fn: self.main_app.cancel_lib_download(f),
        ).pack(side="left", padx=5)

    def _add_installed_controls(self, row: ctk.CTkFrame, group: dict[str, Any]) -> None:
        btn = ctk.CTkButton(
            row,
            text="Delete",
            width=80,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_lib_delete(g, self),
        )
        btn.pack(side="right", padx=10)
        ToolTip(btn, f"Remove {group['final']} and index files.")

    def _add_incomplete_controls(
        self, row: ctk.CTkFrame, group: dict[str, Any]
    ) -> None:
        ctk.CTkButton(
            row,
            text="Delete",
            width=70,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_lib_delete(g, self),
        ).pack(side="right", padx=10)
        ctk.CTkButton(
            row,
            text="Restart",
            width=70,
            fg_color="#aa6622",
            hover_color="#cc8844",
            command=lambda g=group: self.main_app.run_lib_download(
                g["sources"][0], self, restart=True
            ),
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            row,
            text="Resume",
            width=70,
            fg_color="#228822",
            hover_color="#33aa33",
            command=lambda g=group: self.main_app.run_lib_download(
                g["sources"][0], self
            ),
        ).pack(side="right", padx=5)
        ctk.CTkLabel(
            row,
            text="Incomplete",
            text_color="#ffaa00",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="right", padx=10)

    def _add_available_controls(self, row: ctk.CTkFrame, group: dict[str, Any]) -> None:
        for sd in reversed(group["sources"]):
            sb = ctk.CTkButton(
                row,
                text=sd["source"],
                width=60,
                command=lambda s=sd: self.main_app.run_lib_download(s, self),
            )
            sb.pack(side="right", padx=5)
            ToolTip(sb, f"Download from {sd['source']}")
        ctk.CTkLabel(
            row, text="download from", font=ctk.CTkFont(size=11, slant="italic")
        ).pack(side="right", padx=5)

    def show_vep_progress(self) -> None:
        """Display the VEP progress bar and status labels."""
        self.vep_prog_frame.pack(fill="x", padx=20, pady=5)
        self.vep_pbar.pack(side="left", padx=5)
        self.vep_stat_lbl.pack(side="left", padx=5)
        self.vep_cancel_btn.pack(side="left", padx=5)

    def hide_vep_progress(self) -> None:
        """Hide the VEP progress UI elements."""
        self.vep_prog_frame.pack_forget()
        self.vep_pbar.pack_forget()
        self.vep_stat_lbl.pack_forget()
        self.vep_cancel_btn.pack_forget()
