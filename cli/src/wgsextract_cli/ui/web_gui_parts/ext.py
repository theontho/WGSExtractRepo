"""Extract tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_input
from .controller import controller


def frame_ext():
    ui.label(UI_METADATA["ext"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["ext"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input(
            GUI_LABELS["bam_cram"], "bam_path", info_text=GUI_TOOLTIPS["bam_input_tip"]
        )
        ui_row_input(
            GUI_LABELS["region_label"],
            "extract_region",
            info_text=GUI_TOOLTIPS["region_tip"],
        )
        ui_row_input(
            GUI_LABELS["extra_label"],
            "extract_extra",
            info_text=GUI_TOOLTIPS["extra_tip"],
        )

    # Gender detection
    gender = controller.info_data.get("gender", "").lower()
    is_female = "female" in gender

    with ui.expansion("Extract Operations", icon="content_cut", value=True).classes(
        "w-full border border-slate-700 rounded-lg"
    ):
        with ui.row().classes("w-full gap-2 p-4"):
            for cmd in UI_METADATA["ext"]["commands"]:
                # Disable Y-DNA buttons for female samples
                disabled = is_female and cmd["cmd"] in [
                    "ydna-bam",
                    "ydna-vcf",
                    "y-mt-extract",
                ]
                ui.button(
                    cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                ).props(f"outline {'disabled' if disabled else ''}")
                if disabled:
                    with ui.tooltip():
                        ui.label("Disabled: Sample detected as female.")
