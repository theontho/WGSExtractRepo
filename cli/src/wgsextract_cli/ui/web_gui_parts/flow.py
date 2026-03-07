"""Flow frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.ui.constants import UI_METADATA


def frame_flow():
    ui.label(UI_METADATA["flow"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["flow"]["help"]).classes("text-slate-400 mb-4")

    # Workflow SVG or conceptual diagram
    with ui.card().classes(
        "w-full bg-slate-100 p-8 flex items-center justify-center min-h-[400px]"
    ):
        # Placeholder for SVG diagram
        ui.icon("schema", size="128px").classes("text-blue-200")
        ui.label("WGS Extract Pipeline Hierarchy").classes("text-slate-400 font-bold")
        ui.markdown(
            """
        - **BAM/CRAM** → Extraction → **FASTQ**
        - **BAM/CRAM** → Analysis → **VCF**
        - **VCF** → Interpretation → **Ancestry/Lineage**
        """
        ).classes("text-slate-600 mt-4")
