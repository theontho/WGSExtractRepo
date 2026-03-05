import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from wgsextract_cli.ui.constants import MICROARRAY_FORMATS, UI_METADATA


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
        x, y = (
            self.widget.winfo_rootx() + 20,
            self.widget.winfo_rooty() + self.widget.winfo_height() + 5,
        )
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2b2b2b",
            foreground="#ffffff",
            relief="solid",
            borderwidth=1,
            font=("Arial", "10", "normal"),
            padx=10,
            pady=8,
            wraplength=400,
        ).pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class WGSExtractGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WGS Extract GUI")
        self.geometry("1100x850")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.active_downloads = {}
        self.micro_formats_vars = {}
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
        for key in UI_METADATA:
            if key == "lib":
                self.setup_lib_frame()
            elif key == "micro":
                self.setup_microarray_frame()
            else:
                self.setup_frame(key)
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

    def setup_lib_frame(self):
        from wgsextract_cli.core.ref_library import (
            get_genome_size,
            get_genome_status,
            get_grouped_genomes,
        )

        key = "lib"
        meta = UI_METADATA[key]
        if key in self.frames:
            for widget in self.frames[key].winfo_children():
                widget.destroy()
            frame = self.frames[key]
        else:
            frame = ctk.CTkScrollableFrame(self.main_content)
            self.frames[key] = frame
        ctk.CTkLabel(
            frame, text=meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            frame, text=meta["help"], font=ctk.CTkFont(size=12, slant="italic")
        ).pack(pady=(0, 10))
        ldf = ctk.CTkFrame(frame)
        ldf.pack(fill="x", padx=20, pady=5)
        self.lib_dest = self.create_dir_selector(
            ldf, "Library Dir:", os.environ.get("WGSE_REF", "")
        )
        ctk.CTkButton(
            ldf, text="Refresh List", width=100, command=self.setup_lib_frame
        ).pack(side="right", padx=10)
        self.get_attr(
            key,
            "in",
            self.create_file_selector(
                frame, "Input:", os.environ.get("WGSE_INPUT", "")
            ),
        )
        ref_val = os.environ.get("WGSE_REF", "")
        self.get_attr(
            key, "ref", self.create_file_selector(frame, "Reference:", ref_val)
        )

        # 1. Reference Management Section
        if meta["commands"]:
            bf = ctk.CTkFrame(frame, fg_color="transparent")
            bf.pack(fill="x", padx=20, pady=(20, 10))
            ctk.CTkLabel(
                bf,
                text="Reference Management",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(pady=(0, 5))
            gf = ctk.CTkFrame(frame, fg_color="transparent")
            gf.pack(fill="x", padx=20)
            for i, cm in enumerate(meta["commands"]):
                r, c = divmod(i, 3)
                gf.grid_columnconfigure(c, weight=1)
                btn = ctk.CTkButton(
                    gf,
                    text=cm["label"],
                    command=lambda cc=cm["cmd"]: self.run_dispatch(cc),
                )
                btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
                ToolTip(btn, cm["help"])

        # 2. VEP Management Section
        vep_f = ctk.CTkFrame(frame, fg_color="transparent")
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
            "VEP (Variant Effect Predictor) uses a large cache of genomic data to determine how variants (SNPs/InDels) might affect genes and proteins. This cache can be several GBs and is stored in your library.",
        )

        dv = (
            os.path.join(ref_val, "vep")
            if ref_val and os.path.isdir(ref_val)
            else os.path.expanduser("~/.vep")
        )
        self.vep_cache = self.create_dir_selector(frame, "VEP Cache Path:", dv)

        vep_btn_f = ctk.CTkFrame(frame, fg_color="transparent")
        vep_btn_f.pack(fill="x", padx=20)
        for i, cm in enumerate(meta["vep_commands"]):
            vep_btn_f.grid_columnconfigure(i, weight=1)
            btn = ctk.CTkButton(
                vep_btn_f,
                text=cm["label"],
                command=lambda cc=cm["cmd"]: self.run_dispatch(cc),
            )
            btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cm["help"])

        # VEP Progress UI
        self.vep_prog_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.vep_prog_frame.pack(fill="x", padx=20, pady=5)
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
            command=self.cancel_vep_download,
        )

        # 3. Reference Genome List
        hf = ctk.CTkFrame(frame, fg_color="transparent")
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
        ToolTip(
            ii,
            "Reference genomes are the 'master' DNA sequences used as a baseline for comparison during alignment and variant calling.",
        )

        dest = self.lib_dest.get()
        grouped = get_grouped_genomes()
        for group in grouped:
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", padx=20, pady=5)
            fn = group["final"]
            lt = group["label"]
            s = get_genome_status(fn, dest)
            sz = get_genome_size(fn, dest)
            sl = f" ({sz})" if sz else ""
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
            if fn in self.active_downloads:
                di = self.active_downloads[fn]
                dc = ctk.CTkFrame(row, fg_color="transparent")
                dc.pack(side="right", padx=10)
                ctk.CTkProgressBar(dc, variable=di["progress_var"], width=150).pack(
                    side="left", padx=5
                )
                ctk.CTkLabel(
                    dc, textvariable=di["status_var"], font=ctk.CTkFont(size=10)
                ).pack(side="left", padx=5)
                ctk.CTkButton(
                    dc,
                    text="Cancel",
                    width=60,
                    fg_color="#666666",
                    hover_color="#888888",
                    command=lambda f=fn: self.cancel_lib_download(f),
                ).pack(side="left", padx=5)
            elif s == "installed":
                btn = ctk.CTkButton(
                    row,
                    text="Delete",
                    width=80,
                    fg_color="#992222",
                    hover_color="#bb3333",
                    command=lambda g=group: self.run_lib_delete(g),
                )
                btn.pack(side="right", padx=10)
                ToolTip(btn, f"Remove {fn} and index files.")
            elif s == "incomplete":
                ctk.CTkButton(
                    row,
                    text="Delete",
                    width=70,
                    fg_color="#992222",
                    hover_color="#bb3333",
                    command=lambda g=group: self.run_lib_delete(g),
                ).pack(side="right", padx=10)
                ctk.CTkButton(
                    row,
                    text="Restart",
                    width=70,
                    fg_color="#aa6622",
                    hover_color="#cc8844",
                    command=lambda g=group: self.run_lib_download(
                        g["sources"][0], restart=True
                    ),
                ).pack(side="right", padx=5)
                ctk.CTkButton(
                    row,
                    text="Resume",
                    width=70,
                    fg_color="#228822",
                    hover_color="#33aa33",
                    command=lambda g=group: self.run_lib_download(g["sources"][0]),
                ).pack(side="right", padx=5)
                ctk.CTkLabel(
                    row,
                    text="Incomplete",
                    text_color="#ffaa00",
                    font=ctk.CTkFont(size=11, weight="bold"),
                ).pack(side="right", padx=10)
            else:
                for sd in reversed(group["sources"]):
                    sb = ctk.CTkButton(
                        row,
                        text=sd["source"],
                        width=60,
                        command=lambda s=sd: self.run_lib_download(s),
                    )
                    sb.pack(side="right", padx=5)
                    ToolTip(sb, f"Download from {sd['source']}")
                ctk.CTkLabel(
                    row, text="download from", font=ctk.CTkFont(size=11, slant="italic")
                ).pack(side="right", padx=5)

    def run_vep_download(self):
        self.vep_pbar.pack(side="left", padx=5)
        self.vep_stat_lbl.pack(side="left", padx=5)
        self.vep_cancel_btn.pack(side="left", padx=5)
        self.vep_cancel_event = threading.Event()

        def cb(d, t, s):
            pct = d / t if t > 0 else 0
            st = (
                f"{s / (1024 * 1024):.1f} MB/s"
                if s > 1024 * 1024
                else f"{s / 1024:.1f} KB/s"
            )
            self.after(0, lambda: self.vep_prog_var.set(pct))
            self.after(0, lambda: self.vep_stat_var.set(f"{pct * 100:.1f}% - {st}"))

        def run():
            from wgsextract_cli.commands.vep import cmd_vep_download

            class Args:
                pass

            a = Args()
            a.vep_version = "115"
            a.species = "homo_sapiens"
            a.assembly = "GRCh38"
            a.mirror = "uk"
            a.vep_cache = self.vep_cache.get()
            a.ref = self.lib_ref.get()
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
                self.after(
                    0,
                    lambda: (
                        self.vep_pbar.pack_forget(),
                        self.vep_stat_lbl.pack_forget(),
                        self.vep_cancel_btn.pack_forget(),
                    ),
                )
                self.vep_cancel_event = None

        threading.Thread(target=run, daemon=True).start()

    def cancel_vep_download(self):
        if self.vep_cancel_event:
            self.vep_cancel_event.set()
            self.log("Cancelling VEP download...")

    def setup_microarray_frame(self):
        key = "micro"
        meta = UI_METADATA[key]
        frame = ctk.CTkScrollableFrame(self.main_content)
        self.frames[key] = frame
        ctk.CTkLabel(
            frame, text=meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            frame, text=meta["help"], font=ctk.CTkFont(size=12, slant="italic")
        ).pack(pady=(0, 10))
        self.get_attr(
            key,
            "in",
            self.create_file_selector(
                frame, "Input:", os.environ.get("WGSE_INPUT", "")
            ),
        )
        self.get_attr(
            key,
            "ref",
            self.create_file_selector(
                frame, "Reference:", os.environ.get("WGSE_REF", "")
            ),
        )
        ctk.CTkLabel(
            frame,
            text="Select Target Formats:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(10, 5))
        ff = ctk.CTkFrame(frame)
        ff.pack(fill="x", padx=20, pady=5)
        vds = {}
        for f in MICROARRAY_FORMATS:
            (vds.setdefault(f["vendor"], [])).append(f)
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
        sf = ctk.CTkFrame(frame, fg_color="transparent")
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
            frame,
            text="Generate CombinedKit",
            command=lambda: self.run_dispatch("microarray"),
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

    def run_lib_download(self, gd, restart=False):
        dest = self.lib_dest.get()
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
        self.setup_lib_frame()

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
                self.after(0, self.setup_lib_frame)

        threading.Thread(target=run, daemon=True).start()

    def run_lib_delete(self, group):
        dest = self.lib_dest.get()
        from wgsextract_cli.core.ref_library import delete_genome

        if delete_genome(group["final"], dest):
            self.log(f"Deleted {group['final']}")
            self.setup_lib_frame()

    def cancel_lib_download(self, fn):
        if fn in self.active_downloads:
            self.active_downloads[fn]["cancel_event"].set()
            self.log(f"Cancelling {fn}...")

    def setup_frame(self, key):
        meta = UI_METADATA[key]
        frame = ctk.CTkScrollableFrame(self.main_content)
        self.frames[key] = frame
        ctk.CTkLabel(
            frame, text=meta["title"], font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            frame, text=meta["help"], font=ctk.CTkFont(size=12, slant="italic")
        ).pack(pady=(0, 10))
        if key in ["gen", "bam", "ext", "anc", "qc", "vcf"]:
            self.get_attr(
                key,
                "in",
                self.create_file_selector(
                    frame, "Input:", os.environ.get("WGSE_INPUT", "")
                ),
            )
        if key in ["gen", "bam", "vcf"]:
            self.get_attr(
                key,
                "ref",
                self.create_file_selector(
                    frame, "Reference:", os.environ.get("WGSE_REF", "")
                ),
            )
        if key == "gen":
            self.gen_region = self.create_entry(frame, "Region (e.g. chrM):")
            self.align_r1 = self.create_file_selector(frame, "FASTQ R1 (for Align):")
        elif key == "bam":
            self.bam_extra = self.create_entry(frame, "Extra (Fraction/Region):")
        elif key == "ext":
            self.ext_out = self.create_dir_selector(
                frame, "Out Dir:", os.environ.get("WGSE_OUTDIR", "")
            )
            self.ext_region = self.create_entry(frame, "Custom Region:")
        elif key == "anc":
            self.yleaf_path = self.create_file_selector(frame, "Yleaf Path:")
            self.yleaf_pos = self.create_file_selector(frame, "Pos File:")
            self.haplogrep_path = self.create_file_selector(frame, "Haplogrep Path:")
        elif key == "vcf":
            self.vcf_e1 = self.create_file_selector(frame, "Mother/Ann VCF:")
            self.vcf_e2 = self.create_file_selector(frame, "Father/Filter Expr:")
            self.vcf_e3 = self.create_entry(frame, "Gene/Region:")
            self.vcf_vep_cache = self.create_dir_selector(
                frame, "VEP Cache:", os.path.expanduser("~/.vep")
            )
            self.vcf_vep_args = self.create_entry(frame, "Extra VEP Args:")
        grid_f = ctk.CTkFrame(frame, fg_color="transparent")
        grid_f.pack(fill="x", padx=20, pady=10)
        for i, cmd_m in enumerate(meta["commands"]):
            r, c = divmod(i, 3)
            grid_f.grid_columnconfigure(c, weight=1)
            btn = ctk.CTkButton(
                grid_f,
                text=cmd_m["label"],
                command=lambda cc=cmd_m["cmd"]: self.run_dispatch(cc),
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cmd_m["help"])

    def create_entry(self, p, l):
        f = ctk.CTkFrame(p)
        f.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f, text=l, width=120, anchor="w").pack(side="left", padx=10)
        e = ctk.CTkEntry(f)
        e.pack(side="right", fill="x", expand=True, padx=10)
        return e

    def get_attr(self, k, s, v=None):
        n = f"{k}_{s}"
        (setattr(self, n, v) if v else None)
        return getattr(self, n, None)

    def run_dispatch(self, cmd):
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        if cmd == "vep-download":
            self.run_vep_download()
            return
        if cmd == "info":
            self.run_cmd(
                bc
                + [
                    "info",
                    "--input",
                    self.gen_in.get(),
                    "--ref",
                    self.gen_ref.get(),
                    "--detailed",
                ]
            )
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = bc + ["info", cmd, "--input", self.gen_in.get()]
            (c.extend(["-r", self.gen_region.get()]) if self.gen_region.get() else None)
            self.run_cmd(c)
        elif cmd == "align":
            self.run_cmd(
                bc
                + ["align", "--input", self.align_r1.get(), "--ref", self.gen_ref.get()]
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
            c = bc + ["bam", cmd, "--input", self.bam_in.get()]
            (c.extend(["--ref", self.bam_ref.get()]) if self.bam_ref.get() else None)
            (
                c.append(self.bam_extra.get())
                if cmd == "subset" and self.bam_extra.get()
                else None
            )
            self.run_cmd(c)
        elif cmd.startswith("repair-"):
            self.run_cmd(
                bc
                + ["repair", cmd.replace("repair-", ""), "--input", self.bam_in.get()]
            )
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c = bc + ["extract"]
            (
                c.extend(["--input", self.ext_in.get(), "-r", self.ext_region.get()])
                if cmd == "custom"
                else c.extend([cmd, "--input", self.ext_in.get()])
            )
            (c.extend(["--outdir", self.ext_out.get()]) if self.ext_out.get() else None)
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
                    self.vcf_in.get(),
                    "--mother",
                    self.vcf_e1.get(),
                    "--father",
                    self.vcf_e2.get(),
                ]
            elif sub == "run":
                c += ["--input", self.vcf_in.get(), "--ref", self.vcf_ref.get()]
            elif sub == "verify":
                pass
            else:
                c += ["--input", self.vcf_in.get()]
            if cmd == "vep-verify" and self.lib_ref.get():
                c += ["--ref", self.lib_ref.get()]
            elif self.vcf_ref.get():
                c += ["--ref", self.vcf_ref.get()]
            if sub == "annotate" and self.vcf_e1.get():
                c += ["--ann-vcf", self.vcf_e1.get()]
            if sub == "filter":
                (c.extend(["--expr", self.vcf_e2.get()]) if self.vcf_e2.get() else None)
                (c.extend(["--gene", self.vcf_e3.get()]) if self.vcf_e3.get() else None)
            if (
                sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"]
                and self.vcf_e3.get()
            ):
                c += ["-r", self.vcf_e3.get()]
            if "vep" in cmd:
                cv = (
                    self.vep_cache.get()
                    if cmd == "vep-verify"
                    else self.vcf_vep_cache.get()
                )
                if cv:
                    c += ["--vep-cache", cv]
                if sub == "run" and self.vcf_vep_args.get():
                    c += ["--vep-args", self.vcf_vep_args.get()]
            self.run_cmd(c)
        elif cmd == "microarray":
            sel = [fid for fid, v in self.micro_formats_vars.items() if v.get()]
            if not sel:
                self.log("Error: No formats selected.")
                return
            self.run_cmd(
                bc
                + [
                    "microarray",
                    "--input",
                    self.micro_in.get(),
                    "--ref",
                    self.micro_ref.get(),
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
                    self.anc_in.get(),
                    "--yleaf-path",
                    self.yleaf_path.get(),
                    "--pos-file",
                    self.yleaf_pos.get(),
                ]
            )
        elif cmd == "lineage-mt":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "mt-dna",
                    "--input",
                    self.anc_in.get(),
                    "--haplogrep-path",
                    self.haplogrep_path.get(),
                ]
            )
        elif cmd in ["fastqc", "fastp"]:
            self.run_cmd(bc + ["qc", cmd, "--input", self.qc_in.get()])
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = bc + ["ref", sub]
            if sub == "identify":
                c += ["--input", self.lib_in.get()]
            if sub not in ["download", "download-genes"] and self.lib_ref.get():
                c += ["--ref", self.lib_ref.get()]
            self.run_cmd(c)

    def create_file_selector(self, p, l, iv=""):
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=l, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame)
        entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame, text="Browse", width=80, command=lambda: self.browse_file(entry)
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def create_dir_selector(self, p, l, iv=""):
        frame = ctk.CTkFrame(p)
        ctk.CTkLabel(frame, text=l, width=120, anchor="w").pack(side="left", padx=10)
        entry = ctk.CTkEntry(frame)
        entry.insert(0, iv)
        entry.pack(side="left", fill="x", expand=True, padx=10)
        ctk.CTkButton(
            frame, text="Browse", width=80, command=lambda: self.browse_dir(entry)
        ).pack(side="right", padx=10)
        frame.pack(fill="x", padx=20, pady=5)
        return entry

    def browse_file(self, e):
        f = filedialog.askopenfilename()
        (e.delete(0, "end") or e.insert(0, f) if f else None)

    def browse_dir(self, e):
        d = filedialog.askdirectory()
        (e.delete(0, "end") or e.insert(0, d) if d else None)

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


def main():
    WGSExtractGUI().mainloop()

if __name__ == "__main__":
    main()
