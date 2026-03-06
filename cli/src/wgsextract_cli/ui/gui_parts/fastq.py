"""FASTQ tab frame for WGS Extract GUI."""

import os
from typing import Any

import customtkinter as ctk

from wgsextract_cli.core.messages import GUI_LABELS, GUI_MESSAGES, GUI_TOOLTIPS
from wgsextract_cli.core.ref_library import get_genome_status, get_grouped_genomes

from .gen import GenericFrame


class FastqFrame(GenericFrame):
    """
    A specialized frame for FASTQ operations, including automated genome selection.
    """

    def create_ref_selector(self, p: ctk.CTkFrame, meta: dict[str, Any]) -> None:
        """Override reference selector to use a dropdown for known genomes."""
        # Add a section for Reference Selection
        self.create_section_title(self, GUI_LABELS["ref_genome_selection"])

        # 1. Genome Library Dropdown
        self.genome_var = ctk.StringVar(value="Select from Library...")
        self.genome_menu = self.create_option_menu(
            self,
            GUI_LABELS["genome_library"],
            options=self._get_genome_options(),
            variable=self.genome_var,
            on_change=self._on_genome_change,
            info_text=GUI_TOOLTIPS["genome_lib_tip"],
        )

        # 2. Manual Reference Path (as fallback/direct path)
        self.ref_entry = self.create_file_selector(
            self,
            GUI_LABELS["manual_ref_path"],
            variable=self.main_app.ref_path_var,
            info_text="Optional: Manually specify a path to a reference genome FASTA file.",
        )

    def _get_genome_options(self) -> list[str]:
        """Get list of genomes with their installation status."""
        reflib = self.main_app.ref_path_var.get()
        # Note: reflib might be a file path if set by dropdown,
        # we need the root dir to check status of others.
        # But for status check, we'll try to find the library root.
        lib_root = reflib
        if reflib and os.path.isfile(reflib):
            # If it's something like /path/to/lib/genomes/hg19.fa.gz
            # we want /path/to/lib
            parent = os.path.dirname(reflib)
            if os.path.basename(parent) == "genomes":
                lib_root = os.path.dirname(parent)

        options = ["Select from Library...", "---"]
        self.genome_map = {}  # label -> genome_data

        try:
            groups = get_grouped_genomes()
            for g in groups:
                status = get_genome_status(g["final"], lib_root)
                status_str = (
                    f"[{GUI_LABELS['installed']}]"
                    if status == "installed"
                    else f"[{GUI_LABELS['missing']}]"
                )
                label = f"{g['label']} {status_str}"
                options.append(label)
                self.genome_map[label] = g
        except Exception:
            pass

        return options

    def _on_genome_change(self, label: str) -> None:
        """Handle selection of a genome from the dropdown."""
        if label in self.genome_map:
            g = self.genome_map[label]
            reflib = self.main_app.ref_path_var.get()

            lib_root = reflib
            if reflib and os.path.isfile(reflib):
                parent = os.path.dirname(reflib)
                if os.path.basename(parent) == "genomes":
                    lib_root = os.path.dirname(parent)

            if not lib_root or not os.path.isdir(lib_root):
                # Fallback to current working directory if no lib root
                lib_root = os.getcwd()

            final_path = os.path.join(lib_root, "genomes", g["final"])
            # Update the manual ref path variable so the command uses it
            self.main_app.ref_path_var.set(final_path)

    def handle_button_click(self, cmd_key: str) -> None:
        """Intercept 'align' to check if genome needs download."""
        if cmd_key == "align":
            label = self.genome_var.get()
            if label in self.genome_map:
                g = self.genome_map[label]
                reflib = self.main_app.ref_path_var.get()

                lib_root = reflib
                if reflib and os.path.isfile(reflib):
                    parent = os.path.dirname(reflib)
                    if os.path.basename(parent) == "genomes":
                        lib_root = os.path.dirname(parent)

                status = get_genome_status(g["final"], lib_root)

                if status != "installed":
                    if self.main_app.show_question(
                        GUI_MESSAGES["genome_missing_title"],
                        GUI_MESSAGES["genome_missing_msg"].format(label=g["label"]),
                    ):
                        # Switch to library tab and start download
                        self.main_app.show_frame("lib")
                        lib_frame = self.main_app.frames.get("lib")
                        if lib_frame:
                            # Start download for the first source
                            self.main_app.controller.run_lib_download(
                                g["sources"][0], lib_frame
                            )
                        return
                    else:
                        return  # User cancelled

        super().handle_button_click(cmd_key)

    def update_options(self) -> None:
        """Refresh the genome dropdown options."""
        if hasattr(self, "genome_menu"):
            self.genome_menu.configure(values=self._get_genome_options())
