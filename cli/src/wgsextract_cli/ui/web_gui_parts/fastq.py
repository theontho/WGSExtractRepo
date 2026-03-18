"""FASTQ tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import ui_command_button, ui_row_dir, ui_row_input
from .state import state


def frame_fastq():
    ui.label(UI_METADATA["fastq"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["fastq"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input(
            GUI_LABELS["fastq_bam"],
            "fastq_path",
            info_text=GUI_TOOLTIPS["fastq_input_tip"],
        )
        ui_row_dir(
            GUI_LABELS["ref_library_path"],
            "ref_path",
            info_text="Path to the directory containing your reference genomes.",
        )
        ui_row_dir(
            GUI_LABELS["out_dir"], "out_dir", info_text=GUI_TOOLTIPS["out_dir_tip"]
        )

    # File state for dynamic button visibility
    is_bam = state.fastq_path.lower().endswith((".bam", ".cram"))

    # Operations exposed directly for testing and better UX
    with ui.row().classes("w-full gap-2 p-4"):
        for cmd in UI_METADATA["fastq"]["commands"]:
            # Disable Unalign if input is not BAM/CRAM
            disabled = not is_bam and cmd["cmd"] == "unalign"

            # Use our unified command button helper
            btn = ui_command_button(cmd).props(
                f"outline {'disabled' if disabled else ''}"
            )

            if disabled:
                with btn:
                    with ui.tooltip():
                        ui.label("Disabled: Input must be a BAM or CRAM file.")
