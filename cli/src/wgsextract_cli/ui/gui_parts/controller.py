"""Logic and command execution controller for the WGS Extract GUI."""

import json
import os
import subprocess
import sys
import threading
from typing import Any

import customtkinter as ctk

from wgsextract_cli.core.gene_map import (
    are_gene_maps_installed,
    delete_gene_maps,
    download_gene_maps,
)
from wgsextract_cli.core.messages import GUI_LABELS, GUI_MESSAGES, LOG_MESSAGES
from wgsextract_cli.core.utils import proc_registry


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
        self,
        command: list[str],
        cmd_key: str | None = None,
        frame: Any = None,
        on_finish: Any | None = None,
        label: str | None = None,
    ) -> None:
        """
        Execute a shell command in a background thread and log output.

        Args:
            command: The command and its arguments as a list of strings.
            cmd_key: Unique identifier for this command (to support cancellation).
            frame: The UI frame that triggered the command.
            on_finish: Optional callback to run when the command finishes.
            label: Display label for the log tab.
        """
        tab_key = self.main_app.add_log_tab(label or cmd_key or "Task", cmd_key=cmd_key)
        self.main_app.log(
            LOG_MESSAGES["running_cmd"].format(command=" ".join(command)),
            tab_key=tab_key,
        )

        if cmd_key and frame:
            frame.after(0, lambda: frame.set_button_state(cmd_key, "running"))

        def run() -> None:
            # Use process groups so we can kill children (like bcftools)
            popen_kwargs: dict[str, Any] = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,  # Separate stderr to prefix it differently
                "text": True,
                "bufsize": 1,
                "errors": "replace",
            }

            if sys.platform == "win32":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["preexec_fn"] = os.setpgrp

            # Add parent PID for automatic cleanup if GUI dies
            command.extend(["--parent-pid", str(os.getpid())])

            process = subprocess.Popen(command, **popen_kwargs)

            if cmd_key:
                self.active_processes[cmd_key] = process
                proc_registry.register_process(cmd_key, process)

            # Function to read a stream and log it with a prefix
            def read_stream(stream: Any, default_prefix: str) -> None:
                if not stream:
                    return
                for line in stream:
                    if not self.main_app.winfo_exists():
                        break
                    msg = line.strip()
                    if not msg:
                        continue

                    # Intelligent level detection for tools like GATK/samtools
                    upper_msg = msg.upper()
                    detected_lvl = default_prefix

                    # Heuristics for info/warning/error keywords in the line
                    if (
                        " ERROR " in upper_msg
                        or "EXCEPTION" in upper_msg
                        or " FATAL " in upper_msg
                    ):
                        detected_lvl = "❌"
                    elif " WARN " in upper_msg or " WARNING " in upper_msg:
                        detected_lvl = "⚠️"
                    elif (
                        " INFO " in upper_msg
                        or msg.startswith("[")
                        or "USING GATK JAR" in upper_msg
                        or "RUNNING:" in upper_msg
                        or "RUNTIME.TOTALMEMORY" in upper_msg
                        or msg.startswith("/")  # Command echoes often start with paths
                    ):
                        # samtools uses [mpileup] etc on stderr, those are info
                        detected_lvl = "ℹ️"
                    elif " DEBUG " in upper_msg:
                        detected_lvl = "🔍"

                    # If the message already starts with our final prefix strings, don't re-add
                    if any(
                        msg.startswith(p)
                        for p in [
                            "🔍",
                            "ℹ️",
                            "⚠️",
                            "❌",
                            "🚨",
                        ]
                    ):
                        final_msg = msg
                    else:
                        final_msg = f"{detected_lvl}: {msg}"

                    self.main_app.after(
                        0,
                        lambda m=final_msg: self.main_app.log(m, tab_key=tab_key),
                    )

            # Use threads to read stdout and stderr concurrently
            import threading

            t1 = threading.Thread(target=read_stream, args=(process.stdout, "ℹ️"))
            t2 = threading.Thread(target=read_stream, args=(process.stderr, "❌"))
            t1.start()
            t2.start()

            process.wait()
            t1.join()
            t2.join()

            if cmd_key in self.active_processes:
                del self.active_processes[cmd_key]
                proc_registry.unregister_process(cmd_key)

            if self.main_app.winfo_exists():
                self.main_app.after(
                    0,
                    lambda: self.main_app.log(
                        LOG_MESSAGES["finished_exit"].format(code=process.returncode),
                        tab_key=tab_key,
                    ),
                )

                # Check if tab should be closed (was marked for closure during cancellation)
                if tab_key in self.main_app.pending_closure:
                    self.main_app.after(
                        500, lambda: self.main_app.remove_log_tab(tab_key)
                    )
                else:
                    self.main_app.after(
                        0, lambda: self.main_app.mark_tab_finished(tab_key)
                    )

            if cmd_key and frame and frame.winfo_exists():
                frame.after(0, lambda: frame.set_button_state(cmd_key, "normal"))
            if on_finish and frame and frame.winfo_exists():
                frame.after(0, on_finish)

        threading.Thread(target=run, daemon=True).start()

    def cancel_cmd(self, cmd_key: str) -> None:
        """Terminate a running process group."""
        if cmd_key in self.active_processes:
            proc = self.active_processes[cmd_key]
            tab_key = self.main_app.cmd_to_tab.get(cmd_key, "Main")
            self.main_app.log(
                LOG_MESSAGES["cancelling_proc"].format(pid=proc.pid), tab_key=tab_key
            )

            try:
                if sys.platform == "win32":
                    import signal

                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    import signal

                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception as e:
                self.main_app.log(
                    LOG_MESSAGES["cancel_error"].format(error=e), tab_key=tab_key
                )

            # On Unix, we might need kill if it doesn't respond to terminate
            self.main_app.after(1000, lambda: self._force_kill_if_alive(cmd_key, proc))

    def cancel_all(self) -> None:
        """Terminate all active process groups."""
        # Copy keys to avoid mutation issues during iteration
        keys = list(self.active_processes.keys())
        for key in keys:
            self.cancel_cmd(key)

        # Also signal threading events
        if self.main_app.vep_cancel_event:
            self.main_app.vep_cancel_event.set()
        if self.main_app.gene_map_cancel_event:
            self.main_app.gene_map_cancel_event.set()

        # Signal all library downloads
        for fn in list(self.main_app.active_downloads.keys()):
            self.cancel_lib_download(fn)

    def _force_kill_if_alive(self, cmd_key: str, proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            tab_key = self.main_app.cmd_to_tab.get(cmd_key, "Main")
            try:
                if sys.platform == "win32":
                    proc.kill()
                else:
                    import signal

                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                if self.main_app.winfo_exists():
                    self.main_app.log(
                        LOG_MESSAGES["force_killed"].format(pid=proc.pid),
                        tab_key=tab_key,
                    )
            except Exception:
                pass

        if cmd_key in self.active_processes:
            del self.active_processes[cmd_key]
            proc_registry.unregister_process(cmd_key)

    def run_info_detailed(
        self, input_path: str, ref_path: str, frame: Any = None
    ) -> None:
        """Run detailed info command and show results in a separate window."""
        if not input_path:
            self.main_app.log(
                GUI_MESSAGES["error_input_required"].format(field="--input")
            )
            return

        tab_key = self.main_app.add_log_tab("Detailed Info", cmd_key="info")
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

            self.main_app.log(
                LOG_MESSAGES["running_cmd"].format(command=" ".join(cmd)),
                tab_key=tab_key,
            )
            try:
                # Use process groups so we can kill children safely
                popen_kwargs: dict[str, Any] = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.STDOUT,
                    "text": True,
                    "env": env,
                }
                if sys.platform == "win32":
                    popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
                else:
                    popen_kwargs["preexec_fn"] = os.setpgrp

                # Add parent PID
                cmd.extend(["--parent-pid", str(os.getpid())])

                process = subprocess.Popen(cmd, **popen_kwargs)
                self.active_processes["info"] = process
                proc_registry.register_process("info", process)

                output, _ = process.communicate()

                if process.returncode != 0:
                    # Cancelled or failed, don't open a blank window
                    self.main_app.log(
                        f"Info process finished (Exit {process.returncode}).",
                        tab_key=tab_key,
                    )
                    return

                # Filter out "Analyzing..." line
                lines = [
                    line
                    for line in output.splitlines()
                    if not line.startswith("Analyzing")
                ]
                clean_info = "\n".join(lines).strip()
                title = GUI_MESSAGES["detailed_info_title"].format(
                    filename=os.path.basename(input_path)
                )
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0, lambda: self.main_app.show_info_window(title, clean_info)
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.log(
                        GUI_MESSAGES["info_error"].format(error=e), tab_key=tab_key
                    )
            finally:
                if "info" in self.active_processes:
                    del self.active_processes["info"]
                    proc_registry.unregister_process("info")
                if frame and frame.winfo_exists():
                    frame.after(0, lambda: frame.set_button_state("info", "normal"))

                if tab_key in self.main_app.pending_closure:
                    self.main_app.after(
                        500, lambda: self.main_app.remove_log_tab(tab_key)
                    )
                else:
                    self.main_app.after(
                        0, lambda: self.main_app.mark_tab_finished(tab_key)
                    )

        threading.Thread(target=run, daemon=True).start()

    def run_clear_cache(self, input_path: str, frame: Any) -> None:
        """Delete the info cache for the current file and refresh UI."""
        if not input_path:
            return

        out_dir = self.main_app.out_dir_var.get()
        effective_outdir = (
            out_dir if out_dir else os.path.dirname(os.path.abspath(input_path))
        )
        json_cache = os.path.join(
            effective_outdir, f"{os.path.basename(input_path)}.wgse_info.json"
        )

        if os.path.exists(json_cache):
            try:
                os.remove(json_cache)
                self.main_app.log(LOG_MESSAGES["cleared_cache"].format(path=json_cache))
                # Re-trigger info fetch to show fresh data
                ref_path = (
                    self.main_app.ref_path_var.get()
                    if hasattr(self.main_app, "ref_path_var")
                    else None
                )
                self.get_info_fast(input_path, frame, ref_path=ref_path)
            except Exception as e:
                self.main_app.log(f"Error clearing cache: {e}")
        else:
            self.main_app.log(LOG_MESSAGES["no_cache_found"].format(path=json_cache))

    def get_info_fast(
        self, input_path: str, frame: Any, ref_path: str | None = None
    ) -> None:
        """
        Run the 'info' command in fast mode and update the frame's info display.

        Args:
            input_path: Path to the BAM/CRAM file.
            frame: The frame containing the info display.
            ref_path: Optional path to reference genome (required for some CRAMs).
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
                "--debug",
                "info",
                "--input",
                input_path,
            ]
            if ref_path:
                cmd.extend(["--ref", ref_path])

            # Respect outdir if set in GUI
            out_dir = self.main_app.out_dir_var.get()
            if out_dir:
                cmd.extend(["--outdir", out_dir])

            # Add parent PID
            cmd.extend(["--parent-pid", str(os.getpid())])

            self.main_app.log(f"🔍: Triggering fast info: {' '.join(cmd)}")
            try:
                # Run command to ensure cache is populated
                res = subprocess.run(
                    cmd, capture_output=True, text=True, check=False, env=env
                )

                # Log any output from the command to help debugging
                if res.stdout:
                    for line in res.stdout.strip().splitlines():
                        self.main_app.after(
                            0,
                            lambda msg_line=line: self.main_app.log(f"ℹ️: {msg_line}"),
                        )
                if res.stderr:
                    for line in res.stderr.strip().splitlines():
                        self.main_app.after(
                            0,
                            lambda msg_line=line: self.main_app.log(f"🔍: {msg_line}"),
                        )

                if res.returncode != 0:
                    self.main_app.after(
                        0,
                        lambda r=res.returncode: self.main_app.log(
                            LOG_MESSAGES["fast_info_failed"].format(code=r)
                        ),
                    )

                # Load from json cache - use the same logic as the info command
                effective_outdir = (
                    out_dir if out_dir else os.path.dirname(os.path.abspath(input_path))
                )
                json_cache = os.path.join(
                    effective_outdir, f"{os.path.basename(input_path)}.wgse_info.json"
                )

                if os.path.exists(json_cache):
                    with open(json_cache) as f:
                        data = json.load(f)
                    if frame.winfo_exists():
                        frame.after(0, lambda: frame.update_info_display(data))
                else:
                    msg = "Info not available"
                    self.main_app.after(
                        0,
                        lambda: self.main_app.log(
                            f"DEBUG: Cache file not found at {json_cache} after running info command."
                        ),
                    )
                    if res.returncode != 0:
                        # Extract the last line of stderr as it often contains the error message
                        last_line = (
                            res.stderr.strip().splitlines()[-1]
                            if res.stderr
                            else "unknown error"
                        )
                        msg = f"Info error: {last_line}"
                    if frame.winfo_exists():
                        frame.after(0, lambda: frame.update_info_display(msg))
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
        errors = []
        if not lib_frame.vep_cache.get():
            errors.append(
                GUI_MESSAGES["error_input_required"].format(
                    field=GUI_LABELS["vep_cache_path"]
                )
            )
        if not lib_frame.ref_entry.get():
            errors.append(
                GUI_MESSAGES["error_input_required"].format(
                    field=GUI_LABELS["ref_library_path"]
                )
            )

        if errors:
            self.main_app.show_error(
                GUI_MESSAGES["error_missing_input"], "\n".join(errors)
            )
            return

        tab_key = self.main_app.add_log_tab("VEP Download", cmd_key="vep-download")
        lib_frame.show_vep_progress()
        self.main_app.vep_cancel_event = threading.Event()
        proc_registry.register_event("vep-download", self.main_app.vep_cancel_event)

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
            self.main_app.log(LOG_MESSAGES["starting_vep_dl"], tab_key=tab_key)
            try:
                success = cmd_vep_download(a)
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda: self.main_app.log(
                            LOG_MESSAGES["vep_dl_success"]
                            if success
                            else LOG_MESSAGES["vep_dl_failed"],
                            tab_key=tab_key,
                        ),
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda _e=e: self.main_app.log(f"Error: {_e}", tab_key=tab_key),
                    )
            finally:
                if lib_frame.winfo_exists():
                    lib_frame.after(0, lib_frame.hide_vep_progress)
                self.main_app.vep_cancel_event = None
                proc_registry.unregister_event("vep-download")

                if tab_key in self.main_app.pending_closure:
                    self.main_app.after(
                        500, lambda: self.main_app.remove_log_tab(tab_key)
                    )
                else:
                    self.main_app.after(
                        0, lambda: self.main_app.mark_tab_finished(tab_key)
                    )

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
        if not dest:
            self.main_app.show_error(
                GUI_MESSAGES["error_missing_input"],
                GUI_MESSAGES["error_input_required"].format(
                    field=GUI_LABELS["ref_library_path"]
                ),
            )
            return

        fn = gd["final"]
        if fn in self.main_app.active_downloads:
            return

        mode = "restart" if restart else "download"
        tab_key = self.main_app.add_log_tab(f"DL: {gd['label']}", cmd_key=fn)
        self.main_app.log(
            LOG_MESSAGES["starting_lib_dl"].format(mode=mode, label=gd["label"]),
            tab_key=tab_key,
        )
        ce = threading.Event()
        proc_registry.register_event(fn, ce)
        pv = ctk.DoubleVar(value=0)
        sv = ctk.StringVar(value="Waiting...")
        self.main_app.active_downloads[fn] = {
            "cancel_event": ce,
            "progress_var": pv,
            "status_var": sv,
        }
        lib_frame.setup_ui()

        def cb(downloaded: int, total: int, speed: float) -> None:
            pct = downloaded / total if total > 0 else 1.0
            st = (
                f"{speed / (1024 * 1024):.1f} MB/s"
                if speed > 1024 * 1024
                else f"{speed / 1024:.1f} KB/s"
            )
            if lib_frame.winfo_exists():
                lib_frame.after(0, lambda: pv.set(pct))
                lib_frame.after(0, lambda: sv.set(f"{pct * 100:.1f}% - {st}") or None)

        def run() -> None:
            from wgsextract_cli.core.ref_library import download_and_process_genome

            def status_cb(msg: str):
                if self.main_app.winfo_exists():

                    def update():
                        sv.set(msg)
                        # Hide progress bar when processing starts
                        if msg.startswith("Processing"):
                            di = self.main_app.active_downloads.get(fn)
                            if di and "pbar_widget" in di:
                                di["pbar_widget"].pack_forget()

                    self.main_app.after(0, update)
                self.main_app.log(msg, tab_key=tab_key)

            try:
                success = download_and_process_genome(
                    gd,
                    dest,
                    interactive=False,
                    progress_callback=cb,
                    cancel_event=ce,
                    restart=restart,
                    status_callback=status_cb,
                )
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda: self.main_app.log(
                            (
                                LOG_MESSAGES["lib_dl_success"]
                                if success
                                else LOG_MESSAGES["lib_dl_failed"]
                            ).format(label=gd["label"]),
                            tab_key=tab_key,
                        ),
                    )
            except Exception as e:
                if self.main_app.winfo_exists():
                    self.main_app.after(
                        0,
                        lambda _e=e: self.main_app.log(
                            f"Error: {str(_e)}", tab_key=tab_key
                        ),
                    )
            finally:
                if fn in self.main_app.active_downloads:
                    del self.main_app.active_downloads[fn]
                proc_registry.unregister_event(fn)
                if self.main_app.winfo_exists():
                    self.main_app.after(0, self.main_app.refresh_all_frames)
                if lib_frame.winfo_exists():
                    lib_frame.after(0, lib_frame.setup_ui)

                if tab_key in self.main_app.pending_closure:
                    self.main_app.after(
                        500, lambda: self.main_app.remove_log_tab(tab_key)
                    )
                else:
                    self.main_app.after(
                        0, lambda: self.main_app.mark_tab_finished(tab_key)
                    )

        threading.Thread(target=run, daemon=True).start()

    def run_lib_delete(self, group: dict[str, Any], lib_frame: Any) -> None:
        """
        Delete a reference genome and its associated files.

        Args:
            group: Genome data dictionary.
            lib_frame: The library frame instance.
        """
        dest = lib_frame.lib_dest.get()
        if not dest:
            self.main_app.show_error(
                GUI_MESSAGES["error_missing_input"],
                GUI_MESSAGES["error_input_required"].format(
                    field=GUI_LABELS["ref_library_path"]
                ),
            )
            return

        from wgsextract_cli.core.ref_library import delete_genome

        fn = group["final"]
        self.main_app.log(
            LOG_MESSAGES["deleting_genome"].format(filename=fn, path=dest)
        )
        try:
            if delete_genome(fn, dest):
                self.main_app.log(LOG_MESSAGES["delete_success"].format(filename=fn))
            else:
                self.main_app.log(LOG_MESSAGES["delete_failed"].format(filename=fn))
        except Exception as e:
            self.main_app.log(f"Error during deletion: {e}")
        finally:
            if self.main_app.winfo_exists():
                self.main_app.after(0, self.main_app.refresh_all_frames)
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

    def run_ref_index(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Run index command for a specific reference genome."""
        dest = lib_frame.lib_dest.get()
        if not dest:
            return

        final_path = os.path.join(dest, "genomes", group["final"])
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        cmd = bc + ["ref", "index", "--ref", final_path]
        self.run_cmd(
            cmd,
            cmd_key=f"index-{group['final']}",
            frame=lib_frame,
            on_finish=lib_frame.setup_ui,
            label=f"Index {group['final']}",
        )

    def run_ref_unindex(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delete index files for a specific reference genome."""
        dest = lib_frame.lib_dest.get()
        if not dest:
            return

        from wgsextract_cli.core.ref_library import delete_ref_index

        fn = group["final"]
        self.main_app.log(f"Unindexing {fn} in {dest}...")
        try:
            if delete_ref_index(fn, dest):
                self.main_app.log(f"Successfully removed index for {fn}.")
            else:
                self.main_app.log(f"Failed to remove index for {fn}.")
        except Exception as e:
            self.main_app.log(f"Error during unindexing: {e}")
        finally:
            if lib_frame.winfo_exists():
                lib_frame.after(0, lib_frame.setup_ui)

    def run_ref_verify(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Run verify command for a specific reference genome."""
        dest = lib_frame.lib_dest.get()
        if not dest:
            return

        final_path = os.path.join(dest, "genomes", group["final"])
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        cmd = bc + ["ref", "verify", "--ref", final_path]
        self.run_cmd(
            cmd,
            cmd_key=f"verify-{group['final']}",
            frame=lib_frame,
            on_finish=lib_frame.setup_ui,
            label=f"Verify {group['final']}",
        )

    def run_ref_count_ns(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Run count-ns command for a specific reference genome."""
        dest = lib_frame.lib_dest.get()
        if not dest:
            return

        final_path = os.path.join(dest, "genomes", group["final"])
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        cmd = bc + ["ref", "count-ns", "--ref", final_path]
        self.run_cmd(
            cmd,
            cmd_key=f"count-ns-{group['final']}",
            frame=lib_frame,
            on_finish=lib_frame.setup_ui,
            label=f"Count Ns {group['final']}",
        )

    def run_ref_del_ns(self, group: dict[str, Any], lib_frame: Any) -> None:
        """Delete N-count files for a specific reference genome."""
        dest = lib_frame.lib_dest.get()
        if not dest:
            return

        from wgsextract_cli.core.ref_library import delete_ref_ns

        fn = group["final"]
        self.main_app.log(f"Deleting N-count files for {fn} in {dest}...")
        try:
            if delete_ref_ns(fn, dest):
                self.main_app.log(f"Successfully removed N-count files for {fn}.")
            else:
                self.main_app.log(f"Failed to remove N-count files for {fn}.")
        except Exception as e:
            self.main_app.log(f"Error during N-count deletion: {e}")
        finally:
            if lib_frame.winfo_exists():
                lib_frame.after(0, lib_frame.setup_ui)

    def cancel_vep_download(self) -> None:
        """Cancel the active VEP cache download."""
        if self.main_app.vep_cancel_event:
            self.main_app.log("Cancelling VEP download...")
            self.main_app.vep_cancel_event.set()

    def cancel_gene_map_download(self) -> None:
        """Cancel the active gene map download."""
        if self.main_app.gene_map_cancel_event:
            self.main_app.log("Cancelling Gene Map download...")
            self.main_app.gene_map_cancel_event.set()

    def run_gene_map_op(self, frame: Any) -> None:
        """Downloads or deletes the Gene Map database based on current status."""
        reflib = self.main_app.ref_path_var.get()
        if not reflib:
            self.main_app.show_error(
                "Missing Required Input", "Reference Library path is required."
            )
            return

        if are_gene_maps_installed(reflib):
            tab_key = self.main_app.add_log_tab("Gene Map Delete")
            self.main_app.log(f"Deleting Gene Maps from {reflib}...", tab_key=tab_key)
            if delete_gene_maps(reflib):
                self.main_app.log("Successfully deleted Gene Maps.", tab_key=tab_key)
            else:
                self.main_app.log("Failed to delete Gene Maps.", tab_key=tab_key)
            if frame and frame.winfo_exists():
                frame.setup_ui()
        else:
            tab_key = self.main_app.add_log_tab(
                "Gene Map Download", cmd_key="ref-gene-map"
            )
            self.main_app.log(f"Downloading Gene Maps to {reflib}...", tab_key=tab_key)
            if frame and frame.winfo_exists():
                frame.set_button_state("ref-gene-map", "running")

            self.main_app.gene_map_cancel_event = threading.Event()

            def run():
                try:
                    success = download_gene_maps(
                        reflib, cancel_event=self.main_app.gene_map_cancel_event
                    )
                    if self.main_app.winfo_exists():
                        if success:
                            self.main_app.after(
                                0,
                                lambda: self.main_app.log(
                                    "Successfully downloaded Gene Maps.",
                                    tab_key=tab_key,
                                ),
                            )
                        else:
                            self.main_app.after(
                                0,
                                lambda: self.main_app.log(
                                    "Gene Map download cancelled or failed.",
                                    tab_key=tab_key,
                                ),
                            )
                finally:
                    self.main_app.gene_map_cancel_event = None
                    if frame and frame.winfo_exists():
                        frame.after(
                            0, lambda: frame.set_button_state("ref-gene-map", "normal")
                        )
                        frame.after(0, frame.setup_ui)

                    if tab_key in self.main_app.pending_closure:
                        self.main_app.after(
                            500, lambda: self.main_app.remove_log_tab(tab_key)
                        )
                    else:
                        self.main_app.after(
                            0, lambda: self.main_app.mark_tab_finished(tab_key)
                        )

            threading.Thread(target=run, daemon=True).start()

    def run_pet_align(self, frame: Any, extra_args: dict[str, str]) -> None:
        """Execute the pet-align command."""
        ref_fasta = self.main_app.pet_ref_fasta_var.get()
        out_dir = self.main_app.out_dir_var.get()

        if not extra_args.get("r1"):
            self.main_app.show_error("Missing Required Input", "FASTQ R1 is required.")
            return
        if not ref_fasta:
            self.main_app.show_error(
                "Missing Required Input", "Reference Genome FASTA is required."
            )
            return

        cmd = [
            sys.executable,
            "-m",
            "wgsextract_cli.main",
            "pet-align",
            "--r1",
            extra_args["r1"],
            "--species",
            extra_args["pet_type"].lower(),
            "--format",
            extra_args["format"],
            "--ref",
            ref_fasta,
        ]
        if extra_args.get("r2"):
            cmd.extend(["--r2", extra_args["r2"]])
        if out_dir:
            cmd.extend(["--outdir", out_dir])

        label = "Pet Analysis"
        btn = frame.cmd_buttons.get("pet-align")
        if btn:
            label = btn.cget("text")

        self.run_cmd(cmd, cmd_key="pet-align", frame=frame, label=label)

    def run_dispatch(self, cmd: str, frame: Any, label: str | None = None) -> None:
        """
        Maps UI button commands to actual CLI operations.

        Args:
            cmd: The command identifier from UI_METADATA.
            frame: The frame from which the command was triggered.
            label: Display label for the log tab.
        """
        bc = [sys.executable, "-m", "wgsextract_cli.main"]

        # Extract typed fields
        bam_path = getattr(frame, "bam_entry", None)
        bam_val = bam_path.get() if bam_path else ""

        vcf_path = getattr(frame, "vcf_entry", None)
        vcf_val = vcf_path.get() if vcf_path else ""

        fastq_path = getattr(frame, "fastq_entry", None)
        fastq_r1_path = getattr(frame, "align_r1", None)
        fastq_val = (
            fastq_path.get()
            if fastq_path
            else (fastq_r1_path.get() if fastq_r1_path else "")
        )

        ref_path = getattr(frame, "ref_entry", None)
        ref_val = ref_path.get() if ref_path else ""

        # Validate inputs before proceeding
        if not self._validate_inputs(
            cmd,
            frame,
            bam_val=bam_val,
            vcf_val=vcf_val,
            fastq_val=fastq_val,
            ref_val=ref_val,
        ):
            return

        if cmd == "vep-download":
            self.run_vep_download(frame)
            return

        if cmd == "ref-gene-map":
            self.run_gene_map_op(frame)
            return

        if cmd == "info":
            self.run_info_detailed(bam_val, ref_val, frame=frame)

        elif cmd == "clear-cache":
            self.run_clear_cache(bam_val, frame)

        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c = bc + ["info", cmd, "--input", bam_val]
            region = getattr(frame, "region_entry", None)
            if region and region.get():
                c.extend(["-r", region.get()])
            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

        elif cmd == "align":
            c = bc + ["align", "--r1", frame.align_r1.get(), "--ref", ref_val]
            if hasattr(frame, "align_r2") and frame.align_r2.get():
                c.extend(["--r2", frame.align_r2.get()])

            # Use output format if provided
            fmt_var = getattr(frame, "output_format_var", None)
            if fmt_var:
                c.extend(["--format", fmt_var.get()])

            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

        elif cmd in [
            "sort",
            "index",
            "unindex",
            "unsort",
            "to-cram",
            "to-bam",
            "unalign",
            "identify",
        ]:
            c = bc + ["bam", cmd, "--input", bam_val]
            if ref_val:
                c.extend(["--ref", ref_val])

            out_dir = self.main_app.out_dir_var.get()
            if out_dir:
                c.extend(["--outdir", out_dir])

            if cmd == "unalign":
                # unalign requires --r1 and --r2 output paths
                base = os.path.basename(bam_val).split(".")[0]
                effective_out = out_dir if out_dir else os.path.dirname(bam_val)
                r1 = os.path.join(effective_out, f"{base}_R1.fastq.gz")
                r2 = os.path.join(effective_out, f"{base}_R2.fastq.gz")
                c.extend(["--r1", r1, "--r2", r2])

            if cmd == "to-cram":
                cram_ver = getattr(frame, "cram_version_var", None)
                if cram_ver:
                    c.extend(["--cram-version", cram_ver.get()])

            region = getattr(frame, "region_entry", None)
            if (
                region
                and region.get()
                and cmd in ["sort", "to-cram", "to-bam", "unalign"]
            ):
                c.extend(["-r", region.get()])

            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

        elif cmd.startswith("repair-"):
            # Repair FTDNA VCF takes VCF input, others take BAM
            input_to_use = vcf_val if cmd == "repair-ftdna-vcf" else bam_val
            self.run_cmd(
                bc + ["repair", cmd.replace("repair-", ""), "--input", input_to_use],
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd in [
            "mito",
            "ydna",
            "unmapped",
            "custom",
            "mito-fasta",
            "mito-vcf",
            "mt-bam",
            "bam-subset",
            "ydna-bam",
            "ydna-vcf",
            "y-mt-extract",
        ]:
            c = bc + ["extract"]
            sub = (
                "mito-fasta" if cmd == "mito" else "ydna-bam" if cmd == "ydna" else cmd
            )
            c.extend([sub, "--input", bam_val])

            region = getattr(frame, "region_entry", None)
            if region and region.get() and cmd in ["custom", "bam-subset"]:
                c.extend(["-r", region.get()])

            if cmd == "bam-subset":
                extra = getattr(frame, "extra_entry", None)
                if extra and extra.get():
                    val = extra.get()
                    if val.replace(".", "").isdigit():
                        c.extend(["-f", val])
                    else:
                        c.append(val)

            out_dir = getattr(frame, "out_dir", None)
            if out_dir and out_dir.get():
                c.extend(["--outdir", out_dir.get()])
            elif self.main_app.out_dir_var.get():
                c.extend(["--outdir", self.main_app.out_dir_var.get()])

            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

        elif cmd in [
            "snp",
            "indel",
            "sv",
            "cnv",
            "freebayes",
            "gatk",
            "deepvariant",
            "annotate",
            "spliceai",
            "alphamissense",
            "pharmgkb",
            "filter",
            "trio",
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
                label=label,
            )

        elif cmd == "microarray":
            sel = [fid for fid, v in frame.micro_formats_vars.items() if v.get()]
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
                label=label,
            )

        elif cmd == "lineage-y-haplogroup":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "y-haplogroup",
                    "--input",
                    bam_val,
                    "--yleaf-path",
                    frame.yleaf_path.get(),
                    "--pos-file",
                    frame.yleaf_pos.get(),
                ],
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd == "lineage-mt-haplogroup":
            self.run_cmd(
                bc
                + [
                    "lineage",
                    "mt-haplogroup",
                    "--input",
                    bam_val,
                    "--haplogrep-path",
                    frame.haplogrep_path.get(),
                ],
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd == "fastp":
            c = bc + ["qc", "fastp", "--r1", fastq_val]
            fastq_r2 = getattr(frame, "align_r2", None)
            if fastq_r2 and fastq_r2.get():
                c.extend(["--r2", fastq_r2.get()])
            self.run_cmd(
                c,
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd == "fastqc":
            self.run_cmd(
                bc + ["qc", "fastqc", "--input", fastq_val or bam_val],
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd == "vcf-qc":
            self.run_cmd(
                bc + ["qc", "vcf", "--input", vcf_val or bam_val],
                cmd_key=cmd,
                frame=frame,
                label=label,
            )

        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c = bc + ["ref", sub]
            if sub not in ["download", "download-genes"] and ref_val:
                c += ["--ref", ref_val]
            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

    def _dispatch_vcf_vep(
        self,
        cmd: str,
        sub_cmd: str,
        frame: Any,
        bam_val: str,
        vcf_val: str,
        ref_val: str,
        bc: list[str],
        label: str | None = None,
    ) -> None:
        """Helper to handle VCF and VEP command dispatching."""
        sub = cmd.replace("vep-", "") if "vep-" in cmd else cmd
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
            # Annotate, Filter use VCF
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
            if self.main_app.vcf_exclude_gaps_var.get():
                c.append("--exclude-near-gaps")
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

        if cmd == "vcf-qc":
            # Handle caching and opening stats window
            outdir = self.main_app.out_dir_var.get()
            if not outdir:
                outdir = os.path.dirname(os.path.abspath(vcf_val))

            base_name = os.path.basename(vcf_val)
            out_stats = os.path.join(outdir, f"{base_name}.vcfstats.txt")

            def open_stats() -> None:
                if os.path.exists(out_stats):
                    try:
                        with open(out_stats, encoding="utf-8") as f:
                            content = f.read()
                        self.main_app.show_info_window(
                            f"VCF Stats: {base_name}", content
                        )
                    except Exception as e:
                        self.main_app.log(f"❌: Failed to read stats file: {e}")

            if os.path.exists(out_stats):
                self.main_app.log(f"ℹ️: Using cached VCF stats: {out_stats}")
                open_stats()
                return

            self.run_cmd(c, cmd_key=cmd, frame=frame, on_finish=open_stats, label=label)
        else:
            self.run_cmd(c, cmd_key=cmd, frame=frame, label=label)

    def _validate_inputs(self, cmd: str, frame: Any, **vals: str) -> bool:
        """
        Check if required input variables for a command are set.
        Shows an alert and returns False if any are missing.
        """
        bam_val = vals.get("bam_val", "")
        vcf_val = vals.get("vcf_val", "")
        fastq_val = vals.get("fastq_val", "")
        ref_val = vals.get("ref_val", "")

        errors = []

        # Category-based validation
        bam_cmds = [
            "info",
            "clear-cache",
            "calculate-coverage",
            "coverage-sample",
            "sort",
            "index",
            "unindex",
            "unsort",
            "to-cram",
            "to-bam",
            "unalign",
            "bam-subset",
            "mt-bam",
            "mito-fasta",
            "mito-vcf",
            "ydna-bam",
            "ydna-vcf",
            "y-mt-extract",
            "repair-ftdna-bam",
            "mito",
            "ydna",
            "unmapped",
            "custom",
            "snp",
            "indel",
            "sv",
            "cnv",
            "freebayes",
            "gatk",
            "deepvariant",
            "microarray",
            "lineage-y-haplogroup",
            "lineage-mt-haplogroup",
        ]

        vcf_cmds = [
            "repair-ftdna-vcf",
            "annotate",
            "spliceai",
            "alphamissense",
            "pharmgkb",
            "filter",
            "trio",
            "vcf-qc",
        ]

        ref_cmds = [
            "align",
            "microarray",
            "ref-index",
            "ref-verify",
            "ref-count-ns",
            "vep-verify",
        ]

        # Use exact names from labels
        bam_label = GUI_LABELS["bam_cram"] if frame.key != "micro" else "BAM/CRAM Input"
        vcf_label = GUI_LABELS["vcf_input"]

        if cmd in bam_cmds and not bam_val:
            errors.append(GUI_MESSAGES["error_input_required"].format(field=bam_label))

        if cmd in vcf_cmds and not vcf_val:
            errors.append(GUI_MESSAGES["error_input_required"].format(field=vcf_label))

        if cmd in ref_cmds and not ref_val:
            errors.append(
                GUI_MESSAGES["error_input_required"].format(field="Reference")
            )

        # Specific command validation
        if cmd == "align":
            if not getattr(frame, "align_r1", None) or not frame.align_r1.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["fastq_r1"]
                    )
                )

        if cmd == "trio":
            if not getattr(frame, "vcf_mother", None) or not frame.vcf_mother.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["mother_vcf"]
                    )
                )
            if not getattr(frame, "vcf_father", None) or not frame.vcf_father.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["father_vcf"]
                    )
                )

        if cmd == "lineage-y-haplogroup":
            if not getattr(frame, "yleaf_path", None) or not frame.yleaf_path.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["yleaf_path"]
                    )
                )
            if not getattr(frame, "yleaf_pos", None) or not frame.yleaf_pos.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["pos_file"]
                    )
                )

        if cmd == "lineage-mt-haplogroup":
            if (
                not getattr(frame, "haplogrep_path", None)
                or not frame.haplogrep_path.get()
            ):
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["haplogrep_path"]
                    )
                )

        if cmd == "fastp":
            if not fastq_val:
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["fastq_qc"]
                    )
                )
        elif cmd == "fastqc":
            if not bam_val and not fastq_val:
                errors.append(GUI_MESSAGES["error_bam_fastq_required"])
            elif not fastq_val and bam_val.lower().endswith(".cram"):
                # FastQC technically supports BAM but often fails on CRAM
                # unless specifically configured with samtools in path.
                # However, it's safer to unalign first.
                errors.append(
                    "FastQC does not support CRAM files. Please unalign to FASTQ first."
                )

        if cmd == "vep-run":
            if not bam_val and not vcf_val:
                errors.append(GUI_MESSAGES["error_bam_vcf_required"])

        if cmd == "annotate":
            if not getattr(frame, "vcf_ann_vcf", None) or not frame.vcf_ann_vcf.get():
                errors.append(
                    GUI_MESSAGES["error_input_required"].format(
                        field=GUI_LABELS["annotate_vcf"]
                    )
                )

        if cmd == "filter":
            # Check if at least one filter criterion is provided
            f_expr = (
                frame.vcf_filter_expr.get()
                if hasattr(frame, "vcf_filter_expr")
                else None
            )
            f_gene = frame.vcf_gene.get() if hasattr(frame, "vcf_gene") else None
            f_reg = frame.vcf_region.get() if hasattr(frame, "vcf_region") else None
            if not any([f_expr, f_gene, f_reg]):
                errors.append(GUI_MESSAGES["error_filter_crit_required"])

        if cmd == "microarray":
            # Access BooleanVars directly from frame
            sel = [fid for fid, v in frame.micro_formats_vars.items() if v.get()]
            if not sel:
                errors.append(GUI_MESSAGES["error_target_fmt_required"])

        if errors:
            self.main_app.show_error(
                GUI_MESSAGES["error_missing_input"], "\n".join(errors)
            )
            return False

        return True
