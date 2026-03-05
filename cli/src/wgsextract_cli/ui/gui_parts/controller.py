"""Logic and command execution controller for the WGS Extract GUI."""

import subprocess
import sys
import threading
from typing import Any, Callable, Optional, Union

import customtkinter as ctk


class GUIController:
    """Handles the execution of background commands and logic for the GUI."""

    def __init__(self, main_app: Any) -> None:
        """
        Initialize the controller.

        Args:
            main_app: The main application instance (WGSExtractGUI).
        """
        self.main_app = main_app

    def run_cmd(self, command: list[str]) -> None:
        """
        Execute a shell command in a background thread and log output.

        Args:
            command: The command and its arguments as a list of strings.
        """
        self.main_app.log(f"Running: {' '.join(command)}")

        def run() -> None:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if process.stdout:
                for line in process.stdout:
                    self.main_app.after(0, lambda l=line: self.main_app.log(l.strip()))
            process.wait()
            self.main_app.after(
                0, lambda: self.main_app.log(f"Finished (Exit {process.returncode})")
            )

        threading.Thread(target=run, daemon=True).start()

    def run_vep_download(self, lib_frame: Any) -> None:
        """
        Launch the VEP cache download process.

        Args:
            lib_frame: The library frame instance containing VEP UI.
        """
        lib_frame.show_vep_progress()
        self.main_app.vep_cancel_event = threading.Event()

        def cb(downloaded: int, total: int, speed: float) -> None:
            pct = downloaded / total if total > 0 else 0
            st = (
                f"{speed / (1024 * 1024):.1f} MB/s"
                if speed > 1024 * 1024
                else f"{speed / 1024:.1f} KB/s"
            )
            self.main_app.after(0, lambda: lib_frame.vep_prog_var.set(pct))
            self.main_app.after(
                0, lambda: lib_frame.vep_stat_var.set(f"{pct * 100:.1f}% - {st}")
            )

        def run() -> None:
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
            a.cancel_event = self.main_app.vep_cancel_event
            self.main_app.log("Starting VEP cache download...")
            try:
                success = cmd_vep_download(a)
                self.main_app.after(
                    0,
                    lambda: self.main_app.log(
                        f"VEP Download {'Succeeded' if success else 'Failed/Cancelled'}"
                    ),
                )
            except Exception as e:
                self.main_app.after(0, lambda: self.main_app.log(f"Error: {e}"))
            finally:
                self.main_app.after(0, lib_frame.hide_vep_progress)
                self.main_app.vep_cancel_event = None

        threading.Thread(target=run, daemon=True).start()

    def run_lib_download(self, gd: dict[str, Any], lib_frame: Any, restart: bool = False) -> None:
        """
        Launch a reference genome download.

        Args:
            gd: Genome data dictionary.
            lib_frame: The library frame instance.
            restart: Whether to restart a failed/incomplete download.
        """
        dest = lib_frame.lib_dest.get()
        fn = gd["final"]
        if fn in self.main_app.active_downloads:
            return
            
        self.main_app.log(f"Starting {'restart' if restart else 'download'}: {gd['label']}...")
        ce = threading.Event()
        pv = ctk.DoubleVar(value=0)
        sv = ctk.StringVar(value="Waiting...")
        self.main_app.active_downloads[fn] = {
            "cancel_event": ce,
            "progress_var": pv,
            "status_var": sv,
        }
        lib_frame.setup_ui()

        def cb(downloaded: int, total: int, speed: float) -> None:
            pct = downloaded / total if total > 0 else 0
            st = (
                f"{speed / (1024 * 1024):.1f} MB/s"
                if speed > 1024 * 1024
                else f"{speed / 1024:.1f} KB/s"
            )
            self.main_app.after(0, lambda: pv.set(pct))
            self.main_app.after(0, lambda: sv.set(f"{pct * 100:.1f}% - {st}"))

        def run() -> None:
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
                self.main_app.after(
                    0,
                    lambda: self.main_app.log(
                        f"Download {'Succeeded' if success else 'Failed'}: {gd['label']}"
                    ),
                )
            except Exception as e:
                self.main_app.after(0, lambda: self.main_app.log(f"Error: {str(e)}"))
            finally:
                if fn in self.main_app.active_downloads:
                    del self.main_app.active_downloads[fn]
                self.main_app.after(0, lib_frame.setup_ui)

        threading.Thread(target=run, daemon=True).start()

    def run_dispatch(self, cmd: str, frame: Any) -> None:
        """
        Maps UI button commands to actual CLI operations.

        Args:
            cmd: The command identifier from UI_METADATA.
            frame: The frame from which the command was triggered.
        """
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        
        if cmd == "vep-download":
            self.run_vep_download(frame)
            return

        # Extract common fields if they exist in the frame
        input_path = getattr(frame, "input_entry", None)
        input_val = input_path.get() if input_path else ""
        
        ref_path = getattr(frame, "ref_entry", None)
        ref_val = ref_path.get() if ref_path else ""

        if cmd == "info":
            self.run_cmd(bc + ["info", "--input", input_val, "--ref", ref_val, "--detailed"])
        
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = bc + ["info", cmd, "--input", input_val]
            region = getattr(frame, "region_entry", None)
            if region and region.get():
                c.extend(["-r", region.get()])
            self.run_cmd(c)
            
        elif cmd == "align":
            self.run_cmd(bc + ["align", "--input", frame.align_r1.get(), "--ref", ref_val])
            
        elif cmd in ["sort", "index", "unindex", "unsort", "to-cram", "to-bam", "unalign", "subset", "mt-extract"]:
            c = bc + ["bam", cmd, "--input", input_val]
            if ref_val:
                c.extend(["--ref", ref_val])
            extra = getattr(frame, "extra_entry", None)
            if cmd == "subset" and extra and extra.get():
                c.append(extra.get())
            self.run_cmd(c)
            
        elif cmd.startswith("repair-"):
            self.run_cmd(bc + ["repair", cmd.replace("repair-", ""), "--input", input_val])
            
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c = bc + ["extract"]
            region = getattr(frame, "region_entry", None)
            if cmd == "custom" and region:
                c.extend(["--input", input_val, "-r", region.get()])
            else:
                c.extend([cmd, "--input", input_val])
            out_dir = getattr(frame, "out_dir", None)
            if out_dir and out_dir.get():
                c.extend(["--outdir", out_dir.get()])
            self.run_cmd(c)
            
        elif cmd in [
            "snp", "indel", "sv", "cnv", "freebayes", "gatk", "deepvariant",
            "annotate", "filter", "trio", "vcf-qc", "vep-run", "vep-verify"
        ]:
            self._dispatch_vcf_vep(cmd, sub_cmd=cmd, frame=frame, input_val=input_val, ref_val=ref_val, bc=bc)
            
        elif cmd == "microarray":
            sel = [fid for fid, v in frame.micro_formats_vars.items() if v.get()]
            if not sel:
                self.main_app.log("Error: No formats selected.")
                return
            self.run_cmd(bc + ["microarray", "--input", input_val, "--ref", ref_val, "--formats", ",".join(sel)])
            
        elif cmd == "lineage-y":
            self.run_cmd(bc + ["lineage", "y-dna", "--input", input_val, "--yleaf-path", frame.yleaf_path.get(), "--pos-file", frame.yleaf_pos.get()])
            
        elif cmd == "lineage-mt":
            self.run_cmd(bc + ["lineage", "mt-dna", "--input", input_val, "--haplogrep-path", frame.haplogrep_path.get()])
            
        elif cmd in ["fastqc", "fastp"]:
            self.run_cmd(bc + ["qc", cmd, "--input", input_val])
            
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = bc + ["ref", sub]
            if sub == "identify":
                c += ["--input", input_val]
            if sub not in ["download", "download-genes"] and ref_val:
                c += ["--ref", ref_val]
            self.run_cmd(c)

    def _dispatch_vcf_vep(self, cmd: str, sub_cmd: str, frame: Any, input_val: str, ref_val: str, bc: list[str]) -> None:
        """Helper to handle VCF and VEP command dispatching."""
        sub = "qc" if cmd == "vcf-qc" else cmd.replace("vep-", "") if "vep-" in cmd else cmd
        c = bc + ["vep" if "vep-" in cmd else "vcf", sub]
        
        if sub == "trio":
            c += ["--proband", input_val, "--mother", frame.vcf_e1.get(), "--father", frame.vcf_e2.get()]
        elif sub == "run":
            c += ["--input", input_val, "--ref", ref_val]
        elif sub == "verify":
            pass
        else:
            c += ["--input", input_val]
            
        if cmd == "vep-verify" and ref_val:
            c += ["--ref", ref_val]
        elif ref_val:
            c += ["--ref", ref_val]
            
        if sub == "annotate" and frame.vcf_e1.get():
            c += ["--ann-vcf", frame.vcf_e1.get()]
        if sub == "filter":
            if frame.vcf_e2.get(): c.extend(["--expr", frame.vcf_e2.get()])
            if frame.vcf_e3.get(): c.extend(["--gene", frame.vcf_e3.get()])
        if sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"] and frame.vcf_e3.get():
            c += ["-r", frame.vcf_e3.get()]
            
        if "vep" in cmd:
            cv = frame.vep_cache.get() if hasattr(frame, "vep_cache") else getattr(frame, "vcf_vep_cache", None).get()
            if cv: c += ["--vep-cache", cv]
            if sub == "run" and frame.vcf_vep_args.get():
                c += ["--vep-args", frame.vcf_vep_args.get()]
        self.run_cmd(c)
