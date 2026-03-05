import os
import subprocess
import sys
import threading
import tkinter as tk

import customtkinter as ctk

from wgsextract_cli.ui.constants import UI_METADATA
from wgsextract_cli.ui.gui_parts.gen import GenericFrame
from wgsextract_cli.ui.gui_parts.lib import LibFrame
from wgsextract_cli.ui.gui_parts.micro import MicroFrame

class WGSExtractGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WGS Extract GUI")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.active_downloads = {}
        self.vep_cancel_event = None
        
        self.sidebar_frame = ctk.CTkFrame(self, width=160, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            self.sidebar_frame,
            text="WGS Extract",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        for i, (key, meta) in enumerate(UI_METADATA.items()):
            ctk.CTkButton(
                self.sidebar_frame,
                text=meta["title"],
                command=lambda k=key: self.show_frame(k),
            ).grid(row=i + 1, column=0, padx=20, pady=10)
            
        self.main_content = ctk.CTkFrame(self)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)
        
        self.output_text = ctk.CTkTextbox(self, height=200)
        self.output_text.grid(row=1, column=1, sticky="nsew", padx=20, pady=(0, 20))
        
        self.frames = {}
        for key, meta in UI_METADATA.items():
            if key == "lib":
                frame = LibFrame(self.main_content, self, key, meta)
            elif key == "micro":
                frame = MicroFrame(self.main_content, self, key, meta)
            else:
                frame = GenericFrame(self.main_content, self, key, meta)
            self.frames[key] = frame
            
        self.show_frame("gen")
        self.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<Button-4>", self._on_mousewheel)
        self.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        w = event.widget
        delta = event.num == 4 and 1 or event.num == 5 and -1 or event.delta
        curr = w
        while curr:
            if isinstance(curr, (tk.Canvas, tk.Text, ctk.CTkTextbox)):
                if isinstance(curr, tk.Canvas):
                    curr.yview_scroll(
                        int(-1 * (delta / 120))
                        if event.num not in [4, 5]
                        else -1 * delta,
                        "units",
                    )
                else:
                    curr.yview(
                        tk.SCROLL,
                        int(-1 * (delta / 120))
                        if event.num not in [4, 5]
                        else -1 * delta,
                        tk.UNITS,
                    )
                break
            try:
                curr = curr.master
            except:
                break

    def show_frame(self, n):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[n].pack(fill="both", expand=True)

    def log(self, m):
        self.output_text.insert("end", m + "\n")
        self.output_text.see("end")

    def run_cmd(self, c):
        self.log(f"Running: {' '.join(c)}")

        def run():
            p = subprocess.Popen(
                c,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for line in p.stdout:
                self.after(0, lambda l=line: self.log(l.strip()))
            p.wait()
            self.after(0, lambda: self.log(f"Finished (Exit {p.returncode})"))

        threading.Thread(target=run, daemon=True).start()

    def run_vep_download(self, lib_frame):
        lib_frame.show_vep_progress()
        self.vep_cancel_event = threading.Event()

        def cb(d, t, s):
            pct = d / t if t > 0 else 0
            st = (
                f"{s / (1024 * 1024):.1f} MB/s"
                if s > 1024 * 1024
                else f"{s / 1024:.1f} KB/s"
            )
            self.after(0, lambda: lib_frame.vep_prog_var.set(pct))
            self.after(0, lambda: lib_frame.vep_stat_var.set(f"{pct * 100:.1f}% - {st}"))

        def run():
            from wgsextract_cli.commands.vep import cmd_vep_download

            class Args:
                pass

            a = Args()
            a.vep_version = "115"
            a.species = "homo_sapiens"
            a.assembly = "GRCh38"
            a.mirror = "uk"
            a.vep_cache = lib_frame.vep_cache.get()
            a.ref = lib_frame.ref_entry.get()
            a.progress_callback = cb
            a.cancel_event = self.vep_cancel_event
            self.log("Starting VEP cache download...")
            try:
                success = cmd_vep_download(a)
                self.after(
                    0,
                    lambda: self.log(
                        f"VEP Download {'Succeeded' if success else 'Failed/Cancelled'}"
                    ),
                )
            except Exception as e:
                self.after(0, lambda: self.log(f"Error: {e}"))
            finally:
                self.after(0, lib_frame.hide_vep_progress)
                self.vep_cancel_event = None

        threading.Thread(target=run, daemon=True).start()

    def cancel_vep_download(self):
        if self.vep_cancel_event:
            self.vep_cancel_event.set()
            self.log("Cancelling VEP download...")

    def run_lib_download(self, gd, lib_frame, restart=False):
        dest = lib_frame.lib_dest.get()
        fn = gd["final"]
        if fn in self.active_downloads:
            return
        self.log(f"Starting {'restart' if restart else 'download'}: {gd['label']}...")
        ce = threading.Event()
        pv = ctk.DoubleVar(value=0)
        sv = ctk.StringVar(value="Waiting...")
        self.active_downloads[fn] = {
            "cancel_event": ce,
            "progress_var": pv,
            "status_var": sv,
        }
        lib_frame.setup_ui()

        def cb(d, t, s):
            pct = d / t if t > 0 else 0
            st = (
                f"{s / (1024 * 1024):.1f} MB/s"
                if s > 1024 * 1024
                else f"{s / 1024:.1f} KB/s"
            )
            self.after(0, lambda: pv.set(pct))
            self.after(0, lambda: sv.set(f"{pct * 100:.1f}% - {st}"))

        def run():
            from wgsextract_cli.core.ref_library import download_and_process_genome

            try:
                success = download_and_process_genome(
                    gd,
                    dest,
                    interactive=False,
                    progress_callback=cb,
                    cancel_event=ce,
                    restart=restart,
                )
                self.after(
                    0,
                    lambda: self.log(
                        f"Download {'Succeeded' if success else 'Failed'}: {gd['label']}"
                    ),
                )
            except Exception as e:
                self.after(0, lambda: self.log(f"Error: {str(e)}"))
            finally:
                if fn in self.active_downloads:
                    del self.active_downloads[fn]
                self.after(0, lib_frame.setup_ui)

        threading.Thread(target=run, daemon=True).start()

    def run_lib_delete(self, group, lib_frame):
        dest = lib_frame.lib_dest.get()
        from wgsextract_cli.core.ref_library import delete_genome

        if delete_genome(group["final"], dest):
            self.log(f"Deleted {group['final']}")
            lib_frame.setup_ui()

    def cancel_lib_download(self, fn):
        if fn in self.active_downloads:
            self.active_downloads[fn]["cancel_event"].set()
            self.log(f"Cancelling {fn}...")

    def run_dispatch(self, cmd, frame):
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        
        if cmd == "vep-download":
            self.run_vep_download(frame)
            return

        # Common input/ref mappings
        input_path = getattr(frame, "input_entry", None)
        if input_path:
            input_path = input_path.get()
        ref_path = getattr(frame, "ref_entry", None)
        if ref_path:
            ref_path = ref_path.get()

        if cmd == "info":
            self.run_cmd(
                bc
                + [
                    "info",
                    "--input",
                    input_path,
                    "--ref",
                    ref_path,
                    "--detailed",
                ]
            )
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = bc + ["info", cmd, "--input", input_path]
            region = getattr(frame, "region_entry", None)
            if region and region.get():
                c.extend(["-r", region.get()])
            self.run_cmd(c)
        elif cmd == "align":
            self.run_cmd(
                bc
                + ["align", "--input", frame.align_r1.get(), "--ref", ref_path]
            )
        elif cmd in [
            "sort",
            "index",
            "unindex",
            "unsort",
            "to-cram",
            "to-bam",
            "unalign",
            "subset",
            "mt-extract",
        ]:
            c = bc + ["bam", cmd, "--input", input_path]
            if ref_path:
                c.extend(["--ref", ref_path])
            extra = getattr(frame, "extra_entry", None)
            if cmd == "subset" and extra and extra.get():
                c.append(extra.get())
            self.run_cmd(c)
        elif cmd.startswith("repair-"):
            self.run_cmd(
                bc
                + ["repair", cmd.replace("repair-", ""), "--input", input_path]
            )
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c = bc + ["extract"]
            region = getattr(frame, "region_entry", None)
            if cmd == "custom" and region:
                c.extend(["--input", input_path, "-r", region.get()])
            else:
                c.extend([cmd, "--input", input_path])
            out_dir = getattr(frame, "out_dir", None)
            if out_dir and out_dir.get():
                c.extend(["--outdir", out_dir.get()])
            self.run_cmd(c)
        elif cmd in [
            "snp",
            "indel",
            "sv",
            "cnv",
            "freebayes",
            "gatk",
            "deepvariant",
            "annotate",
            "filter",
            "trio",
            "vcf-qc",
            "vep-run",
            "vep-verify",
        ]:
            sub = (
                "qc"
                if cmd == "vcf-qc"
                else cmd.replace("vep-", "")
                if "vep-" in cmd
                else cmd
            )
            c = bc + ["vep" if "vep-" in cmd else "vcf", sub]
            if sub == "trio":
                c += [
                    "--proband",
                    input_path,
                    "--mother",
                    frame.vcf_e1.get(),
                    "--father",
                    frame.vcf_e2.get(),
                ]
            elif sub == "run":
                c += ["--input", input_path, "--ref", ref_path]
            elif sub == "verify":
                pass
            else:
                c += ["--input", input_path]
                
            if cmd == "vep-verify" and ref_path:
                c += ["--ref", ref_path]
            elif ref_path:
                c += ["--ref", ref_path]
                
            if sub == "annotate" and frame.vcf_e1.get():
                c += ["--ann-vcf", frame.vcf_e1.get()]
            if sub == "filter":
                if frame.vcf_e2.get():
                    c.extend(["--expr", frame.vcf_e2.get()])
                if frame.vcf_e3.get():
                    c.extend(["--gene", frame.vcf_e3.get()])
            if (
                sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"]
                and frame.vcf_e3.get()
            ):
                c += ["-r", frame.vcf_e3.get()]
            if "vep" in cmd:
                cv = frame.vep_cache.get() if hasattr(frame, "vep_cache") else getattr(frame, "vcf_vep_cache", None).get()
                if cv:
                    c += ["--vep-cache", cv]
                if sub == "run" and frame.vcf_vep_args.get():
                    c += ["--vep-args", frame.vcf_vep_args.get()]
            self.run_cmd(c)
        elif cmd == "microarray":
            sel = [fid for fid, v in frame.micro_formats_vars.items() if v.get()]
            if not sel:
                self.log("Error: No formats selected.")
                return
            self.run_cmd(
                bc
                + [
                    "microarray",
                    "--input",
                    input_path,
                    "--ref",
                    ref_path,
                    "--formats",
                    ",".join(sel),
                ]
            )
        elif cmd == "lineage-y":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "y-dna",
                    "--input",
                    input_path,
                    "--yleaf-path",
                    frame.yleaf_path.get(),
                    "--pos-file",
                    frame.yleaf_pos.get(),
                ]
            )
        elif cmd == "lineage-mt":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "mt-dna",
                    "--input",
                    input_path,
                    "--haplogrep-path",
                    frame.haplogrep_path.get(),
                ]
            )
        elif cmd in ["fastqc", "fastp"]:
            self.run_cmd(bc + ["qc", cmd, "--input", input_path])
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = bc + ["ref", sub]
            if sub == "identify":
                c += ["--input", input_path]
            if sub not in ["download", "download-genes"] and ref_path:
                c += ["--ref", ref_path]
            self.run_cmd(c)

def main():
    WGSExtractGUI().mainloop()

if __name__ == "__main__":
    main()
