"""Library tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_dir, ui_row_input
from .controller import controller
from .state import state


def frame_lib():
    ui.label(UI_METADATA["lib"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["lib"]["help"]).classes("text-slate-400 mb-4")

    from wgsextract_cli.core.ref_library import (
        get_genome_size,
        get_genome_status,
        get_grouped_genomes,
        has_ref_ns,
    )

    with ui.column().classes("w-full gap-4"):
        ui_row_dir(
            GUI_LABELS["ref_library_path"],
            "ref_path",
            info_text="Path to store downloaded reference genomes and databases.",
        )
        ui_row_input(
            GUI_LABELS["vep_cache_path"],
            "vep_cache_path",
            info_text=GUI_TOOLTIPS["vep_cache_tip"],
        )

        # 1. Genome Management Section
        with ui.expansion("Manage Genomes", icon="library_books", value=True).classes(
            "w-full border border-slate-700 rounded-lg"
        ):
            with ui.column().classes("w-full p-4 gap-2"):
                grouped = get_grouped_genomes()
                dest = state.ref_path

                for group in grouped:
                    fn = group["final"]
                    status = get_genome_status(fn, dest)
                    size = get_genome_size(fn, dest)
                    has_ns = has_ref_ns(fn, dest)

                    # Real-time download info
                    dl_info = controller.active_downloads.get(fn)

                    with ui.card().classes("w-full mb-1 p-3"):
                        with ui.row().classes("w-full items-center justify-between"):
                            with ui.column().classes("gap-0"):
                                ui.label(group["label"]).classes("font-bold text-sm")
                                ui.label(group["description"]).classes(
                                    "text-xs text-slate-400"
                                )
                                if dl_info:
                                    status_text = dl_info["status"]
                                else:
                                    status_text = f"Status: {status.capitalize()}"
                                    if size:
                                        status_text += f" | Size: {size}"
                                ui.label(status_text).classes("text-xs mt-1")

                                if dl_info:
                                    ui.linear_progress().bind_value_from(
                                        dl_info, "prog"
                                    ).classes("w-full mt-2")

                            with ui.row().classes("gap-1 items-center"):
                                if dl_info:
                                    ui.button(
                                        icon="close",
                                        color="red",
                                        on_click=lambda f=fn: (
                                            controller.cancel_lib_download(f)
                                        ),
                                    ).props("flat dense")
                                elif status == "missing":
                                    ui.button(
                                        "Download",
                                        icon="download",
                                        on_click=lambda g=group: (
                                            controller.run_lib_download(g)
                                        ),
                                    ).props("outline dense")
                                elif status in ["installed", "unindexed"]:
                                    with ui.row().classes("gap-1"):
                                        if status == "unindexed":
                                            ui.button(
                                                "Index",
                                                icon="bolt",
                                                on_click=lambda g=group: (
                                                    controller.run_ref_index(g)
                                                ),
                                            ).props("outline dense color=warning")
                                        else:
                                            ui.button(
                                                "Verify",
                                                icon="check_circle",
                                                on_click=lambda g=group: (
                                                    controller.run_ref_verify(g)
                                                ),
                                            ).props("outline dense color=success")

                                        if not has_ns:
                                            ui.button(
                                                "Count-Ns",
                                                icon="analytics",
                                                on_click=lambda g=group: (
                                                    controller.run_ref_count_ns(g)
                                                ),
                                            ).props("outline dense")

                                        ui.button(
                                            icon="delete",
                                            color="red",
                                            on_click=lambda g=group: (
                                                controller.run_lib_delete(g)
                                            ),
                                        ).props("flat dense")
                                elif status == "incomplete":
                                    ui.button(
                                        "Resume",
                                        icon="play_arrow",
                                        on_click=lambda g=group: (
                                            controller.run_lib_download(g)
                                        ),
                                    ).props("outline dense color=positive")
                                    ui.button(
                                        icon="delete",
                                        color="red",
                                        on_click=lambda g=group: (
                                            controller.run_lib_delete(g)
                                        ),
                                    ).props("flat dense")

        # 2. VEP & Databases Section
        with ui.expansion("Databases & Tools", icon="dataset", value=False).classes(
            "w-full border border-slate-700 rounded-lg"
        ):
            with ui.column().classes("w-full p-4 gap-4"):
                # VEP Cache
                with ui.card().classes("w-full p-3"):
                    ui.label("Ensembl VEP Cache").classes("font-bold mb-2 text-sm")
                    with ui.row().classes("w-full gap-2"):
                        vep_dl_cmd = next(
                            c
                            for c in UI_METADATA["lib"]["vep_commands"]
                            if c["cmd"] == "vep-download"
                        )
                        ui.button(
                            vep_dl_cmd["label"],
                            on_click=lambda: controller.run_vep_download(),
                        ).props("outline color=primary")

                        vep_verify_cmd = next(
                            c
                            for c in UI_METADATA["lib"]["vep_commands"]
                            if c["cmd"] == "vep-verify"
                        )
                        ui.button(
                            vep_verify_cmd["label"],
                            on_click=lambda c=vep_verify_cmd: run_generic_cmd(c),
                        ).props("outline")

                # Gene Maps
                with ui.card().classes("w-full p-3"):
                    ui.label("Gene Names Database").classes("font-bold mb-2 text-sm")
                    with ui.row().classes("w-full gap-2"):
                        gene_cmd = UI_METADATA["lib"]["commands"][0]  # Gene Map
                        ui.button(
                            gene_cmd["label"],
                            on_click=lambda c=gene_cmd: run_generic_cmd(c),
                        ).props("outline color=secondary")

    # Refresh timer to update progress bars and status
    ui.timer(1.0, ui.update)
