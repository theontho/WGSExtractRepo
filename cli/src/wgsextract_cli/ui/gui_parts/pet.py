"""Pet Analysis tab frame for Cat and Dog genome analysis."""

import customtkinter as ctk

from wgsextract_cli.core.help_texts import ABOUT_PET_SEQUENCING
from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
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
        self.pet_type_var = ctk.StringVar(value="Dog")
        self.create_option_menu(
            self,
            GUI_LABELS["pet_species"],
            options=["Dog", "Cat"],
            variable=self.pet_type_var,
            info_text=GUI_TOOLTIPS["pet_species_tip"],
        )

        # Reference Library Selector
        self.ref_entry = self.create_dir_selector(
            self,
            GUI_LABELS["ref_library_path"],
            variable=self.main_app.ref_path_var,
            info_text=GUI_TOOLTIPS["ref_lib_tip"],
        )

        # Output Directory Selector
        self.out_dir = self.create_dir_selector(
            self,
            GUI_LABELS["out_dir"],
            variable=self.main_app.out_dir_var,
            info_text="Directory where the resulting BAM and VCF files will be saved.",
        )

        # FASTQ Inputs
        align_cmd = next(c for c in meta["commands"] if c["cmd"] == "pet-analysis")

        self.fastq_r1 = self.create_file_selector(
            self,
            GUI_LABELS["fastq_r1"],
            button_text=align_cmd["label"],
            command=lambda: self.handle_button_click("pet-analysis"),
            info_text=GUI_TOOLTIPS["pet_r1_tip"],
        )
        self.cmd_buttons["pet-analysis"] = self.fastq_r1.action_button
        ToolTip(self.cmd_buttons["pet-analysis"], align_cmd["help"])

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

    def handle_button_click(self, cmd_key: str) -> None:
        """Handle pet analysis button click with custom parameters."""
        if cmd_key == "pet-analysis":
            # We'll pass extra args to the controller
            extra_args = {
                "pet_type": self.pet_type_var.get(),
                "r1": self.fastq_r1.get(),
                "r2": self.fastq_r2.get(),
                "format": self.output_format_var.get(),
            }
            self.main_app.controller.run_pet_analysis(self, extra_args)
        else:
            super().handle_button_click(cmd_key)

    def show_about_pets(self) -> None:
        """Show information about pet sequencing."""
        self.main_app.show_info_window("About Pet Sequencing", ABOUT_PET_SEQUENCING)
