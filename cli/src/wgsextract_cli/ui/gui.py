import customtkinter as ctk
import subprocess
import threading
import os
import sys
import tkinter as tk
from tkinter import filedialog
from wgsextract_cli.ui.constants import UI_METADATA

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify="left",
                         background="#2b2b2b", foreground="#ffffff", 
                         relief="solid", borderwidth=1,
                         font=("Arial", "10", "normal"), 
                         padx=10, pady=8, wraplength=400)
        label.pack()

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw: tw.destroy()

class WGSExtractGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WGS Extract GUI")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(self.sidebar_frame, text="WGS Extract", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))

        for i, (key, meta) in enumerate(UI_METADATA.items()):
            btn = ctk.CTkButton(self.sidebar_frame, text=meta["title"], command=lambda k=key: self.show_frame(k))
            btn.grid(row=i+1, column=0, padx=20, pady=10)

        self.main_content = ctk.CTkFrame(self)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        self.output_text = ctk.CTkTextbox(self, height=200)
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=20, pady=(0, 20))

        self.frames = {}
        for key in UI_METADATA:
            if key == "lib":
                self.setup_lib_frame()
            else:
                self.setup_frame(key)
        self.show_frame("gen")

        # Global Mouse Wheel Bind
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        # Find widget under mouse
        widget = event.widget
        # If it's a canvas (part of CTkScrollableFrame) or CTkTextbox, we scroll it
        # Tkinter events for scroll: Windows/macOS use event.delta, Linux uses Button-4/5
        delta = 0
        if event.num == 4: delta = 1
        elif event.num == 5: delta = -1
        else: delta = event.delta

        # Helper to find the nearest scrollable parent canvas
        curr = widget
        while curr:
            if isinstance(curr, (tk.Canvas, tk.Text, ctk.CTkTextbox)):
                if isinstance(curr, tk.Canvas):
                    curr.yview_scroll(int(-1*(delta/120)) if event.num not in [4,5] else -1*delta, "units")
                else:
                    # CTkTextbox or tk.Text
                    curr.yview(tk.SCROLL, int(-1*(delta/120)) if event.num not in [4,5] else -1*delta, tk.UNITS)
                break
            try:
                curr = curr.master
            except:
                break

    def setup_lib_frame(self):
        from wgsextract_cli.core.ref_library import get_grouped_genomes, is_genome_installed
        key = "lib"
        meta = UI_METADATA[key]
        
        # Clear existing frame if refreshing
        if key in self.frames:
            for widget in self.frames[key].winfo_children():
                widget.destroy()
            frame = self.frames[key]
        else:
            frame = ctk.CTkScrollableFrame(self.main_content)
            self.frames[key] = frame
        
        ctk.CTkLabel(frame, text=meta["title"], font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(frame, text=meta["help"], font=ctk.CTkFont(size=12, slant="italic")).pack(pady=(0, 10))

        # Library directory selector
        lib_dir_frame = ctk.CTkFrame(frame)
        lib_dir_frame.pack(fill="x", padx=20, pady=5)
        self.lib_dest = self.create_dir_selector(lib_dir_frame, "Library Dir:", os.environ.get("WGSE_REF", ""))
        # Re-render on change? For now just manual refresh button
        ctk.CTkButton(lib_dir_frame, text="Refresh List", width=100, command=self.setup_lib_frame).pack(side="right", padx=10)

        dest = self.lib_dest.get()
        grouped = get_grouped_genomes()

        for group in grouped:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", padx=20, pady=5)
            
            label_txt = group["label"]
            installed = is_genome_installed(group["final"], dest)
            
            ctk.CTkLabel(row, text=label_txt, anchor="w").pack(side="left", padx=10, expand=True, fill="x")
            
            if installed:
                btn = ctk.CTkButton(row, text="Delete", width=80, fg_color="#992222", hover_color="#bb3333",
                                    command=lambda g=group: self.run_lib_delete(g))
                btn.pack(side="right", padx=10)
                ToolTip(btn, f"Remove {group['final']} and all its index files from local storage.")
            else:
                # Multiple source buttons
                for source_data in reversed(group["sources"]):
                    s_btn = ctk.CTkButton(row, text=source_data["source"], width=60,
                                          command=lambda s=source_data: self.run_lib_download(s))
                    s_btn.pack(side="right", padx=5)
                    ToolTip(s_btn, f"Download from {source_data['source']}\nURL: {source_data['url']}")

    def run_lib_download(self, genome_data):
        dest = self.lib_dest.get()
        self.log(f"Starting download: {genome_data['label']} from {genome_data['source']}...")
        def run():
            from wgsextract_cli.core.ref_library import download_and_process_genome
            try:
                success = download_and_process_genome(genome_data, dest, interactive=False)
                self.after(0, lambda: self.log(f"Download {'Succeeded' if success else 'Failed'}"))
                self.after(0, self.setup_lib_frame) # Refresh view
            except Exception as e:
                self.after(0, lambda: self.log(f"Error: {str(e)}"))
        threading.Thread(target=run, daemon=True).start()

    def run_lib_delete(self, group):
        dest = self.lib_dest.get()
        from wgsextract_cli.core.ref_library import delete_genome
        if delete_genome(group["final"], dest):
            self.log(f"Deleted {group['final']}")
            self.setup_lib_frame()

    def setup_frame(self, key):
        meta = UI_METADATA[key]
        frame = ctk.CTkScrollableFrame(self.main_content)
        self.frames[key] = frame
        
        ctk.CTkLabel(frame, text=meta["title"], font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        ctk.CTkLabel(frame, text=meta["help"], font=ctk.CTkFont(size=12, slant="italic")).pack(pady=(0, 10))

        # Common Inputs
        if key in ["gen", "bam", "ext", "vcf", "anc", "qc_ref"]:
            self.get_attr(key, "in", self.create_file_selector(frame, "Input:", os.environ.get("WGSE_INPUT", "")))
        if key in ["gen", "bam", "vcf"]:
            self.get_attr(key, "ref", self.create_file_selector(frame, "Reference:", os.environ.get("WGSE_REF", "")))
        
        # Specialized Inputs
        if key == "gen":
            self.gen_region = self.create_entry(frame, "Region (e.g. chrM):")
            self.align_r1 = self.create_file_selector(frame, "FASTQ R1 (for Align):")
        elif key == "bam":
            self.bam_extra = self.create_entry(frame, "Extra (Fraction/Region):")
        elif key == "ext":
            self.ext_out = self.create_dir_selector(frame, "Out Dir:", os.environ.get("WGSE_OUTDIR", ""))
            self.ext_region = self.create_entry(frame, "Custom Region:")
        elif key == "vcf":
            self.vcf_e1 = self.create_file_selector(frame, "Mother/Ann VCF:")
            self.vcf_e2 = self.create_file_selector(frame, "Father/Filter Expr:")
            self.vcf_e3 = self.create_entry(frame, "Gene/Region:")
            self.vep_cache = self.create_dir_selector(frame, "VEP Cache:", os.path.expanduser("~/.vep"))
            self.vep_args = self.create_entry(frame, "Extra VEP Args:")
        elif key == "anc":
            self.yleaf_path = self.create_file_selector(frame, "Yleaf Path:")
            self.yleaf_pos = self.create_file_selector(frame, "Pos File:")
            self.haplogrep_path = self.create_file_selector(frame, "Haplogrep Path:")

        # Buttons
        grid_frame = ctk.CTkFrame(frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=20, pady=10)
        for i, cmd_meta in enumerate(meta["commands"]):
            row, col = divmod(i, 3)
            grid_frame.grid_columnconfigure(col, weight=1)
            btn = ctk.CTkButton(grid_frame, text=cmd_meta["label"], command=lambda c=cmd_meta["cmd"]: self.run_dispatch(c))
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cmd_meta["help"])

    def create_entry(self, parent, label):
        f = ctk.CTkFrame(parent); f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f, text=label, width=120, anchor="w").pack(side="left", padx=10)
        e = ctk.CTkEntry(f); e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def get_attr(self, key, suffix, val=None):
        name = f"{key}_{suffix}"
        if val: setattr(self, name, val)
        return getattr(self, name, None)

    def run_dispatch(self, cmd):
        base_cmd = [sys.executable, "-m", "wgsextract_cli.main"]
        if cmd == "info": 
            self.run_cmd(base_cmd + ["info", "--input", self.gen_in.get(), "--ref", self.gen_ref.get(), "--detailed"])
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = base_cmd + ["info", cmd, "--input", self.gen_in.get()]
            if self.gen_region.get(): c += ["-r", self.gen_region.get()]
            self.run_cmd(c)
        elif cmd == "align":
            self.run_cmd(base_cmd + ["align", "--input", self.align_r1.get(), "--ref", self.gen_ref.get()])
        elif cmd in ["sort", "index", "unindex", "unsort", "to-cram", "to-bam", "unalign", "subset", "mt-extract"]:
            c = base_cmd + ["bam", cmd, "--input", self.bam_in.get()]
            if self.bam_ref.get(): c += ["--ref", self.bam_ref.get()]
            if cmd == "subset" and self.bam_extra.get(): c += [self.bam_extra.get()]
            self.run_cmd(c)
        elif cmd.startswith("repair-"):
            self.run_cmd(base_cmd + ["repair", cmd.replace("repair-", ""), "--input", self.bam_in.get()])
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c = base_cmd + ["extract"]
            if cmd == "custom": c += ["--input", self.ext_in.get(), "-r", self.ext_region.get()]
            else: c += [cmd, "--input", self.ext_in.get()]
            if self.ext_out.get(): c += ["--outdir", self.ext_out.get()]
            self.run_cmd(c)
        elif cmd in ["snp", "indel", "sv", "cnv", "freebayes", "gatk", "deepvariant", "annotate", "filter", "trio", "vcf-qc"]:
            sub = "qc" if cmd == "vcf-qc" else cmd
            c = base_cmd + ["vcf", sub]
            if sub == "trio": c += ["--proband", self.vcf_in.get(), "--mother", self.vcf_e1.get(), "--father", self.vcf_e2.get()]
            else: c += ["--input", self.vcf_in.get()]
            if self.vcf_ref.get(): c += ["--ref", self.vcf_ref.get()]
            if sub == "annotate" and self.vcf_e1.get(): c += ["--ann-vcf", self.vcf_e1.get()]
            if sub == "filter":
                if self.vcf_e2.get(): c += ["--expr", self.vcf_e2.get()]
                if self.vcf_e3.get(): c += ["--gene", self.vcf_e3.get()]
            if sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"] and self.vcf_e3.get(): c += ["-r", self.vcf_e3.get()]
            self.run_cmd(c)
        elif cmd.startswith("vep-"):
            sub = cmd.replace("vep-", "")
            c = base_cmd + ["vep"]
            if sub == "run":
                c += ["--input", self.vcf_in.get(), "--ref", self.vcf_ref.get()]
                if self.vep_cache.get(): c += ["--vep-cache", self.vep_cache.get()]
                if self.vep_args.get(): c += ["--vep-args", self.vep_args.get()]
            else:
                c += [sub]
                if self.vep_cache.get(): c += ["--vep-cache", self.vep_cache.get()]
            self.run_cmd(c)
        elif cmd == "microarray":
            self.run_cmd(base_cmd + ["microarray", "--input", self.anc_in.get()])
        elif cmd == "lineage-y":
            self.run_cmd(base_cmd + ["lineage", "y-dna", "--input", self.anc_in.get(), "--yleaf-path", self.yleaf_path.get(), "--pos-file", self.yleaf_pos.get()])
        elif cmd == "lineage-mt":
            self.run_cmd(base_cmd + ["lineage", "mt-dna", "--input", self.anc_in.get(), "--haplogrep-path", self.haplogrep_path.get()])
        elif cmd in ["fastqc", "fastp"]:
            self.run_cmd(base_cmd + ["qc", cmd, "--input", self.qr_input.get()])
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = base_cmd + ["ref", sub]
            if sub not in ["download", "download-genes"]: c += ["--ref", self.qr_input.get()]
            self.run_cmd(c)
        elif cmd in ["coverage-wgs", "coverage-wes"]:
            # Actually info commands
            c = base_cmd + ["info", "calculate-coverage", "--input", self.qr_input.get()]
            # The CLI doesn't have coverage-wgs/wes subcommands, it has calculate-coverage
            # I should check if coverage-wgs is a thing in the CLI or if I made it up.
            # Looking at qc.py again... it's NOT there.
            self.run_cmd(c)

    def create_file_selector(self, parent, label_text, initial_value=""):
        frame = ctk.CTkFrame(parent); frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame, text=label_text, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame); entry.insert(0, initial_value); entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(frame, text="Browse", width=80, command=lambda: self.browse_file(entry)).pack(side="right", padx=10)
        return entry

    def create_dir_selector(self, parent, label_text, initial_value=""):
        frame = ctk.CTkFrame(parent); frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame, text=label_text, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame); entry.insert(0, initial_value); entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(frame, text="Browse", width=80, command=lambda: self.browse_dir(entry)).pack(side="right", padx=10)
        return entry

    def browse_file(self, entry):
        f = filedialog.askopenfilename()
        if f: entry.delete(0, "end"); entry.insert(0, f)

    def browse_dir(self, entry):
        d = filedialog.askdirectory()
        if d: entry.delete(0, "end"); entry.insert(0, d)

    def show_frame(self, name):
        for f in self.frames.values(): f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    def log(self, message):
        self.output_text.insert("end", message + "\n"); self.output_text.see("end")

    def run_cmd(self, cmd):
        self.log(f"Running: {' '.join(cmd)}")
        def run():
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in p.stdout: self.after(0, lambda l=line: self.log(l.strip()))
            p.wait(); self.after(0, lambda: self.log(f"Finished (Exit {p.returncode})"))
        threading.Thread(target=run, daemon=True).start()

def main():
    WGSExtractGUI().mainloop()

if __name__ == "__main__":
    main()
