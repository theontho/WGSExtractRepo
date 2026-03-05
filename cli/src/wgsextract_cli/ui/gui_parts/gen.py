import os
import customtkinter as ctk
from .common import BaseFrame, ToolTip

class GenericFrame(BaseFrame):
    def setup_ui(self):
        super().setup_ui()
        key = self.key
        meta = self.meta
        
        if key in ["gen", "bam", "ext", "anc", "qc", "vcf"]:
            self.input_entry = self.create_file_selector(
                self, "Input:", os.environ.get("WGSE_INPUT", "")
            )
        
        if key in ["gen", "bam", "vcf"]:
            self.ref_entry = self.create_file_selector(
                self, "Reference:", os.environ.get("WGSE_REF", "")
            )
            
        if key == "gen":
            self.region_entry = self.create_entry(self, "Region (e.g. chrM):")
            self.align_r1 = self.create_file_selector(self, "FASTQ R1 (for Align):")
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

        grid_f = ctk.CTkFrame(self, fg_color="transparent")
        grid_f.pack(fill="x", padx=20, pady=10)
        for i, cmd_m in enumerate(meta["commands"]):
            r, c = divmod(i, 3)
            grid_f.grid_columnconfigure(c, weight=1)
            btn = ctk.CTkButton(
                grid_f,
                text=cmd_m["label"],
                command=lambda cc=cmd_m["cmd"]: self.main_app.run_dispatch(cc, self),
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cmd_m["help"])
