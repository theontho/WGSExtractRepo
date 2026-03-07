"""Settings tab frame for the Web GUI."""

from nicegui import ui

from .common import save_env, ui_row_dir, ui_row_input


def frame_settings():
    ui.label("Settings").classes("text-h5 mb-2")
    ui.markdown("Configure environment variables and global paths.").classes(
        "text-slate-400 mb-4"
    )

    with ui.card().classes("w-full p-4 gap-4"):
        ui_row_dir("Output Directory", "out_dir")
        ui_row_dir("Reference Library", "ref_path")
        ui_row_input("Yleaf Execution Path", "yleaf_path")
        ui_row_input("Haplogrep JAR Path", "haplogrep_path")

        ui.separator()
        with ui.row().classes("w-full justify-end"):
            ui.button("Save to .env.local", on_click=save_env).props("primary")
