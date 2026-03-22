"""VCF tab frame for the Web GUI."""

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import UI_METADATA

from .common import run_generic_cmd, ui_row_dir, ui_row_input
from .state import state


def frame_vcf():
    ui.label(UI_METADATA["vcf"]["title"]).classes("text-h5 mb-2")
    ui.markdown(UI_METADATA["vcf"]["help"]).classes("text-slate-400 mb-4")

    with ui.column().classes("w-full gap-2 mb-4"):
        ui_row_input(
            GUI_LABELS["vcf_input"], "vcf_path", info_text=GUI_TOOLTIPS["vcf_input_tip"]
        )
        ui_row_dir(
            GUI_LABELS["ref_library_path"],
            "ref_path",
            info_text="Path to the directory containing your reference genomes.",
        )
        ui_row_dir(
            GUI_LABELS["out_dir"], "out_dir", info_text=GUI_TOOLTIPS["out_dir_tip"]
        )

    # 1. Variant Calling & Annotation Section
    with ui.expansion(
        GUI_LABELS["var_calling_ann"], icon="biotech", value=True
    ).classes("w-full border border-slate-700 rounded-lg mb-2"):
        with ui.column().classes("w-full p-4 gap-2"):
            ui_row_input(
                GUI_LABELS["region_generic"],
                "vcf_region",
                info_text="Specific chromosomal region (e.g., chrM, chr1:100-200).",
            )
            ui_row_input(
                GUI_LABELS["gene_name"],
                "vcf_gene",
                info_text="Target gene name (e.g., BRCA1).",
            )

            with ui.row().classes("w-full items-center px-2"):
                ui.checkbox(GUI_LABELS["gap_aware_filtering"]).bind_value(
                    state, "vcf_exclude_gaps"
                )
                icon = ui.icon("info", size="xs").classes(
                    "text-blue-400 cursor-help ms-1"
                )
                with icon:
                    from .common import add_tooltip

                    add_tooltip(GUI_TOOLTIPS["gap_aware_tip"])

            ui_row_input(
                GUI_LABELS["filter_expr"],
                "vcf_filter_expr",
                info_text="BCFTools filter expression (e.g., 'QUAL>30 && DP>10').",
            )
            ui_row_input(
                GUI_LABELS["annotate_vcf"],
                "vcf_ann_vcf",
                info_text="VCF file to use for annotation (e.g., ClinVar, dbSNP).",
            )

            ui.label("Calling Actions").classes("text-subtitle2 mt-4")
            with ui.row().classes("w-full gap-2"):
                calling_cmds = UI_METADATA["vcf"]["commands"][:7]  # SNP to DeepVariant
                for cmd in calling_cmds:
                    ui.button(
                        cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                    ).props("outline")

            ui.label("Processing Actions").classes("text-subtitle2 mt-2")
            with ui.row().classes("w-full gap-2"):
                proc_cmds = [
                    c
                    for c in UI_METADATA["vcf"]["commands"]
                    if c["cmd"]
                    in [
                        "annotate",
                        "spliceai",
                        "alphamissense",
                        "pharmgkb",
                        "filter",
                        "vcf-qc",
                        "repair-ftdna-vcf",
                    ]
                ]
                for cmd in proc_cmds:
                    ui.button(
                        cmd["label"], on_click=lambda c=cmd: run_generic_cmd(c)
                    ).props("outline color=orange")

    # 2. Trio Analysis Section
    with ui.expansion(GUI_LABELS["trio_analysis"], icon="family_restroom").classes(
        "w-full border border-slate-700 rounded-lg mb-2"
    ):
        with ui.column().classes("w-full p-4 gap-2"):
            ui.markdown(GUI_TOOLTIPS["trio_analysis_help"]).classes(
                "text-xs text-slate-400 mb-2"
            )
            ui_row_input(
                GUI_LABELS["mother_vcf"],
                "vcf_mother",
                info_text="Path to the mother's VCF.",
            )
            ui_row_input(
                GUI_LABELS["father_vcf"],
                "vcf_father",
                info_text="Path to the father's VCF.",
            )

            with ui.row().classes("w-full justify-end"):
                trio_cmd = next(
                    c for c in UI_METADATA["vcf"]["commands"] if c["cmd"] == "trio"
                )
                ui.button(
                    trio_cmd["label"], on_click=lambda: run_generic_cmd(trio_cmd)
                ).props("color=primary")

    # 3. VEP Analysis Section
    with ui.expansion(GUI_LABELS["vep_analysis"], icon="psychology").classes(
        "w-full border border-slate-700 rounded-lg mb-2"
    ):
        with ui.column().classes("w-full p-4 gap-2"):
            ui.markdown(GUI_TOOLTIPS["vep_analysis_help"]).classes(
                "text-xs text-slate-400 mb-2"
            )
            ui_row_input(
                GUI_LABELS["vep_cache"],
                "vep_cache_path",
                info_text=GUI_TOOLTIPS["vep_cache_tip"],
            )
            ui_row_input(
                GUI_LABELS["extra_vep_args"],
                "vcf_vep_args",
                info_text=GUI_TOOLTIPS["vep_args_tip"],
            )

            with ui.row().classes("w-full justify-end"):
                vep_cmd = next(
                    c for c in UI_METADATA["vcf"]["commands"] if c["cmd"] == "vep-run"
                )
                ui.button(
                    vep_cmd["label"], on_click=lambda: run_generic_cmd(vep_cmd)
                ).props("color=secondary")
