"""Microarray simulation tab frame for generating CombinedKit formats."""

import os
from typing import Any

import customtkinter as ctk

from wgsextract_cli.ui.constants import MICROARRAY_FORMATS
from .common import BaseFrame


class MicroFrame(BaseFrame):
    """
    A frame for configuring and launching microarray simulations for various vendors
    (23andMe, AncestryDNA, FTDNA, MyHeritage, etc.).
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the microarray frame."""
        super().setup_ui()
        key = self.key

        # File Selectors
        self.input_entry = self.create_file_selector(
            self, "Input:", os.environ.get("WGSE_INPUT", "")
        )
        self.ref_entry = self.create_file_selector(
            self, "Reference:", os.environ.get("WGSE_REF", "")
        )

        ctk.CTkLabel(
            self,
            text="Select Target Formats:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))

        # Format Selection Grid
        ff = ctk.CTkFrame(self)
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

        # Selection Utility Buttons
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(
            sf, text="Select All", width=100, command=self.micro_select_all
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            sf, text="Unselect All", width=100, command=self.micro_unselect_all
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            sf,
            text="Select Recommended",
            width=150,
            command=self.micro_select_recommended,
        ).pack(side="left", padx=5)

        # Action Button
        btn = ctk.CTkButton(
            self,
            text="Generate CombinedKit",
            command=lambda: self.main_app.run_dispatch("microarray", self),
        )
        btn.pack(pady=20)

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
