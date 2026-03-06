"""Microarray simulation tab frame for generating CombinedKit formats."""

from typing import Any

import customtkinter as ctk

from wgsextract_cli.ui.constants import BUTTON_FONT, MICROARRAY_FORMATS

from .common import ScrollableBaseFrame, ToolTip


class MicroFrame(ScrollableBaseFrame):
    """
    A frame for configuring and launching microarray simulations for various vendors
    (23andMe, AncestryDNA, FTDNA, MyHeritage, etc.).
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the microarray frame."""
        super().setup_ui()

        # File Selectors
        self.bam_entry = self.create_file_selector(
            self,
            "BAM/CRAM Input:",
            variable=self.main_app.bam_path_var,
            info_text="Select your aligned DNA data (BAM or CRAM file).",
        )
        self.ref_entry = self.create_dir_selector(
            self,
            "Reference:",
            variable=self.main_app.ref_path_var,
            info_text="Select the directory containing the reference genome library.",
        )
        self.out_dir = self.create_dir_selector(
            self,
            "Out Dir:",
            variable=self.main_app.out_dir_var,
            info_text="Directory where generated CombinedKit files will be saved.",
        )

        ctk.CTkLabel(
            self,
            text="Select Target Formats:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))

        # Buttons Row (Selection Utility + Action)
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=5)

        btn_all = ctk.CTkButton(
            bf,
            text="Select All",
            width=100,
            command=self.micro_select_all,
            font=BUTTON_FONT,
        )
        btn_all.pack(side="left", padx=5)
        ToolTip(btn_all, "Select all available microarray vendor formats.")

        btn_none = ctk.CTkButton(
            bf,
            text="Unselect All",
            width=100,
            command=self.micro_unselect_all,
            font=BUTTON_FONT,
        )
        btn_none.pack(side="left", padx=5)
        ToolTip(btn_none, "Deselect all microarray vendor formats.")

        btn_rec = ctk.CTkButton(
            bf,
            text="Select Recommended",
            width=150,
            command=self.micro_select_recommended,
            font=BUTTON_FONT,
        )
        btn_rec.pack(side="left", padx=5)
        ToolTip(btn_rec, "Select only the most common and compatible vendor formats.")

        btn_gen = ctk.CTkButton(
            bf,
            text="Generate CombinedKit",
            command=lambda: self.handle_button_click("microarray"),
            font=BUTTON_FONT,
        )
        btn_gen.pack(side="right", padx=5)
        self.cmd_buttons["microarray"] = btn_gen
        from wgsextract_cli.ui.constants import UI_TOOLTIPS

        ToolTip(btn_gen, UI_TOOLTIPS["microarray"])

        # Format Selection Grid
        ff = ctk.CTkFrame(self, fg_color="transparent")
        ff.pack(fill="x", padx=20, pady=5)

        # Group formats by vendor
        vds: dict[str, list[dict[str, Any]]] = {}
        for f in MICROARRAY_FORMATS:
            vds.setdefault(f["vendor"], []).append(f)

        self.micro_formats_vars: dict[str, ctk.BooleanVar] = {}
        ri = 0
        for vendor, fmts in vds.items():
            ctk.CTkLabel(
                ff, text=vendor, font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=ri, column=0, columnspan=3, sticky="w", padx=10, pady=(5, 2))
            ri += 1
            for i, f in enumerate(fmts):
                r, c = divmod(i, 3)
                var = ctk.BooleanVar(value=f.get("recommended", False))
                self.micro_formats_vars[f["id"]] = var
                ctk.CTkCheckBox(ff, text=f["label"], variable=var).grid(
                    row=ri + r, column=c, sticky="w", padx=20, pady=2
                )
            ri += (len(fmts) + 2) // 3

    def micro_select_all(self) -> None:
        """Select all available microarray formats."""
        for v in self.micro_formats_vars.values():
            v.set(True)

    def micro_unselect_all(self) -> None:
        """Unselect all microarray formats."""
        for v in self.micro_formats_vars.values():
            v.set(False)

    def micro_select_recommended(self) -> None:
        """Select only the recommended microarray formats."""
        ids = [f["id"] for f in MICROARRAY_FORMATS if f.get("recommended")]
        for fid, v in self.micro_formats_vars.items():
            v.set(fid in ids)
