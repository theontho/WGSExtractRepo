"""Web-based Graphical User Interface for WGS Extract using NiceGUI."""

import asyncio
import logging

from nicegui import ui

from wgsextract_cli.core.messages import GUI_LABELS
from wgsextract_cli.ui.constants import UI_METADATA

from .web_gui_parts.anc import frame_anc
from .web_gui_parts.common import (
    log_area,
    set_render_content_refresh_cb,
)
from .web_gui_parts.controller import controller
from .web_gui_parts.ext import frame_ext
from .web_gui_parts.fastq import frame_fastq
from .web_gui_parts.flow import frame_flow
from .web_gui_parts.gen import frame_gen
from .web_gui_parts.lib import frame_lib
from .web_gui_parts.micro import frame_micro
from .web_gui_parts.pet import frame_pet
from .web_gui_parts.settings import frame_settings
from .web_gui_parts.state import state
from .web_gui_parts.vcf import frame_vcf

logger = logging.getLogger(__name__)


@ui.refreshable
def render_content():
    with ui.column().classes("w-full p-8"):
        if state.active_tab == "flow":
            frame_flow()
        elif state.active_tab == "gen":
            frame_gen()
        elif state.active_tab == "ext":
            frame_ext()
        elif state.active_tab == "micro":
            frame_micro()
        elif state.active_tab == "anc":
            frame_anc()
        elif state.active_tab == "vcf":
            frame_vcf()
        elif state.active_tab == "fastq":
            frame_fastq()
        elif state.active_tab == "lib":
            frame_lib()
        elif state.active_tab == "pet":
            frame_pet()
        elif state.active_tab == "settings":
            frame_settings()

        log_area()


# Set the refresh callback for the controller to use
set_render_content_refresh_cb(render_content.refresh)


@ui.page("/")
def main_page():
    header()
    sidebar()
    render_content()

    # Trigger fast info on startup if path is already set (e.g. from .env)
    if state.bam_path and not controller.info_data:
        asyncio.create_task(controller.get_info_fast(state.bam_path))


def header():
    with ui.header().classes("items-center justify-between bg-blue-900"):
        ui.label(GUI_LABELS["app_title"]).classes("text-h6 font-bold")
        with ui.row().classes("items-center"):
            ui.button(
                icon="settings", on_click=lambda: controller.set_tab("settings")
            ).props("flat color=white")
            ui.button(
                icon="help",
                on_click=lambda: ui.navigate.to(
                    "https://github.com/WGS-Extract/WGSExtract", new_tab=True
                ),
            ).props("flat color=white")


def sidebar():
    with ui.left_drawer(value=True).classes("bg-slate-100").props("bordered"):
        with ui.column().classes("w-full p-4 gap-2"):
            # Logo placeholder
            ui.icon("biotech", size="lg").classes("self-center mb-4 text-blue-800")

            for key, meta in UI_METADATA.items():
                if key == "settings":
                    continue
                ui.button(
                    meta["title"], on_click=lambda k=key: controller.set_tab(k)
                ).classes("w-full").props(
                    f"flat color={'primary' if state.active_tab == key else 'black'}"
                )


def main():
    """Start the NiceGUI application."""
    from nicegui import app

    from wgsextract_cli.core.utils import cleanup_processes

    app.on_shutdown(cleanup_processes)
    ui.run(title="WGS Extract Web GUI", port=8081, reload=False, dark=True)


if __name__ in {"__main__", "nicegui"}:
    main()
