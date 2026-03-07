"""Ancestry tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_input


def frame_anc():
    ui.label(UI_METADATA["anc"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["anc"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input(
            GUI_LABELS["bam_cram"], "bam_path", info_text=GUI_TOOLTIPS["bam_input_tip"]
        )
        ui_row_input(
            GUI_LABELS["yleaf_path"],
            "yleaf_path",
            info_text="Path to the Yleaf executable for Y-haplogroup prediction.",
        )
        ui_row_input(
            GUI_LABELS["pos_file"],
            "yleaf_pos",
            info_text="Yleaf position file (e.g., data/yleaf/pos.txt).",
        )
        ui_row_input(
            GUI_LABELS["haplogrep_path"],
            "haplogrep_path",
            info_text="Path to the Haplogrep jar or executable for mitochondrial lineage.",
        )

    with ui.expansion("Ancestry Operations", icon="groups", value=True).classes(
        "w-full border border-slate-700 rounded-lg"
    ):
        with ui.row().classes("w-full gap-2 p-4"):
            for cmd in UI_METADATA["anc"]["commands"]:
                ui.button(
                    cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                ).props("outline")
