"""Generic tab frame for various CLI commands."""

from typing import Any

import customtkinter as ctk

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS

from .common import ScrollableBaseFrame, ToolTip


class GenericFrame(ScrollableBaseFrame):
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
        if key in ["gen", "vcf"]:
            self.create_ref_selector(self, meta)

        # Shared Output Directory Field
        if key in ["gen", "vcf", "fastq"]:
            self.out_dir = self.create_dir_selector(
                self,
                GUI_LABELS["out_dir"],
                variable=self.main_app.out_dir_var,
                info_text=GUI_TOOLTIPS["out_dir_tip"],
            )

        # Typed Input Fields
        cmds_to_hide: set[str] = set()

        if key in ["gen", "ext", "anc", "vcf"]:
            cb = self.on_input_change if key == "gen" else None

            self.bam_entry = self.create_file_selector(
                self,
                GUI_LABELS["bam_cram"],
                variable=self.main_app.bam_path_var,
                on_change=cb,
                info_text=GUI_TOOLTIPS["bam_input_tip"],
            )

        elif key == "fastq":
            # Separate BAM/CRAM input for Unalign
            self.create_section_title(self, "BAM / CRAM -> FASTQ")
            unalign_cmd = next(c for c in meta["commands"] if c["cmd"] == "unalign")

            self.bam_entry = self.create_file_selector(
                self,
                GUI_LABELS["bam_cram"],
                variable=self.main_app.bam_path_var,
                button_text=unalign_cmd["label"],
                command=lambda: self.handle_button_click("unalign"),
                info_text=GUI_TOOLTIPS["bam_input_tip"],
            )
            self.cmd_buttons["unalign"] = self.bam_entry.action_button
            ToolTip(self.cmd_buttons["unalign"], unalign_cmd["help"])
            cmds_to_hide.add("unalign")

            # FASTQ Input Section
            self.create_section_title(self, "FASTQ -> BAM/CRAM")

            # Reference fields (including dropdown via override in FastqFrame)
            self.create_ref_selector(self, meta)

            self.align_r1 = self.create_file_selector(
                self,
                GUI_LABELS["fastq_r1"],
                info_text=GUI_TOOLTIPS["pet_r1_tip"],
            )

            self.align_r2 = self.create_file_selector(
                self,
                GUI_LABELS["fastq_r2"],
                info_text=GUI_TOOLTIPS["pet_r2_tip"],
            )

            # Output format selection
            self.output_format_var = ctk.StringVar(value="BAM")
            self.create_option_menu(
                self,
                GUI_LABELS["output_format"],
                options=["BAM", "CRAM"],
                variable=self.output_format_var,
                info_text=GUI_TOOLTIPS["output_fmt_tip"],
            )

        if key == "vcf":
            self.vcf_entry = self.create_file_selector(
                self,
                GUI_LABELS["vcf_input"],
                variable=self.main_app.vcf_path_var,
                info_text=GUI_TOOLTIPS["vcf_input_tip"],
            )

        # Info Display area (for General tab)
        if key == "gen":
            self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
            self.info_frame.pack(fill="x", padx=30, pady=5)

            # CRAM Version selector for General tab
            self.cram_version_var = ctk.StringVar(value="3.0")
            self.create_option_menu(
                self,
                "Output CRAM Version:",
                options=["2.1", "3.0", "3.1"],
                variable=self.cram_version_var,
                info_text="Select CRAM version for to-cram conversion. 3.0 is recommended for GATK compatibility.",
            )

        # Tab-Specific Fields
        if key == "gen":
            # No region_entry here anymore
            pass
        elif key == "fastq":
            # Already handled in Typed Input Fields above
            pass
        elif key == "ext":
            self.out_dir = self.create_dir_selector(
                self,
                GUI_LABELS["out_dir"],
                variable=self.main_app.out_dir_var,
                info_text="Directory where extracted files will be saved.",
            )

            # Get commands to extract labels and help
            custom_cmd = next(c for c in meta["commands"] if c["cmd"] == "custom")
            subset_cmd = next(c for c in meta["commands"] if c["cmd"] == "bam-subset")

            self.region_entry = self.create_entry(
                self,
                GUI_LABELS["region_label"],
                button_text=custom_cmd["label"],
                command=lambda: self.handle_button_click("custom"),
                info_text=GUI_TOOLTIPS["region_tip"],
            )
            self.cmd_buttons["custom"] = self.region_entry.action_button
            ToolTip(self.cmd_buttons["custom"], custom_cmd["help"])
            cmds_to_hide.add("custom")

            self.extra_entry = self.create_entry(
                self,
                GUI_LABELS["extra_label"],
                button_text=subset_cmd["label"],
                command=lambda: self.handle_button_click("bam-subset"),
                info_text=GUI_TOOLTIPS["extra_tip"],
            )
            self.cmd_buttons["bam-subset"] = self.extra_entry.action_button
            ToolTip(self.cmd_buttons["bam-subset"], subset_cmd["help"])
            cmds_to_hide.add("bam-subset")

        elif key == "anc":
            y_cmd = next(
                c for c in meta["commands"] if c["cmd"] == "lineage-y-haplogroup"
            )
            mt_cmd = next(
                c for c in meta["commands"] if c["cmd"] == "lineage-mt-haplogroup"
            )

            self.yleaf_path = self.create_file_selector(
                self,
                GUI_LABELS["yleaf_path"],
                variable=self.main_app.yleaf_path_var,
                info_text="Path to the Yleaf executable for Y-haplogroup prediction.",
            )
            self.yleaf_pos = self.create_file_selector(
                self,
                GUI_LABELS["pos_file"],
                button_text=y_cmd["label"],
                command=lambda: self.handle_button_click("lineage-y-haplogroup"),
                info_text="Yleaf position file (e.g., data/yleaf/pos.txt).",
            )
            self.cmd_buttons["lineage-y-haplogroup"] = self.yleaf_pos.action_button
            ToolTip(self.cmd_buttons["lineage-y-haplogroup"], y_cmd["help"])
            cmds_to_hide.add("lineage-y-haplogroup")

            self.haplogrep_path = self.create_file_selector(
                self,
                GUI_LABELS["haplogrep_path"],
                variable=self.main_app.haplogrep_path_var,
                button_text=mt_cmd["label"],
                command=lambda: self.handle_button_click("lineage-mt-haplogroup"),
                info_text="Path to the Haplogrep jar or executable for mitochondrial lineage.",
            )
            self.cmd_buttons[
                "lineage-mt-haplogroup"
            ] = self.haplogrep_path.action_button
            ToolTip(self.cmd_buttons["lineage-mt-haplogroup"], mt_cmd["help"])
            cmds_to_hide.add("lineage-mt-haplogroup")

        elif key == "vcf":
            trio_cmd = next(c for c in meta["commands"] if c["cmd"] == "trio")
            ann_cmd = next(c for c in meta["commands"] if c["cmd"] == "annotate")
            filter_cmd = next(c for c in meta["commands"] if c["cmd"] == "filter")
            vep_cmd = next(c for c in meta["commands"] if c["cmd"] == "vep-run")

            # 1. Variant Calling & Annotation Section
            self.create_section_title(
                self,
                GUI_LABELS["var_calling_ann"],
                GUI_TOOLTIPS["var_calling_ann_help"],
            )

            self.vcf_region = self.create_entry(
                self,
                GUI_LABELS["region_generic"],
                info_text="Specific chromosomal region (e.g., chrM, chr1:100-200). Used by: Calling actions (BAM), Filter (VCF), and Run VEP.",
            )

            self.vcf_gene = self.create_entry(
                self,
                GUI_LABELS["gene_name"],
                info_text="Target gene name (e.g., BRCA1). Used by: Filter (VCF).",
            )

            # Gap-aware filtering checkbox
            self.create_checkbox_with_info(
                self,
                GUI_LABELS["gap_aware_filtering"],
                self.main_app.vcf_exclude_gaps_var,
                GUI_TOOLTIPS["gap_aware_tip"],
            )

            self.vcf_filter_expr = self.create_entry(
                self,
                GUI_LABELS["filter_expr"],
                button_text=filter_cmd["label"],
                command=lambda: self.handle_button_click("filter"),
                info_text="BCFTools filter expression (e.g., 'QUAL>30 && DP>10'). Used by: Filter (VCF).",
            )
            self.cmd_buttons["filter"] = self.vcf_filter_expr.action_button
            ToolTip(self.cmd_buttons["filter"], filter_cmd["help"])
            cmds_to_hide.add("filter")

            self.vcf_ann_vcf = self.create_file_selector(
                self,
                GUI_LABELS["annotate_vcf"],
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
                "spliceai",
                "alphamissense",
                "pharmgkb",
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
                GUI_LABELS["trio_analysis"],
                GUI_TOOLTIPS["trio_analysis_help"],
            )

            self.vcf_mother = self.create_file_selector(
                self,
                GUI_LABELS["mother_vcf"],
                variable=self.main_app.vcf_mother_var,
                button_text=None,
                info_text="Path to the mother's VCF for trio analysis.",
            )
            self.vcf_father = self.create_file_selector(
                self,
                GUI_LABELS["father_vcf"],
                variable=self.main_app.vcf_father_var,
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
                GUI_LABELS["vep_analysis"],
                GUI_TOOLTIPS["vep_analysis_help"],
            )

            self.vcf_vep_cache = self.create_read_only_entry_with_info(
                self,
                GUI_LABELS["vep_cache"],
                self.main_app.vep_cache_var,
                GUI_TOOLTIPS["vep_cache_tip"],
            )

            self.vcf_vep_args = self.create_entry(
                self,
                GUI_LABELS["extra_vep_args"],
                button_text=vep_cmd["label"],
                command=lambda: self.handle_button_click("vep-run"),
                info_text=GUI_TOOLTIPS["vep_args_tip"],
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

    def create_ref_selector(self, p: ctk.CTkFrame, meta: dict[str, Any]) -> None:
        """Create the reference directory selector."""
        self.ref_entry = self.create_dir_selector(
            p,
            GUI_LABELS["ref_library_path"],
            variable=self.main_app.ref_path_var,
            info_text="Path to the directory containing your reference genomes.",
        )

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
            self._relayout_grid(
                GUI_LABELS["info_commands"], self.meta["info_commands"], cols=4
            )
            self._relayout_grid(
                GUI_LABELS["bam_cram_mgmt"], self.meta["bam_commands"], cols=4
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
