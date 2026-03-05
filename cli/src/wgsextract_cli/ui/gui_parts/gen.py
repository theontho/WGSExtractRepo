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

        # Shared Reference Field
        if key in ["gen", "vcf", "fastq"]:
            self.ref_entry = self.create_file_selector(
                self,
                "Reference:",
                variable=self.main_app.ref_path_var,
                info_text="Path to the reference genome FASTA file (.fa or .fasta).",
            )

        # Typed Input Fields
        self.cmd_buttons: dict[str, ctk.CTkButton] = {}
        cmds_to_hide: set[str] = set()

        if key in ["gen", "ext", "anc", "vcf", "fastq"]:
            cb = self.on_input_change if key == "gen" else None

            button_text = None
            command = None
            if key == "fastq":
                unalign_cmd = next(c for c in meta["commands"] if c["cmd"] == "unalign")
                button_text = unalign_cmd["label"]

                def unalign_cb():
                    return self.handle_button_click("unalign")

                command = unalign_cb
                cmds_to_hide.add("unalign")

            self.bam_entry = self.create_file_selector(
                self,
                "BAM/CRAM:",
                variable=self.main_app.bam_path_var,
                on_change=cb,
                button_text=button_text,
                command=command,
                info_text="Input BAM or CRAM file.",
            )

            if key == "fastq" and "unalign" in cmds_to_hide:
                self.cmd_buttons["unalign"] = self.bam_entry.action_button
                ToolTip(self.cmd_buttons["unalign"], unalign_cmd["help"])

        if key == "vcf":
            self.vcf_entry = self.create_file_selector(
                self,
                "VCF Input:",
                variable=self.main_app.vcf_path_var,
                info_text="Input VCF file for processing (Annotate, Filter, QC).",
            )

        # Info Display area (for General tab)
        if key == "gen":
            self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.info_frame.pack(fill="x", padx=30, pady=5)

        # Tab-Specific Fields
        if key == "gen":
            # No region_entry here anymore
            pass
        elif key == "fastq":
            align_cmd = next(c for c in meta["commands"] if c["cmd"] == "align")
            self.align_r1 = self.create_file_selector(
                self,
                "FASTQ R1:",
                button_text=align_cmd["label"],
                command=lambda: self.handle_button_click("align"),
                info_text="First read file (R1) for alignment.",
            )
            self.cmd_buttons["align"] = self.align_r1.action_button
            ToolTip(self.cmd_buttons["align"], align_cmd["help"])
            cmds_to_hide.add("align")

            self.align_r2 = self.create_file_selector(
                self,
                "FASTQ R2 (optional):",
                info_text="Second read file (R2) for paired-end alignment.",
            )

            # FastQ for QC as the last field
            self.fastq_entry = self.create_file_selector(
                self,
                "FASTQ for QC:",
                variable=self.main_app.fastq_path_var,
                info_text="Primary FASTQ file for QC actions (FastQC, FastP).",
            )

        elif key == "ext":
            self.out_dir = self.create_dir_selector(
                self,
                "Out Dir:",
                variable=self.main_app.out_dir_var,
                info_text="Directory where extracted files will be saved.",
            )

            # Get commands to extract labels and help
            custom_cmd = next(c for c in meta["commands"] if c["cmd"] == "custom")
            subset_cmd = next(c for c in meta["commands"] if c["cmd"] == "subset")

            self.region_entry = self.create_entry(
                self,
                "Region (e.g. chrM):",
                button_text=custom_cmd["label"],
                command=lambda: self.handle_button_click("custom"),
                info_text="Specify a chromosomal region (e.g., chr1:100-200) to extract.",
            )
            self.cmd_buttons["custom"] = self.region_entry.action_button
            ToolTip(self.cmd_buttons["custom"], custom_cmd["help"])
            cmds_to_hide.add("custom")

            self.extra_entry = self.create_entry(
                self,
                "Extra (e.g. -f 0.1 for subset):",
                button_text=subset_cmd["label"],
                command=lambda: self.handle_button_click("subset"),
                info_text="Additional parameters, like fraction (-f 0.1) for subsetting reads.",
            )
            self.cmd_buttons["subset"] = self.extra_entry.action_button
            ToolTip(self.cmd_buttons["subset"], subset_cmd["help"])
            cmds_to_hide.add("subset")

        elif key == "anc":
            y_cmd = next(c for c in meta["commands"] if c["cmd"] == "lineage-y")
            mt_cmd = next(c for c in meta["commands"] if c["cmd"] == "lineage-mt")

            self.yleaf_path = self.create_file_selector(
                self,
                "Yleaf Path:",
                info_text="Path to the Yleaf executable for Y-haplogroup prediction.",
            )
            self.yleaf_pos = self.create_file_selector(
                self,
                "Pos File:",
                button_text=y_cmd["label"],
                command=lambda: self.handle_button_click("lineage-y"),
                info_text="Yleaf position file (e.g., data/yleaf/pos.txt).",
            )
            self.cmd_buttons["lineage-y"] = self.yleaf_pos.action_button
            ToolTip(self.cmd_buttons["lineage-y"], y_cmd["help"])
            cmds_to_hide.add("lineage-y")

            self.haplogrep_path = self.create_file_selector(
                self,
                "Haplogrep Path:",
                button_text=mt_cmd["label"],
                command=lambda: self.handle_button_click("lineage-mt"),
                info_text="Path to the Haplogrep jar or executable for mitochondrial lineage.",
            )
            self.cmd_buttons["lineage-mt"] = self.haplogrep_path.action_button
            ToolTip(self.cmd_buttons["lineage-mt"], mt_cmd["help"])
            cmds_to_hide.add("lineage-mt")

        elif key == "vcf":
            trio_cmd = next(c for c in meta["commands"] if c["cmd"] == "trio")
            ann_cmd = next(c for c in meta["commands"] if c["cmd"] == "annotate")
            filter_cmd = next(c for c in meta["commands"] if c["cmd"] == "filter")
            vep_cmd = next(c for c in meta["commands"] if c["cmd"] == "vep-run")

            # 1. Variant Calling & Annotation Section
            ctk.CTkLabel(
                self,
                text="Variant Calling & Annotation",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=(15, 5))

            self.vcf_region = self.create_entry(
                self,
                "Region:",
                info_text="Specific chromosomal region (e.g., chrM, chr1:100-200). Used by: Calling actions (BAM), Filter (VCF), and Run VEP.",
            )

            self.vcf_gene = self.create_entry(
                self,
                "Gene Name:",
                info_text="Target gene name (e.g., BRCA1). Used by: Filter (VCF).",
            )

            self.vcf_filter_expr = self.create_entry(
                self,
                "Filter Expr:",
                button_text=filter_cmd["label"],
                command=lambda: self.handle_button_click("filter"),
                info_text="BCFTools filter expression (e.g., 'QUAL>30 && DP>10'). Used by: Filter (VCF).",
            )
            self.cmd_buttons["filter"] = self.vcf_filter_expr.action_button
            ToolTip(self.cmd_buttons["filter"], filter_cmd["help"])
            cmds_to_hide.add("filter")

            self.vcf_ann_vcf = self.create_file_selector(
                self,
                "Annotate VCF:",
                button_text=ann_cmd["label"],
                command=lambda: self.handle_button_click("annotate"),
                info_text="VCF file to use for annotation (e.g., ClinVar, dbSNP).",
            )
            self.cmd_buttons["annotate"] = self.vcf_ann_vcf.action_button
            ToolTip(self.cmd_buttons["annotate"], ann_cmd["help"])
            cmds_to_hide.add("annotate")

            # Calling Buttons Grid (SNP, InDel, Freebayes, etc.)
            calling_cmd_keys = [
                "snp",
                "indel",
                "sv",
                "cnv",
                "freebayes",
                "gatk",
                "deepvariant",
                "vcf-qc",
                "repair-ftdna-vcf",
            ]
            calling_cmds = [c for c in meta["commands"] if c["cmd"] in calling_cmd_keys]
            self._create_section(None, calling_cmds)
            for c in calling_cmds:
                cmds_to_hide.add(c["cmd"])

            # 2. Trio Analysis Section
            ctk.CTkLabel(
                self, text="Trio Analysis", font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(15, 5))

            self.vcf_mother = self.create_file_selector(
                self,
                "Mother VCF:",
                button_text=None,
                info_text="Path to the mother's VCF for trio analysis.",
            )
            self.vcf_father = self.create_file_selector(
                self,
                "Father VCF:",
                button_text=trio_cmd["label"],
                command=lambda: self.handle_button_click("trio"),
                info_text="Path to the father's VCF for trio analysis. The proband should be in the primary VCF Input field.",
            )
            self.cmd_buttons["trio"] = self.vcf_father.action_button
            ToolTip(self.cmd_buttons["trio"], trio_cmd["help"])
            cmds_to_hide.add("trio")

            # 3. VEP Analysis Section
            ctk.CTkLabel(
                self, text="VEP Analysis", font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(15, 5))

            self.vcf_vep_cache = self.create_read_only_entry_with_info(
                self,
                "VEP Cache:",
                self.main_app.vep_cache_var,
                "Location of Ensembl VEP cache data. Derived from the current Reference path.",
            )

            self.vcf_vep_args = self.create_entry(
                self,
                "Extra VEP Args:",
                button_text=vep_cmd["label"],
                command=lambda: self.handle_button_click("vep-run"),
                info_text="Additional raw command-line arguments to pass to VEP. Uses BAM/CRAM if provided, otherwise VCF Input.",
            )
            self.cmd_buttons["vep-run"] = self.vcf_vep_args.action_button
            ToolTip(self.cmd_buttons["vep-run"], vep_cmd["help"])
            cmds_to_hide.add("vep-run")

        # Action Buttons Section
        if key == "gen":
            self._create_section("Info Commands", meta["info_commands"])
            self._create_section("BAM / CRAM Management", meta["bam_commands"])
        else:
            # Filter commands that are already in entries
            cmds_to_show = [c for c in meta["commands"] if c["cmd"] not in cmds_to_hide]
            self._create_section(None, cmds_to_show)

        # Auto-trigger if initial value exists
        if key == "gen" and hasattr(self, "bam_entry") and self.bam_entry.get():
            # Use after to defer until mainloop is ready
            self.after(100, lambda: self.on_input_change(self.bam_entry.get()))

    def _create_section(
        self, title: str | None, commands: list[dict[str, Any]]
    ) -> None:
        """Helper to create a section of command buttons."""
        if not commands:
            return

        if title:
            ctk.CTkLabel(
                self, text=title, font=ctk.CTkFont(size=14, weight="bold")
            ).pack(pady=(15, 5))

        grid_f = ctk.CTkFrame(self, fg_color="transparent")
        grid_f.pack(fill="x", padx=20, pady=5)

        for i, cmd_m in enumerate(commands):
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

    def on_input_change(self, value: str) -> None:
        """Called when the input file path changes."""
        if value.lower().endswith((".bam", ".cram")):
            self.main_app.controller.get_info_fast(value, self)
        else:
            # Always ensure GUI updates run on the main thread
            self.after(0, lambda: self.update_info_display(None))

    def update_info_display(self, data: Any) -> None:
        """Update the info frame with fast info output (dict or error string)."""
        if not self.winfo_exists():
            return

        # Toggle clear-cache button visibility
        if "clear-cache" in self.cmd_buttons:
            input_path = self.bam_entry.get()
            json_cache = ""
            if input_path:
                outdir = os.path.dirname(os.path.abspath(input_path))
                json_cache = os.path.join(
                    outdir, f"{os.path.basename(input_path)}.wgse_info.json"
                )

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
            (
                "Avg Read Length:",
                f"{data.get('avg_read_len', 0):.0f} bp, {data.get('std_read_len', 0):.0f} σ, {'Paired-end' if data.get('is_paired') else 'Single-end'}",
            ),
            (
                "Avg Insert Size:",
                f"{data.get('avg_insert_size', 0):.0f} bp, {data.get('std_read_len', 0):.0f} σ",
            ),
        ]

        if data.get("sequencer") and data.get("sequencer") != "Unknown":
            items.append(("Sequencer:", data.get("sequencer")))

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

    def handle_button_click(self, cmd_key: str) -> None:
        """Handle button click, either running a new command or cancelling an active one."""
        if cmd_key in self.main_app.controller.active_processes:
            self.main_app.controller.cancel_cmd(cmd_key)
        else:
            self.main_app.run_dispatch(cmd_key, self)

    def set_button_state(self, cmd_key: str, state: str) -> None:
        """Update button text and color based on execution state."""
        if not self.winfo_exists() or cmd_key not in self.cmd_buttons:
            return

        btn = self.cmd_buttons[cmd_key]
        if state == "running":
            btn.configure(
                text="Cancel",
                fg_color=("#cfd8dc", "#455a64"),
                hover_color=("#b0bec5", "#37474f"),
                text_color=("#000000", "#ffffff"),
            )
        else:
            # Restore original label and color from meta
            # Handle split commands for 'gen' key
            all_cmds = []
            if self.key == "gen":
                all_cmds = self.meta["info_commands"] + self.meta["bam_commands"]
            else:
                all_cmds = self.meta["commands"]

            label = next(c["label"] for c in all_cmds if c["cmd"] == cmd_key)
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
