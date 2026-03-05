"""Logic and command execution controller for the WGS Extract GUI."""

import json
import os
import subprocess
import sys
import threading
from typing import Any

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
        self.active_processes: dict[str, subprocess.Popen] = {}

    def run_cmd(
        self, command: list[str], cmd_key: str | None = None, frame: Any = None
    ) -> None:
        """
        Execute a shell command in a background thread and log output.

        Args:
            command: The command and its arguments as a list of strings.
            cmd_key: Unique identifier for this command (to support cancellation).
            frame: The UI frame that triggered the command.
        """
        self.main_app.log(f"Running: {' '.join(command)}")

        if cmd_key and frame:
            frame.after(0, lambda: frame.set_button_state(cmd_key, "running"))

        def run() -> None:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            if cmd_key:
                self.active_processes[cmd_key] = process

            if process.stdout:
                for line in process.stdout:
                    if not self.main_app.winfo_exists():
                        break
                    self.main_app.after(
                        0,
                        lambda line_content=line: self.main_app.log(
                            line_content.strip()
                        ),
                    )

            process.wait()

            if cmd_key in self.active_processes:
                del self.active_processes[cmd_key]

            if self.main_app.winfo_exists():
                self.main_app.after(
                    0,
                    lambda: self.main_app.log(f"Finished (Exit {process.returncode})"),
                )
            if cmd_key and frame and frame.winfo_exists():
                frame.after(0, lambda: frame.set_button_state(cmd_key, "normal"))

        threading.Thread(target=run, daemon=True).start()

    def cancel_cmd(self, cmd_key: str) -> None:
        """Terminate a running process."""
        if cmd_key in self.active_processes:
            proc = self.active_processes[cmd_key]
            self.main_app.log(f"Cancelling process {proc.pid}...")
            proc.terminate()
            # On Unix, we might need kill if it doesn't respond to terminate
            self.main_app.after(1000, lambda: self._force_kill_if_alive(cmd_key, proc))

    def _force_kill_if_alive(self, cmd_key: str, proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            proc.kill()
            if self.main_app.winfo_exists():
                self.main_app.log(f"Force killed process {proc.pid}.")
        if cmd_key in self.active_processes:
            del self.active_processes[cmd_key]

    def run_info_detailed(
        self, input_path: str, ref_path: str, frame: Any = None
    ) -> None:
        """Run detailed info command and show results in a separate window."""
        if not input_path:
            self.main_app.log("Error: --input required for info.")
            return

        if frame:
            frame.after(0, lambda: frame.set_button_state("info", "running"))

        def run() -> None:
            # Skip environment variables for stability
            env = os.environ.copy()
            env["WGSE_SKIP_DOTENV"] = "1"
            cmd = [
                sys.executable,
                "-m",
                "wgsextract_cli.main",
                "info",
                "--input",
                input_path,
                "--detailed",
            ]
            if ref_path:
                cmd.extend(["--ref", ref_path])

            self.main_app.log(f"Running: {' '.join(cmd)}")
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                )
                self.active_processes["info"] = process

                output, _ = process.communicate()

                # Filter out "Analyzing..." line
                lines = [
                    line
                    for line in output.splitlines()
                    if not line.startswith("Analyzing")
                ]
                clean_info = "\n".join(lines).strip()
                title = f"Detailed Info: {os.path.basename(input_path)}"
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0, lambda: self.main_app.show_info_window(title, clean_info)
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.log(f"Error running info: {e}")
            finally:
                if "info" in self.active_processes:
                    del self.active_processes["info"]
                if frame and frame.winfo_exists():
                    frame.after(0, lambda: frame.set_button_state("info", "normal"))

        threading.Thread(target=run, daemon=True).start()

    def run_clear_cache(self, input_path: str, frame: Any) -> None:
        """Delete the info cache for the current file and refresh UI."""
        if not input_path:
            return

        outdir = os.path.dirname(os.path.abspath(input_path))
        json_cache = os.path.join(
            outdir, f"{os.path.basename(input_path)}.wgse_info.json"
        )

        if os.path.exists(json_cache):
            try:
                os.remove(json_cache)
                self.main_app.log(f"Cleared cache: {json_cache}")
                # Re-trigger info fetch to show fresh data
                self.get_info_fast(input_path, frame)
            except Exception as e:
                self.main_app.log(f"Error clearing cache: {e}")
        else:
            self.main_app.log("No cache found to clear.")

    def get_info_fast(self, input_path: str, frame: Any) -> None:
        """
        Run the 'info' command in fast mode and update the frame's info display.

        Args:
            input_path: Path to the BAM/CRAM file.
            frame: The frame containing the info display.
        """
        if not os.path.exists(input_path):
            return

        def run() -> None:
            # Skip environment variables for stability
            env = os.environ.copy()
            env["WGSE_SKIP_DOTENV"] = "1"
            cmd = [
                sys.executable,
                "-m",
                "wgsextract_cli.main",
                "info",
                "--input",
                input_path,
            ]
            try:
                # Run command to ensure cache is populated
                subprocess.run(
                    cmd, capture_output=True, text=True, check=False, env=env
                )

                # Load from json cache
                outdir = os.path.dirname(os.path.abspath(input_path))
                json_cache = os.path.join(
                    outdir, f"{os.path.basename(input_path)}.wgse_info.json"
                )

                if os.path.exists(json_cache):
                    with open(json_cache) as f:
                        data = json.load(f)
                    if frame.winfo_exists():
                        frame.after(0, lambda: frame.update_info_display(data))
                else:
                    if frame.winfo_exists():
                        frame.after(
                            0, lambda: frame.update_info_display("Info not available")
                        )
            except Exception as e:
                if frame.winfo_exists():
                    frame.after(
                        0, lambda _e=e: frame.update_info_display(f"Error: {_e}")
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
            if lib_frame.winfo_exists():
                lib_frame.after(0, lambda: lib_frame.vep_prog_var.set(pct))
                lib_frame.after(
                    0, lambda: lib_frame.vep_stat_var.set(f"{pct * 100:.1f}% - {st}")
                )

        def run() -> None:
            from wgsextract_cli.commands.vep import cmd_vep_download

            class Args:
                vep_version: str
                species: str
                assembly: str
                mirror: str
                vep_cache: str
                ref: str
                progress_callback: Any
                cancel_event: Any

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
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda: self.main_app.log(
                            f"VEP Download {'Succeeded' if success else 'Failed/Cancelled'}"
                        ),
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0, lambda _e=e: self.main_app.log(f"Error: {_e}")
                    )
            finally:
                if lib_frame.winfo_exists():
                    lib_frame.after(0, lib_frame.hide_vep_progress)
                self.main_app.vep_cancel_event = None

        threading.Thread(target=run, daemon=True).start()

    def run_lib_download(
        self, gd: dict[str, Any], lib_frame: Any, restart: bool = False
    ) -> None:
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

        self.main_app.log(
            f"Starting {'restart' if restart else 'download'}: {gd['label']}..."
        )
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
            if lib_frame.winfo_exists():
                lib_frame.after(0, lambda: pv.set(pct))
                lib_frame.after(0, lambda: sv.set(f"{pct * 100:.1f}% - {st}"))

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
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda: self.main_app.log(
                            f"Download {'Succeeded' if success else 'Failed'}: {gd['label']}"
                        ),
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0, lambda _e=e: self.main_app.log(f"Error: {str(_e)}")
                    )
            finally:
                if fn in self.main_app.active_downloads:
                    del self.main_app.active_downloads[fn]
                if lib_frame.winfo_exists():
                    lib_frame.after(0, lib_frame.setup_ui)

        threading.Thread(target=run, daemon=True).start()

    def run_lib_delete(self, group: dict[str, Any], lib_frame: Any) -> None:
        """
        Delete a reference genome and its associated files.

        Args:
            group: Genome data dictionary.
            lib_frame: The library frame instance.
        """
        from wgsextract_cli.core.ref_library import delete_genome

        dest = lib_frame.lib_dest.get()
        fn = group["final"]
        self.main_app.log(f"Deleting {fn} from {dest}...")
        try:
            if delete_genome(fn, dest):
                self.main_app.log(f"Successfully deleted {fn}.")
            else:
                self.main_app.log(f"Failed to delete {fn}.")
        except Exception as e:
            self.main_app.log(f"Error during deletion: {e}")
        finally:
            if lib_frame.winfo_exists():
                lib_frame.after(0, lib_frame.setup_ui)

    def cancel_lib_download(self, fn: str) -> None:
        """
        Cancel an active library download.

        Args:
            fn: Final filename of the genome being downloaded.
        """
        if fn in self.main_app.active_downloads:
            self.main_app.log(f"Cancelling download: {fn}...")
            self.main_app.active_downloads[fn]["cancel_event"].set()

    def cancel_vep_download(self) -> None:
        """Cancel the active VEP cache download."""
        if self.main_app.vep_cancel_event:
            self.main_app.log("Cancelling VEP download...")
            self.main_app.vep_cancel_event.set()

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

        # Extract typed fields
        bam_path = getattr(frame, "bam_entry", None)
        bam_val = bam_path.get() if bam_path else ""

        vcf_path = getattr(frame, "vcf_entry", None)
        vcf_val = vcf_path.get() if vcf_path else ""

        fastq_path = getattr(frame, "fastq_entry", None)
        fastq_val = fastq_path.get() if fastq_path else ""

        ref_path = getattr(frame, "ref_entry", None)
        ref_val = ref_path.get() if ref_path else ""

        if cmd == "info":
            self.run_info_detailed(bam_val, ref_val, frame=frame)

        elif cmd == "clear-cache":
            self.run_clear_cache(bam_val, frame)

        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = bc + ["info", cmd, "--input", bam_val]
            region = getattr(frame, "region_entry", None)
            if region and region.get():
                c.extend(["-r", region.get()])
            self.run_cmd(c, cmd_key=cmd, frame=frame)

        elif cmd == "align":
            c = bc + ["align", "--r1", frame.align_r1.get(), "--ref", ref_val]
            if hasattr(frame, "align_r2") and frame.align_r2.get():
                c.extend(["--r2", frame.align_r2.get()])
            self.run_cmd(c, cmd_key=cmd, frame=frame)

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
            c = bc + ["bam", cmd, "--input", bam_val]
            if ref_val:
                c.extend(["--ref", ref_val])

            region = getattr(frame, "region_entry", None)
            if (
                region
                and region.get()
                and cmd in ["sort", "to-cram", "to-bam", "unalign", "subset"]
            ):
                c.extend(["-r", region.get()])

            extra = getattr(frame, "extra_entry", None)
            if cmd == "subset" and extra and extra.get():
                val = extra.get()
                if val.replace(".", "").isdigit():
                    c.extend(["-f", val])
                else:
                    c.append(val)
            self.run_cmd(c, cmd_key=cmd, frame=frame)

        elif cmd.startswith("repair-"):
            # Repair FTDNA VCF takes VCF input, others take BAM
            input_to_use = vcf_val if cmd == "repair-ftdna-vcf" else bam_val
            self.run_cmd(
                bc + ["repair", cmd.replace("repair-", ""), "--input", input_to_use],
                cmd_key=cmd,
                frame=frame,
            )

        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c = bc + ["extract"]
            region = getattr(frame, "region_entry", None)
            if cmd == "custom" and region:
                c.extend(["--input", bam_val, "-r", region.get()])
            else:
                c.extend([cmd, "--input", bam_val])
            out_dir = getattr(frame, "out_dir", None)
            if out_dir and out_dir.get():
                c.extend(["--outdir", out_dir.get()])
            self.run_cmd(c, cmd_key=cmd, frame=frame)

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
            self._dispatch_vcf_vep(
                cmd,
                sub_cmd=cmd,
                frame=frame,
                bam_val=bam_val,
                vcf_val=vcf_val,
                ref_val=ref_val,
                bc=bc,
            )

        elif cmd == "microarray":
            sel = [fid for fid, v in frame.micro_formats_vars.items() if v.get()]
            if not sel:
                self.main_app.log("Error: No formats selected.")
                return
            self.run_cmd(
                bc
                + [
                    "microarray",
                    "--input",
                    bam_val,
                    "--ref",
                    ref_val,
                    "--formats",
                    ",".join(sel),
                ],
                cmd_key=cmd,
                frame=frame,
            )

        elif cmd == "lineage-y":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "y-dna",
                    "--input",
                    bam_val,
                    "--yleaf-path",
                    frame.yleaf_path.get(),
                    "--pos-file",
                    frame.yleaf_pos.get(),
                ],
                cmd_key=cmd,
                frame=frame,
            )

        elif cmd == "lineage-mt":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "mt-dna",
                    "--input",
                    bam_val,
                    "--haplogrep-path",
                    frame.haplogrep_path.get(),
                ],
                cmd_key=cmd,
                frame=frame,
            )

        elif cmd in ["fastqc", "fastp"]:
            self.run_cmd(
                bc + ["qc", cmd, "--input", fastq_val or bam_val],
                cmd_key=cmd,
                frame=frame,
            )

        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = bc + ["ref", sub]
            if sub == "identify":
                c += ["--input", bam_val]
            if sub not in ["download", "download-genes"] and ref_val:
                c += ["--ref", ref_val]
            self.run_cmd(c, cmd_key=cmd, frame=frame)

    def _dispatch_vcf_vep(
        self,
        cmd: str,
        sub_cmd: str,
        frame: Any,
        bam_val: str,
        vcf_val: str,
        ref_val: str,
        bc: list[str],
    ) -> None:
        """Helper to handle VCF and VEP command dispatching."""
        sub = (
            "qc"
            if cmd == "vcf-qc"
            else cmd.replace("vep-", "")
            if "vep-" in cmd
            else cmd
        )
        c = bc + ["vep" if "vep-" in cmd else "vcf", sub]

        # Determine which input to use
        # Calling actions use BAM
        calling_actions = [
            "snp",
            "indel",
            "freebayes",
            "gatk",
            "deepvariant",
            "sv",
            "cnv",
        ]

        if sub == "trio":
            c += [
                "--proband",
                vcf_val,
                "--mother",
                frame.vcf_mother.get(),
                "--father",
                frame.vcf_father.get(),
            ]
        elif sub == "run":
            # VEP run uses BAM if present, otherwise VCF
            c += ["--input", bam_val or vcf_val, "--ref", ref_val]
        elif sub == "verify":
            pass
        elif sub in calling_actions:
            c += ["--input", bam_val]
        else:
            # Annotate, Filter, QC use VCF
            c += ["--input", vcf_val]

        if cmd == "vep-verify" and ref_val:
            c += ["--ref", ref_val]
        elif ref_val:
            c += ["--ref", ref_val]

        if sub == "annotate" and frame.vcf_ann_vcf.get():
            c += ["--ann-vcf", frame.vcf_ann_vcf.get()]
        if sub == "filter":
            if frame.vcf_filter_expr.get():
                c.extend(["--expr", frame.vcf_filter_expr.get()])
            if frame.vcf_gene.get():
                c.extend(["--gene", frame.vcf_gene.get()])
            if frame.vcf_region.get():
                c.extend(["--region", frame.vcf_region.get()])
        if (
            sub in ["snp", "indel", "freebayes", "gatk", "deepvariant", "run"]
            and hasattr(frame, "vcf_region")
            and frame.vcf_region.get()
        ):
            c += ["-r", frame.vcf_region.get()]

        if "vep" in cmd:
            vvc = getattr(frame, "vcf_vep_cache", None)
            cv = (
                frame.vep_cache.get()
                if hasattr(frame, "vep_cache")
                else vvc.get()
                if vvc
                else None
            )
            if cv:
                c += ["--vep-cache", cv]
            if sub == "run" and frame.vcf_vep_args.get():
                c += ["--vep-args", frame.vcf_vep_args.get()]
        self.run_cmd(c, cmd_key=cmd, frame=frame)
