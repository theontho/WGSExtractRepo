import os
import customtkinter as ctk
from .common import BaseFrame
from wgsextract_cli.ui.constants import MICROARRAY_FORMATS

class MicroFrame(BaseFrame):
    def setup_ui(self):
        super().setup_ui()
        key = self.key
        meta = self.meta
        
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
        
        ff = ctk.CTkFrame(self)
        ff.pack(fill="x", padx=20, pady=5)
        
        vds = {}
        for f in MICROARRAY_FORMATS:
            vds.setdefault(f["vendor"], []).append(f)
            
        self.micro_formats_vars = {}
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
        
        btn = ctk.CTkButton(
            self,
            text="Generate CombinedKit",
            command=lambda: self.main_app.run_dispatch("microarray", self),
        )
        btn.pack(pady=20)

    def micro_select_all(self):
        for v in self.micro_formats_vars.values():
            v.set(True)

    def micro_unselect_all(self):
        for v in self.micro_formats_vars.values():
            v.set(False)

    def micro_select_recommended(self):
        ids = [f["id"] for f in MICROARRAY_FORMATS if f.get("recommended")]
        for fid, v in self.micro_formats_vars.items():
            v.set(fid in ids)
