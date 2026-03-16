"""General tab frame for the Web GUI."""

import asyncio

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import info_display, run_generic_cmd, ui_row_dir, ui_row_input
from .controller import controller
from .state import state


def frame_gen():
    ui.label(UI_METADATA["gen"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["gen"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input(
            GUI_LABELS["bam_cram"], "bam_path", info_text=GUI_TOOLTIPS["bam_input_tip"]
        )
        ui_row_dir(
            GUI_LABELS["ref_library_path"],
            "ref_path",
            info_text="Path to the directory containing your reference genomes.",
        )
        ui_row_dir(
            GUI_LABELS["out_dir"], "out_dir", info_text=GUI_TOOLTIPS["out_dir_tip"]
        )

    # CRAM Version selector
    with ui.row().classes("w-full items-center px-2 gap-4"):
        with ui.row().classes("items-center gap-1 w-40"):
            ui.label("CRAM Version:").classes("font-bold text-sm")
            with ui.icon("info", size="xs").classes("text-blue-400 cursor-help"):
                from .common import add_tooltip

                add_tooltip(
                    "Select CRAM version for to-cram conversion. 3.0 is recommended for GATK compatibility."
                )

        ui.select(["2.1", "3.0", "3.1"]).bind_value(state, "cram_version").classes(
            "w-24"
        ).props("outlined dense")

    # Info Display Area
    info_display()

    # File state for dynamic button visibility
    fstats = controller.info_data.get("file_stats", {})
    is_sorted = fstats.get("sorted", False)
    is_indexed = fstats.get("indexed", False)
    is_cram = state.bam_path.lower().endswith(".cram")

    # Operations
    with ui.expansion("Operations", icon="settings", value=True).classes(
        "w-full mt-4 border border-slate-700 rounded-lg"
    ):
        with ui.column().classes("w-full p-4 gap-4"):
            # Info commands
            with ui.row().classes("w-full gap-2"):
                for cmd in UI_METADATA["gen"]["info_commands"]:
                    if cmd["cmd"] == "info":
                        ui.button(
                            cmd["label"],
                            on_click=lambda: asyncio.create_task(
                                controller.get_info_fast(state.bam_path, detailed=True)
                            ),
                        ).props("color=primary")
                    else:
                        ui.button(
                            cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                        ).props("outline")

            ui.separator()

            # BAM commands
            with ui.row().classes("w-full gap-2"):
                visibility_map = {
                    "sort": not is_sorted,
                    "unsort": is_sorted,
                    "index": is_sorted and not is_indexed,
                    "unindex": is_indexed,
                    "to-cram": not is_cram,
                    "to-bam": is_cram,
                    "repair-ftdna-bam": True,
                }

                for cmd in UI_METADATA["gen"]["bam_commands"]:
                    if visibility_map.get(cmd["cmd"], True):
                        ui.button(
                            cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                        ).props("outline color=orange")
