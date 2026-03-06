"""Generic tab frame for various CLI commands."""

from typing import Any

import customtkinter as ctk

from wgsextract_cli.ui.constants import BUTTON_FONT

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
            self.ref_entry = self.create_dir_selector(
                self,
                "Reference:",
                variable=self.main_app.ref_path_var,
                info_text="Path to the directory containing your reference genomes (FASTA files).",
            )

        # Shared Output Directory Field
        if key in ["gen", "vcf", "fastq"]:
            self.out_dir = self.create_dir_selector(
                self,
                "Out Dir:",
                variable=self.main_app.out_dir_var,
                info_text="Directory where logs, caches, and results will be saved.",
            )

        # Typed Input Fields
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
            self.create_section_title(
                self,
                "Variant Calling & Annotation",
                "Identify SNPs, InDels, and Structural Variants, then add metadata to the resulting VCF file.",
            )

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

            # Gap-aware filtering checkbox
            self.create_checkbox_with_info(
                self,
                "Gap-Aware Filtering",
                self.main_app.vcf_exclude_gaps_var,
                "Exclude variants in or near genomic gaps (requires Count Ns output for the reference).",
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
            self.create_section_title(
                self,
                "Trio Analysis",
                "Compare variant calls between a child (proband) and their parents to identify inheritance patterns and de novo mutations.",
            )

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
            self.create_section_title(
                self,
                "VEP Analysis",
                "Predict the functional impact of your variants using the Ensembl Variant Effect Predictor.",
            )

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
            self._create_section("Info Commands", meta["info_commands"], cols=4)
            self._create_section("BAM / CRAM Management", meta["bam_commands"], cols=4)
        else:
            # Filter commands that are already in entries
            cmds_to_show = [c for c in meta["commands"] if c["cmd"] not in cmds_to_hide]
            self._create_section(None, cmds_to_show)

        # Auto-trigger if initial value exists
        if key == "gen" and hasattr(self, "bam_entry") and self.bam_entry.get():
            # Use after to defer until mainloop is ready
            self.after(100, lambda: self.on_input_change(self.bam_entry.get()))
        elif key == "gen":
            # Ensure buttons are in correct initial state
            self.after(0, lambda: self.update_info_display(None))

        # Refresh info if reference or output dir changes
        if key == "gen":
            self.main_app.ref_path_var.trace_add(
                "write", lambda *args: self.on_input_change(self.bam_entry.get())
            )
            self.main_app.out_dir_var.trace_add(
                "write", lambda *args: self.on_input_change(self.bam_entry.get())
            )

    def _create_section(
        self, title: str | None, commands: list[dict[str, Any]], cols: int = 3
    ) -> None:
        """Helper to create a section of command buttons."""
        if not commands:
            return

        if title:
            # Map known titles to tooltips
            help_map = {
                "Info Commands": "Rapidly analyze file metadata and calculate genomic coverage depth.",
                "BAM / CRAM Management": "Standard file maintenance tasks including sorting, indexing, and format conversion.",
            }
            self.create_section_title(self, title, help_map.get(title))

        grid_f = ctk.CTkFrame(self, fg_color="transparent")
        grid_f.pack(fill="x", padx=20, pady=5)

        for i, cmd_m in enumerate(commands):
            r, c = divmod(i, cols)
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
                font=BUTTON_FONT,
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cmd_m["help"])
            self.cmd_buttons[cmd_m["cmd"]] = btn

            # Hide specific buttons by default in info tab
            if self.key == "gen" and cmd_m["cmd"] in [
                "clear-cache",
                "sort",
                "unsort",
                "index",
                "unindex",
                "to-bam",
                "to-cram",
            ]:
                btn.grid_remove()

    def update_info_display(self, data: Any) -> None:
        """Override to handle dynamic button layout and greying."""
        super().update_info_display(data)
        if not isinstance(data, dict):
            return

        if self.key == "ext":
            gender = data.get("gender", "").lower()
            is_female = "female" in gender
            for cmd, btn in self.cmd_buttons.items():
                if cmd in ["ydna-bam", "ydna-vcf", "y-mt-extract"]:
                    if is_female:
                        btn.configure(state="disabled", fg_color="gray")
                    else:
                        # Restore original color
                        orig_color = ("#3a7ebf", "#1f538d")
                        btn.configure(state="normal", fg_color=orig_color)

        elif self.key == "gen":
            fstats = data.get("file_stats", {})
            is_sorted = fstats.get("sorted", False)
            is_indexed = fstats.get("indexed", False)
            input_path = self.bam_entry.get() if hasattr(self, "bam_entry") else ""
            is_cram = input_path.lower().endswith(".cram")

            # 1. Update visibility
            visibility_map = {
                "sort": not is_sorted,
                "unsort": is_sorted,
                "index": is_sorted and not is_indexed,
                "unindex": is_indexed,
                "to-cram": not is_cram,
                "to-bam": is_cram,
                "clear-cache": True,
                "calculate-coverage": True,
                "coverage-sample": True,
                "info": True,
                "repair-ftdna-bam": True,
            }

            for cmd, visible in visibility_map.items():
                if cmd in self.cmd_buttons:
                    if visible:
                        self.cmd_buttons[cmd].grid()
                    else:
                        self.cmd_buttons[cmd].grid_remove()

            # 2. Re-layout sections to fill rows (fix gaps)
            self._relayout_grid("Info Commands", self.meta["info_commands"], cols=4)
            self._relayout_grid(
                "BAM / CRAM Management", self.meta["bam_commands"], cols=4
            )

    def _relayout_grid(
        self, section_title: str, commands: list[dict[str, Any]], cols: int
    ) -> None:
        """Dynamically re-grid visible buttons to fill rows from left-to-right."""
        visible_btns = []
        for cmd_m in commands:
            cmd = cmd_m["cmd"]
            if (
                cmd in self.cmd_buttons
                and self.cmd_buttons[cmd].winfo_manager() == "grid"
            ):
                visible_btns.append(self.cmd_buttons[cmd])

        for i, btn in enumerate(visible_btns):
            r, c = divmod(i, cols)
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")

    def on_input_change(self, value: str) -> None:
        """Called when the input file path changes."""
        if value.lower().endswith((".bam", ".cram")):
            ref_path = (
                self.main_app.ref_path_var.get()
                if hasattr(self, "main_app") and hasattr(self.main_app, "ref_path_var")
                else None
            )
            self.main_app.controller.get_info_fast(value, self, ref_path=ref_path)
        else:
            # Always ensure GUI updates run on the main thread
            self.after(0, lambda: self.update_info_display(None))
