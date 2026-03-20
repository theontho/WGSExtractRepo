"""Shared UI components and helpers for the Web GUI."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from nicegui import events, ui

from wgsextract_cli.core.messages import GUI_TOOLTIPS

from .controller import controller
from .state import state

# Global callback to refresh the main content
_render_content_refresh_cb = None


def set_render_content_refresh_cb(cb):
    global _render_content_refresh_cb
    _render_content_refresh_cb = cb


def render_content_refresh():
    if _render_content_refresh_cb:
        _render_content_refresh_cb()


class LocalFilePicker(ui.dialog):
    def __init__(
        self,
        directory: str | Path,
        *,
        upper_limit: str | Path | None = None,
        multiple: bool = False,
        show_hidden_files: bool = False,
    ) -> None:
        super().__init__()
        self.path = Path(directory).expanduser()
        if upper_limit is None:
            self.upper_limit = None
        else:
            self.upper_limit = Path(upper_limit).expanduser()
        self.show_hidden_files = show_hidden_files
        self.multiple = multiple

        with self, ui.card():
            self.add_header()
            self.grid = (
                ui.aggrid(
                    {
                        "columnDefs": [
                            {"field": "name", "headerName": "File Name"},
                            {"field": "size", "headerName": "Size"},
                            {"field": "type", "headerName": "Type"},
                        ],
                        "rowSelection": "multiple" if multiple else "single",
                    },
                    html_columns=[0],
                )
                .classes("w-[600px] h-[400px]")
                .on("cellDoubleClicked", self.handle_double_click)
            )
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=self.close).props("outline")
                ui.button("Ok", on_click=self._handle_ok)
        self.update_grid()

    def add_header(self) -> None:
        with ui.row().classes("w-full items-center justify-between"):
            ui.label(str(self.path)).classes("text-lg font-bold truncate flex-grow")
            with ui.row():
                ui.button(icon="arrow_upward", on_click=self.path_up).props("flat")
                ui.button(icon="refresh", on_click=self.update_grid).props("flat")

    def path_up(self) -> None:
        if self.upper_limit and self.path <= self.upper_limit:
            return
        self.path = self.path.parent
        self.update_grid()

    def update_grid(self) -> None:
        paths = list(self.path.glob("*"))
        if not self.show_hidden_files:
            paths = [p for p in paths if not p.name.startswith(".")]
        paths.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

        rows = []
        for p in paths:
            rows.append(
                {
                    "name": f"📁 {p.name}" if p.is_dir() else f"📄 {p.name}",
                    "size": f"{p.stat().st_size:,} bytes" if p.is_file() else "",
                    "type": "Dir" if p.is_dir() else "File",
                    "path": str(p),
                }
            )
        self.grid.options["rowData"] = rows
        self.grid.update()

    async def handle_double_click(self, e: events.GenericEventArguments) -> None:
        path = Path(e.args["data"]["path"])
        if path.is_dir():
            self.path = path
            self.update_grid()
        else:
            self.submit([str(path)] if self.multiple else str(path))

    async def _handle_ok(self):
        selected = await self.grid.get_selected_rows()
        if not selected:
            return
        res = [s["path"] for s in selected]
        self.submit(res if self.multiple else res[0])


def add_tooltip(text: str):
    """Add a tooltip to the preceding element."""
    with ui.tooltip().classes("bg-slate-800 text-white text-xs p-2"):
        ui.label(text)


async def save_env():
    """Save current state to .env.local file."""
    cli_root = Path(__file__).parent.parent.parent.parent.parent
    env_path = cli_root / ".env.local"

    content = [
        f'WGSE_INPUT="{state.bam_path}"',
        f'WGSE_INPUT_VCF="{state.vcf_path}"',
        f'WGSE_MOTHER_VCF="{state.vcf_mother}"',
        f'WGSE_FATHER_VCF="{state.vcf_father}"',
        f'WGSE_REF="{state.ref_path}"',
        f'WGSE_OUTDIR="{state.out_dir}"',
        f'WGSE_YLEAF_PATH="{state.yleaf_path}"',
        f'WGSE_HAPLOGREP_PATH="{state.haplogrep_path}"',
        f'WGSE_VEP_CACHE="{state.vep_cache_path}"',
    ]

    try:
        with open(env_path, "w") as f:
            f.write("\n".join(content) + "\n")
        ui.notify("Settings saved to .env.local", type="positive")
    except Exception as e:
        ui.notify(f"Failed to save settings: {e}", type="negative")


def ui_row_input(
    label: str, value_attr: str, placeholder: str = "", info_text: str | None = None
):
    """Helper to create a row with a label, input, and file picker button."""
    with ui.row().classes("w-full items-center gap-4 px-2"):
        with ui.row().classes("items-center gap-1 w-40"):
            ui.label(label).classes("font-bold text-sm")
            if info_text:
                icon = ui.icon("info", size="xs").classes("text-blue-400 cursor-help")
                with icon:
                    add_tooltip(info_text)

        input_widget = (
            ui.input(placeholder=placeholder)
            .bind_value(state, value_attr)
            .classes("flex-grow")
            .props("outlined dense")
        )

        async def pick_file_action():
            start_dir = getattr(state, value_attr) or os.getcwd()
            if not os.path.isdir(start_dir):
                start_dir = os.path.dirname(start_dir) if start_dir else os.getcwd()

            picker = LocalFilePicker(start_dir)
            result = await picker
            if result:
                setattr(state, value_attr, result)
                if value_attr == "bam_path":
                    asyncio.create_task(controller.get_info_fast(result))

        ui.button(icon="folder", on_click=pick_file_action).props("flat dense")
    return input_widget


def ui_row_dir(
    label: str, value_attr: str, placeholder: str = "", info_text: str | None = None
):
    """Helper to create a row with a label, input, and directory picker button."""
    with ui.row().classes("w-full items-center gap-4 px-2"):
        with ui.row().classes("items-center gap-1 w-40"):
            ui.label(label).classes("font-bold text-sm")
            if info_text:
                icon = ui.icon("info", size="xs").classes("text-blue-400 cursor-help")
                with icon:
                    add_tooltip(info_text)

        ui.input(placeholder=placeholder).bind_value(state, value_attr).classes(
            "flex-grow"
        ).props("outlined dense")

        async def pick_dir_action():
            val = getattr(state, value_attr) or os.getcwd()
            start_dir = val if os.path.isdir(val) else os.getcwd()
            picker = LocalFilePicker(start_dir)
            result = await picker
            if result:
                setattr(state, value_attr, result)

        ui.button(icon="folder_open", on_click=pick_dir_action).props("flat dense")


def info_display():
    """Renders the BAM/CRAM info display similar to the Python GUI."""
    if not controller.info_data:
        return

    data = controller.info_data
    with ui.card().classes("w-full bg-slate-800 p-4 gap-4"):
        with ui.row().classes("w-full justify-between items-center"):
            ui.label("Sample Information").classes("text-lg font-bold")
            if data.get("md5_signature"):
                ui.label(f"MD5: {data['md5_signature'][:8]}...").classes(
                    "text-xs text-slate-400"
                )

        with ui.grid(columns=2).classes("w-full gap-x-8 gap-y-2"):
            # Basic Info
            fstats = data.get("file_stats", {})
            size_gb = fstats.get("size_gb", 0)
            size_str = (
                f"{size_gb:.1f} GB" if isinstance(size_gb, int | float) else "0.0 GB"
            )

            with ui.column().classes("gap-1"):
                ui.label("Reference Model").classes("text-xs text-slate-400 uppercase")
                ui.label(data.get("ref_model_str", "Unknown")).classes("font-mono")

            with ui.column().classes("gap-1"):
                ui.label("File Stats").classes("text-xs text-slate-400 uppercase")
                ui.label(
                    f"{'Sorted' if fstats.get('sorted') else 'Unsorted'}, {'Indexed' if fstats.get('indexed') else 'Unindexed'}, {size_str}"
                ).classes("font-mono")

            # Detailed Basic Info (if available)
            if data.get("gender"):
                with ui.column().classes("gap-1"):
                    ui.label("Predicted Gender").classes(
                        "text-xs text-slate-400 uppercase"
                    )
                    ui.label(data["gender"]).classes("font-mono")

            if data.get("file_content"):
                with ui.column().classes("gap-1"):
                    ui.label("File Content").classes("text-xs text-slate-400 uppercase")
                    ui.label(data["file_content"]).classes("font-mono")

            read_len_val = data.get("avg_read_len", 0)
            if read_len_val:
                with ui.column().classes("gap-1"):
                    ui.label("Read Length").classes("text-xs text-slate-400 uppercase")
                    ui.label(f"{read_len_val:.0f} bp").classes("font-mono")

            if data.get("sequencer"):
                with ui.column().classes("gap-1"):
                    ui.label("Sequencer").classes("text-xs text-slate-400 uppercase")
                    ui.label(data["sequencer"]).classes("font-mono")

        # Metrics (Mapped vs Raw)
        metrics = data.get("metrics")
        if metrics:
            ui.separator().classes("my-2")
            ui.label("Alignment Metrics").classes("text-md font-bold text-blue-300")
            with ui.grid(columns=3).classes("w-full gap-4"):
                with ui.column():
                    ui.label("Metric").classes("text-xs font-bold text-slate-500")
                    ui.label("Mapped").classes("text-sm")
                    ui.label("Raw").classes("text-sm")

                with ui.column():
                    ui.label("Read Depth").classes("text-xs font-bold text-slate-500")
                    ui.label(f"{metrics.get('ard_mapped', 0):.1f} x").classes(
                        "font-mono"
                    )
                    ui.label(f"{metrics.get('ard_raw', 0):.1f} x").classes("font-mono")

                with ui.column():
                    ui.label("Gigabases").classes("text-xs font-bold text-slate-500")
                    ui.label(f"{metrics.get('gbases_mapped', 0):.2f} G").classes(
                        "font-mono"
                    )
                    ui.label(f"{metrics.get('gbases_raw', 0):.2f} G").classes(
                        "font-mono"
                    )

        # Chromosome Table
        if data.get("chrom_table_csv"):
            import csv
            import io

            ui.separator().classes("my-2")
            ui.label("Chromosome Statistics").classes(
                "text-md font-bold text-green-300"
            )
            si = io.StringIO(data["chrom_table_csv"])
            reader = csv.DictReader(si)
            rows = list(reader)

            ui.aggrid(
                {
                    "columnDefs": [
                        {"field": "Seq Name", "headerName": "Chrom", "width": 100},
                        {"field": "Model Len", "headerName": "Length", "width": 120},
                        {
                            "field": "Model N Len",
                            "headerName": "N Bases",
                            "width": 100,
                        },
                        {
                            "field": "# Segs Map",
                            "headerName": "Mapped Reads",
                            "width": 120,
                        },
                        {"field": "Map Gbases", "headerName": "Gbases", "width": 100},
                        {"field": "Map ARD", "headerName": "Depth", "width": 80},
                        {
                            "field": "Breadth Coverage",
                            "headerName": "Coverage",
                            "width": 100,
                        },
                    ],
                    "rowData": rows,
                    "rowHeight": 30,
                }
            ).classes("w-full h-80 text-xs")


def log_area():
    with ui.card().classes("w-full mt-4 p-0 bg-slate-900 border border-slate-700"):
        with ui.tabs().bind_value(state, "current_log_tab") as tabs:
            for tab in state.log_tabs:
                ui.tab(tab)

        with ui.tab_panels(tabs, value="Main").classes("w-full bg-transparent"):
            for tab in state.log_tabs:
                with ui.tab_panel(tab):
                    log_widget = ui.log(max_lines=1000).classes(
                        "w-full h-96 font-mono text-xs bg-black text-green-400 p-2"
                    )
                    for line in state.logs.get(tab, []):
                        log_widget.push(line)
                    if tab == state.current_log_tab:
                        controller.main_log = log_widget


def run_generic_cmd(cmd_meta: dict[str, Any]):
    bc = [sys.executable, "-m", "wgsextract_cli.main"]
    cmd = cmd_meta["cmd"]

    # Input mapping
    input_path = state.bam_path
    if cmd in ["annotate", "filter", "vcf-qc", "repair-ftdna-vcf", "vep-run"]:
        input_path = state.vcf_path
    elif cmd in ["align", "fastqc", "fastp"]:
        input_path = state.fastq_path or state.bam_path

    # Command mapping
    if cmd in [
        "sort",
        "index",
        "unindex",
        "unsort",
        "to-cram",
        "to-bam",
        "repair-ftdna-bam",
        "identify",
    ]:
        command = bc + ["bam", cmd, "--input", input_path]
        if cmd == "to-cram" and state.cram_version:
            command.extend(["--cram-version", state.cram_version])
    elif cmd in [
        "mito-fasta",
        "mt-bam",
        "mito-vcf",
        "ydna-bam",
        "ydna-vcf",
        "y-mt-extract",
        "unmapped",
        "custom",
        "bam-subset",
    ]:
        command = bc + ["extract", cmd, "--input", input_path]
        if cmd == "custom" and state.extract_region:
            command.extend(["--region", state.extract_region])
        if cmd == "bam-subset" and state.extract_region:
            command.extend(["--region", state.extract_region])
        if cmd == "bam-subset" and state.extract_extra:
            # For bam-subset, the 'extra' is the fraction
            val = state.extract_extra
            if val.replace(".", "").isdigit():
                command.extend(["--fraction", val])
            else:
                command.append(val)
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
        "vcf-qc",
        "repair-ftdna-vcf",
        "trio",
        "vep-run",
    ]:
        command = bc + ["vcf", cmd, "--input", input_path]
        if state.vcf_exclude_gaps:
            command.append("--exclude-gaps")
        if cmd == "annotate" and state.vcf_ann_vcf:
            command.extend(["--ann-vcf", state.vcf_ann_vcf])
        if cmd == "filter":
            if state.vcf_filter_expr:
                command.extend(["--filter-expr", state.vcf_filter_expr])
            if state.vcf_gene:
                command.extend(["--gene", state.vcf_gene])
            if state.vcf_region:
                command.extend(["--region", state.vcf_region])
        if cmd == "trio":
            if state.vcf_mother:
                command.extend(["--mother", state.vcf_mother])
            if state.vcf_father:
                command.extend(["--father", state.vcf_father])
        if cmd == "vep-run":
            if state.vep_cache_path:
                command.extend(["--vep-cache", state.vep_cache_path])
            if state.vcf_vep_args:
                command.extend(["--vep-args", state.vcf_vep_args])
            if state.vcf_region:
                command.extend(["--region", state.vcf_region])
    elif cmd == "microarray":
        command = bc + ["microarray", "--input", input_path, "--ref", state.ref_path]
    elif cmd == "lineage-y-haplogroup":
        command = bc + [
            "lineage",
            "y-haplogroup",
            "--input",
            input_path,
            "--yleaf-path",
            state.yleaf_path,
        ]
        if state.yleaf_pos:
            command.extend(["--yleaf-pos", state.yleaf_pos])
    elif cmd == "lineage-mt-haplogroup":
        command = bc + [
            "lineage",
            "mt-haplogroup",
            "--input",
            input_path,
            "--haplogrep-path",
            state.haplogrep_path,
        ]
    elif cmd == "align":
        command = bc + ["align", "--r1", state.fastq_path, "--ref", state.ref_path]
    elif cmd == "pet-align":
        pet_type = "Dog" if "Dog" in state.pet_species else "Cat"
        command = bc + [
            "pet-align",
            "--species",
            pet_type.lower(),
            "--r1",
            state.pet_fastq_r1,
            "--r2",
            state.pet_fastq_r2,
            "--ref",
            state.pet_ref_fasta,
            "--format",
            state.pet_output_format.upper(),
        ]
    elif cmd == "clear-cache":
        out_dir = state.out_dir or os.path.dirname(os.path.abspath(input_path))
        json_cache = os.path.join(
            out_dir, f"{os.path.basename(input_path)}.wgse_info.json"
        )
        if os.path.exists(json_cache):
            os.remove(json_cache)
            ui.notify(f"Cleared info cache for {os.path.basename(input_path)}")
            controller.info_data = {}
            from .common import render_content_refresh

            render_content_refresh()
        else:
            ui.notify("No cache file found to clear.")
        return
    elif cmd == "calculate-coverage":
        command = bc + ["bam", "calculate-coverage", "--input", input_path]
    elif cmd == "coverage-sample":
        command = bc + ["bam", "coverage-sample", "--input", input_path]
    elif cmd == "unalign":
        command = bc + ["bam", "unalign", "--input", input_path]
    elif cmd == "fastqc":
        command = bc + ["qc", "fastqc", "--input", input_path]
    elif cmd == "fastp":
        command = bc + ["qc", "fastp", "--input", input_path]
    elif cmd == "ref-gene-map":
        command = bc + ["ref", "gene-map"]
    elif cmd == "vep-verify":
        command = bc + ["vep", "--verify-only", "--vep-cache", state.vep_cache_path]
    elif cmd == "vcf-qc":
        command = bc + ["qc", "vcf", "--input", input_path]
    else:
        ui.notify(f"Command {cmd} dispatch not fully implemented", type="warning")
        return

    # Add global flags
    if (
        state.ref_path
        and "--ref" not in command
        and cmd not in ["repair-ftdna-bam", "repair-ftdna-vcf", "fastqc", "fastp"]
    ):
        command.extend(["--ref", state.ref_path])
    if state.out_dir:
        command.extend(["--outdir", state.out_dir])

    asyncio.create_task(
        controller.run_cmd(command, label=cmd_meta["label"], cmd_key=cmd)
    )


def ui_command_button(cmd_meta: dict[str, Any]):
    """Helper to create a command button with tooltip."""
    btn = ui.button(cmd_meta["label"], on_click=lambda: run_generic_cmd(cmd_meta))
    with btn:
        add_tooltip(GUI_TOOLTIPS.get(cmd_meta["cmd"], ""))
    return btn
