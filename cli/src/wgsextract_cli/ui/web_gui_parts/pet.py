"""Pet tab frame for the Web GUI."""

import os

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_dir, ui_row_input
from .state import state


def frame_pet():
    ui.label(UI_METADATA["pet"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["pet"]["help"]).classes("text-slate-400 mb-4")

    from wgsextract_cli.core.help_texts import ABOUT_PET_SEQUENCING
    from wgsextract_cli.core.ref_library import get_genome_status, get_grouped_genomes

    def show_about():
        with ui.dialog() as dialog, ui.card():
            ui.label("About Pet Sequencing").classes("text-h6")
            ui.markdown(ABOUT_PET_SEQUENCING)
            ui.button("Close", on_click=dialog.close)
        dialog.open()

    with ui.row().classes("w-full mb-4"):
        ui.button(GUI_LABELS["about_pet_seq"], icon="info", on_click=show_about).props(
            "outline"
        )

    with ui.column().classes("w-full gap-2 mb-4"):
        # Species selection
        groups = get_grouped_genomes()
        pet_options = ["Select Pet Species..."]
        pet_map = {}
        for g in groups:
            if "Dog" in g["label"] or "Cat" in g["label"]:
                status = get_genome_status(g["final"], state.ref_path)
                status_str = "[Installed]" if status == "installed" else "[Missing]"
                label = f"{g['label']} {status_str}"
                pet_options.append(label)
                pet_map[label] = g

        def on_species_change(e):
            if e.value in pet_map:
                g = pet_map[e.value]
                path = os.path.join(state.ref_path, "genomes", g["final"])
                state.pet_ref_fasta = path

        ui.select(
            pet_options, label=GUI_LABELS["pet_species"], on_change=on_species_change
        ).bind_value(state, "pet_species").classes("w-full").props("outlined dense")
        # Add tooltip to the select
        with ui.tooltip():
            ui.label(GUI_TOOLTIPS["pet_species_tip"])

        ui_row_input(
            GUI_LABELS["ref_fasta_path"], "pet_ref_fasta", info_text=GUI_TOOLTIPS["ref"]
        )
        ui_row_dir(
            GUI_LABELS["out_dir"], "out_dir", info_text=GUI_TOOLTIPS["out_dir_tip"]
        )
        ui_row_input(
            GUI_LABELS["fastq_r1"], "pet_fastq_r1", info_text=GUI_TOOLTIPS["pet_r1_tip"]
        )
        ui_row_input(
            GUI_LABELS["fastq_r2"], "pet_fastq_r2", info_text=GUI_TOOLTIPS["pet_r2_tip"]
        )

        ui.select(["BAM", "CRAM"], label=GUI_LABELS["output_format"]).bind_value(
            state, "pet_output_format"
        ).classes("w-full").props("outlined dense")
        with ui.tooltip():
            ui.label(GUI_TOOLTIPS["output_fmt_tip"])

    with ui.expansion("Pet Operations", icon="pets", value=True).classes(
        "w-full border border-slate-700 rounded-lg"
    ):
        with ui.row().classes("w-full gap-2 p-4"):
            for cmd in UI_METADATA["pet"]["commands"]:
                ui.button(
                    cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                ).props("outline")
