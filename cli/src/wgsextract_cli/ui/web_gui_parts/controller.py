"""Main controller for the Web GUI."""

import asyncio
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
from typing import Any

from nicegui import ui

from wgsextract_cli.core.utils import proc_registry

from .state import state


class WebController:
    """Handles command execution and logic for the Web GUI."""

    def __init__(self) -> None:
        """Initialize the controller."""
        self.active_processes: dict[str, subprocess.Popen | threading.Event] = {}
        self.active_downloads: dict[str, dict[str, Any]] = {}
        self.info_data: dict[str, Any] = {}
        self.main_log: Any = None

    def log(self, message: str, tab: str = "Main"):
        """Add a message to the specified log tab with level detection."""
        if not message.strip():
            return

        upper_msg = message.upper()
        emoji = "ℹ️"

        if any(kw in upper_msg for kw in ["ERROR", "EXCEPTION", "FATAL"]):
            emoji = "❌"
        elif any(kw in upper_msg for kw in ["WARN", "WARNING"]):
            emoji = "⚠️"
        elif any(
            kw in upper_msg
            for kw in [
                "DEBUG",
                "RUNNING:",
                "IDENTIFIED:",
                "SUGGESTED:",
                "AUTO-DETECTED:",
            ]
        ):
            emoji = "🔍"
        elif "FINISHED" in upper_msg:
            emoji = "✅"

        formatted_msg = f"{emoji} {message.strip()}"

        if tab not in state.logs:
            state.logs[tab] = []
            state.log_tabs.append(tab)
            from .common import render_content_refresh

            render_content_refresh()

        state.logs[tab].append(formatted_msg)
        # Update the UI log if it's the current tab
        if state.current_log_tab == tab and self.main_log:
            self.main_log.push(formatted_msg)
        print(f"[{tab}] {formatted_msg}")

    async def run_cmd(
        self,
        command: list[str],
        label: str,
        cmd_key: str | None = None,
        on_finish: Callable | None = None,
    ):
        """Run a command and stream output to a new log tab."""
        tab_name = label
        if tab_name not in state.log_tabs:
            state.log_tabs.append(tab_name)
            state.logs[tab_name] = []
            ui.update()

        state.current_log_tab = tab_name
        self.log(f"Running: {' '.join(command)}", tab_name)

        try:
            # Add parent PID for automatic cleanup if GUI dies
            command.extend(["--parent-pid", str(os.getpid())])

            # Use process groups for cancellation on Unix
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setpgrp if sys.platform != "win32" else None,
            )

            if cmd_key:
                state.running_processes[cmd_key] = process
                # Cast to Any because asyncio process has slightly different type than Popen
                # but we only use it for polling/killing which works similarly.
                proc_registry.register_process(cmd_key, process)  # type: ignore

            async def read_stream(stream, prefix):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    msg = line.decode().strip()
                    if msg:
                        self.log(f"{prefix}: {msg}", tab_name)

            await asyncio.gather(
                read_stream(process.stdout, "ℹ️"),
                read_stream(process.stderr, "❌"),
            )

            return_code = await process.wait()
            self.log(f"Process finished with exit code {return_code}", tab_name)

            if cmd_key and cmd_key in state.running_processes:
                del state.running_processes[cmd_key]
                proc_registry.unregister_process(cmd_key)

            if on_finish:
                on_finish()

        except Exception as e:
            self.log(f"Error running command: {e}", tab_name)
            ui.notify(f"Error: {e}", type="negative")

    def cancel_cmd(self, cmd_key: str):
        """Cancel a running command."""
        if cmd_key in state.running_processes:
            process = state.running_processes[cmd_key]
            if sys.platform == "win32":
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), 15)  # SIGTERM
            self.log(f"Cancelled process {cmd_key}", state.current_log_tab)

    def set_tab(self, name: str):
        state.active_tab = name
        # render_content.refresh() will be called from the main GUI file or via a callback
        from .common import render_content_refresh

        render_content_refresh()
        ui.update()

    async def get_info_fast(self, input_path: str, detailed: bool = False) -> None:
        """Run the 'info' command and update the state."""
        if not input_path or not os.path.exists(input_path):
            return

        command = [
            sys.executable,
            "-m",
            "wgsextract_cli.main",
            "info",
            "--input",
            input_path,
        ]
        if detailed:
            command.append("--detailed")
        if state.ref_path:
            command.extend(["--ref", state.ref_path])
        if state.out_dir:
            command.extend(["--outdir", state.out_dir])

        # Add parent PID
        command.extend(["--parent-pid", str(os.getpid())])

        if detailed:
            # For detailed info, run via run_cmd to show progress in a log tab
            async def on_finish():
                out_dir = state.out_dir or os.path.dirname(os.path.abspath(input_path))
                json_cache = os.path.join(
                    out_dir, f"{os.path.basename(input_path)}.wgse_info.json"
                )
                if os.path.exists(json_cache):
                    with open(json_cache) as f:
                        data = json.load(f)
                    self.info_data = data
                    # Refresh UI
                    from .common import render_content_refresh

                    render_content_refresh()
                    ui.update()

            await self.run_cmd(command, label="Detailed Info", on_finish=on_finish)
        else:
            self.log(f"🔍: Triggering fast info: {' '.join(command)}")

            # Run in a separate thread to not block the loop for fast info
            def run():
                env = os.environ.copy()
                env["WGSE_SKIP_DOTENV"] = "1"
                subprocess.run(command, capture_output=True, text=True, env=env)

                # Load from json cache
                out_dir = state.out_dir or os.path.dirname(os.path.abspath(input_path))
                json_cache = os.path.join(
                    out_dir, f"{os.path.basename(input_path)}.wgse_info.json"
                )

                if os.path.exists(json_cache):
                    with open(json_cache) as f:
                        data = json.load(f)
                    self.info_data = data
                    # Refresh UI instead of reloading window
                    from .common import render_content_refresh

                    render_content_refresh()
                    ui.update()

            threading.Thread(target=run, daemon=True).start()

    # --- Library Management ---

    def run_lib_download(self, gd: dict[str, Any], restart: bool = False) -> None:
        """Launch a reference genome download in the background."""
        dest = state.ref_path
        if not dest:
            ui.notify("Reference Library Path is required.", type="negative")
            return

        fn = gd["final"]
        if fn in self.active_downloads:
            ui.notify(f"Download for {fn} is already active.")
            return

        self.log(
            f"Starting download: {gd['label']}"
        )  # Removed tab_lvl="INFO" as log method handles it
        ce = threading.Event()
        proc_registry.register_event(fn, ce)
        self.active_downloads[fn] = {"cancel": ce, "prog": 0.0, "status": "Waiting..."}

        def cb(downloaded: int, total: int, speed: float) -> None:
            pct = downloaded / total if total > 0 else 1.0
            st = (
                f"{speed / (1024 * 1024):.1f} MB/s"
                if speed > 1024 * 1024
                else f"{speed / 1024:.1f} KB/s"
            )
            self.active_downloads[fn]["prog"] = pct
            self.active_downloads[fn]["status"] = f"{pct * 100:.1f}% - {st}"

        def status_cb(msg: str):
            self.log(f"[{gd['label']}] {msg}")
            if fn in self.active_downloads:
                self.active_downloads[fn]["status"] = msg

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
                    status_callback=status_cb,
                )
                self.log(
                    f"Download {'Success' if success else 'Failed'}: {gd['label']}"
                )  # Removed tab_lvl="FINISHED"
            except Exception as e:
                self.log(
                    f"Download Error [{gd['label']}]: {e}"
                )  # Removed tab_lvl="ERROR"
            finally:
                if fn in self.active_downloads:
                    del self.active_downloads[fn]
                proc_registry.unregister_event(fn)

        threading.Thread(target=run, daemon=True).start()

    def run_vep_download(self) -> None:
        """Launch VEP cache download."""
        if not state.vep_cache_path:
            ui.notify("VEP Cache Path is required.", type="negative")
            return

        self.log("Starting VEP download...")  # Removed tab_lvl="INFO"
        ce = threading.Event()
        proc_registry.register_event("vep-download", ce)
        self.active_processes["vep-download"] = (
            ce  # Reuse dictionary for cancel signaling
        )

        def cb(downloaded: int, total: int, speed: float) -> None:
            # We could track this in state if needed for a progress bar
            pass  # Removed assignment to pct

        def run() -> None:
            from wgsextract_cli.commands.vep import cmd_vep_download

            class Args:
                vep_version = "115"
                species = "homo_sapiens"
                assembly = "GRCh38"
                mirror = "uk"
                vep_cache = state.vep_cache_path
                ref = state.ref_path
                progress_callback = cb
                cancel_event = ce

            try:
                success = cmd_vep_download(Args())
                self.log(
                    f"VEP Download {'Success' if success else 'Failed'}"
                )  # Removed tab_lvl="FINISHED"
            except Exception as e:
                self.log(f"VEP Download Error: {e}")  # Removed tab_lvl="ERROR"
            finally:
                if "vep-download" in self.active_processes:
                    del self.active_processes["vep-download"]
                proc_registry.unregister_event("vep-download")

        threading.Thread(target=run, daemon=True).start()

    def cancel_lib_download(self, fn: str) -> None:
        """Cancel an active library download."""
        if fn in self.active_downloads:
            self.log(f"Cancelling download: {fn}...")
            self.active_downloads[fn]["cancel"].set()

    def run_lib_delete(self, group: dict[str, Any]) -> None:
        """Delete a genome from the library."""
        from wgsextract_cli.core.ref_library import delete_genome

        fn = group["final"]
        if delete_genome(fn, state.ref_path):
            self.log(f"Deleted genome: {fn}")
        else:
            self.log(f"Failed to delete genome: {fn}")  # Removed tab_lvl="ERROR"

    def run_ref_index(self, group: dict[str, Any]) -> None:
        """Run samtools index on a genome."""
        final_path = os.path.join(state.ref_path, "genomes", group["final"])
        command = [
            sys.executable,
            "-m",
            "wgsextract_cli.main",
            "ref",
            "index",
            "--ref",
            final_path,
        ]
        asyncio.create_task(self.run_cmd(command, label=f"Index {group['final']}"))

    def run_ref_verify(self, group: dict[str, Any]) -> None:
        """Run reference verification."""
        final_path = os.path.join(state.ref_path, "genomes", group["final"])
        command = [
            sys.executable,
            "-m",
            "wgsextract_cli.main",
            "ref",
            "verify",
            "--ref",
            final_path,
        ]
        asyncio.create_task(self.run_cmd(command, label=f"Verify {group['final']}"))

    def run_ref_count_ns(self, group: dict[str, Any]) -> None:
        """Run N-count analysis."""
        final_path = os.path.join(state.ref_path, "genomes", group["final"])
        command = [
            sys.executable,
            "-m",
            "wgsextract_cli.main",
            "ref",
            "count-ns",
            "--ref",
            final_path,
        ]
        asyncio.create_task(self.run_cmd(command, label=f"Count-Ns {group['final']}"))


controller = WebController()
