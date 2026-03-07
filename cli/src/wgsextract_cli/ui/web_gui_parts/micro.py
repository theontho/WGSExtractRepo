"""Microarray tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_input


def frame_micro():
    ui.label(UI_METADATA["micro"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["micro"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input("BAM/CRAM Input", "bam_path")
        ui_row_input("Reference (BWA)", "ref_path")

    ui.button(
        GUI_LABELS["btn_generate_ck"],
        on_click=lambda: run_generic_cmd(UI_METADATA["micro"]["commands"][0]),
    ).props("primary").classes("w-full max-w-xs self-center")
