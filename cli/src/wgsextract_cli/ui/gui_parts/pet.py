"""Pet Analysis tab frame for Cat and Dog genome analysis."""

import os

import customtkinter as ctk

from wgsextract_cli.core.help_texts import ABOUT_PET_SEQUENCING
from wgsextract_cli.core.messages import GUI_LABELS, GUI_MESSAGES, GUI_TOOLTIPS
from wgsextract_cli.core.ref_library import get_genome_status, get_grouped_genomes
from wgsextract_cli.ui.constants import BUTTON_FONT

from .common import ScrollableBaseFrame, ToolTip


class PetFrame(ScrollableBaseFrame):
    """
    A frame for performing Pet Analysis (Cat/Dog alignment and variant calling).
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the pet analysis frame."""
        super().setup_ui()
        meta = self.meta

        # About Pet Sequencing Button
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=5)
        btn = ctk.CTkButton(
            f,
            text=GUI_LABELS["about_pet_seq"],
            command=self.show_about_pets,
            font=BUTTON_FONT,
            fg_color="#2c3e50",
            hover_color="#34495e",
        )
        btn.pack(side="left", padx=10)
        ToolTip(
            btn, "Click to learn more about dog and cat sequencing and how to get data."
        )

        # Pet Type Selection
        self.pet_type_var = ctk.StringVar(value="Select Pet Species...")
        self.pet_menu = self.create_option_menu(
            self,
            GUI_LABELS["pet_species"],
            options=self._get_pet_options(),
            variable=self.pet_type_var,
            on_change=self._on_pet_change,
            info_text=GUI_TOOLTIPS["pet_species_tip"],
        )

        # Reference Genome Selector
        self.ref_entry = self.create_file_selector(
            self,
            GUI_LABELS["ref_fasta_path"],
            variable=self.main_app.pet_ref_fasta_var,
            info_text="Path to the specific reference genome FASTA file.",
        )

        # Output Directory Selector
        self.out_dir = self.create_dir_selector(
            self,
            GUI_LABELS["out_dir"],
            variable=self.main_app.out_dir_var,
            info_text="Directory where the resulting BAM and VCF files will be saved.",
        )

        # FASTQ Inputs
        self.fastq_r1 = self.create_file_selector(
            self,
            GUI_LABELS["fastq_r1"],
            info_text=GUI_TOOLTIPS["pet_r1_tip"],
        )

        self.fastq_r2 = self.create_file_selector(
            self,
            GUI_LABELS["fastq_r2"],
            info_text=GUI_TOOLTIPS["pet_r2_tip"],
        )

        # Output format selection
        self.output_format_var = ctk.StringVar(value="BAM")
        self.create_option_menu(
            self,
            GUI_LABELS["output_format"],
            options=["BAM", "CRAM"],
            variable=self.output_format_var,
            info_text=GUI_TOOLTIPS["output_fmt_tip"],
        )

        # Action Buttons Section
        self._create_section(None, meta["commands"])

    def _get_pet_options(self) -> list[str]:
        """Get list of pet genomes with their installation status."""
        reflib = self.main_app.ref_path_var.get()
        lib_root = reflib
        if reflib and os.path.isfile(reflib):
            parent = os.path.dirname(reflib)
            if os.path.basename(parent) == "genomes":
                lib_root = os.path.dirname(parent)

        options = ["Select Pet Species..."]
        self.pet_map = {}  # label -> genome_data

        try:
            groups = get_grouped_genomes()
            for g in groups:
                if "Dog" in g["label"] or "Cat" in g["label"]:
                    status = get_genome_status(g["final"], lib_root)
                    status_str = (
                        f"[{GUI_LABELS['installed']}]"
                        if status == "installed"
                        else f"[{GUI_LABELS['missing']}]"
                    )
                    base_label = "Dog" if "Dog" in g["label"] else "Cat"
                    label = f"{base_label} {status_str}"
                    options.append(label)
                    self.pet_map[label] = g
        except Exception:
            pass

        if len(options) == 1:
            # Fallback
            options = ["Select Pet Species...", "Dog", "Cat"]

        return options

    def _on_pet_change(self, label: str) -> None:
        """Handle selection of a pet species from the dropdown."""
        if hasattr(self, "pet_map") and label in self.pet_map:
            g = self.pet_map[label]
            if not g.get("final"):
                return
            reflib = self.main_app.ref_path_var.get()

            lib_root = reflib
            if reflib and os.path.isfile(reflib):
                parent = os.path.dirname(reflib)
                if os.path.basename(parent) == "genomes":
                    lib_root = os.path.dirname(parent)

            if not lib_root or not os.path.isdir(lib_root):
                lib_root = os.getcwd()

            final_path = os.path.join(lib_root, "genomes", g["final"])
            self.main_app.pet_ref_fasta_var.set(final_path)

    def handle_button_click(self, cmd_key: str) -> None:
        """Handle pet analysis button click with custom parameters."""
        if cmd_key == "pet-analysis":
            label = self.pet_type_var.get()
            pet_type = "Dog" if "Dog" in label else "Cat"

            # Check for download if missing
            if hasattr(self, "pet_map") and label in self.pet_map:
                g = self.pet_map[label]
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
                        self.main_app.show_frame("lib")
                        lib_frame = self.main_app.frames.get("lib")
                        if lib_frame:
                            self.main_app.controller.run_lib_download(
                                g["sources"][0], lib_frame
                            )
                        return
                    else:
                        return

            # We'll pass extra args to the controller
            extra_args = {
                "pet_type": pet_type,
                "r1": self.fastq_r1.get(),
                "r2": self.fastq_r2.get(),
                "format": self.output_format_var.get(),
            }
            self.main_app.controller.run_pet_analysis(self, extra_args)
        else:
            super().handle_button_click(cmd_key)

    def update_options(self) -> None:
        """Refresh the pet species dropdown options."""
        if hasattr(self, "pet_menu"):
            self.pet_menu.configure(values=self._get_pet_options())

    def show_about_pets(self) -> None:
        """Show information about pet sequencing."""
        self.main_app.show_info_window("About Pet Sequencing", ABOUT_PET_SEQUENCING)
