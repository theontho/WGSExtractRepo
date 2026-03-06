"""Pet Analysis tab frame for Cat and Dog genome analysis."""

import customtkinter as ctk

from .common import ScrollableBaseFrame, ToolTip


class PetFrame(ScrollableBaseFrame):
    """
    A frame for performing Pet Analysis (Cat/Dog alignment and variant calling).
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the pet analysis frame."""
        super().setup_ui()
        meta = self.meta

        # Pet Type Selection
        self.pet_type_var = ctk.StringVar(value="Dog")
        self.create_option_menu(
            self,
            "Pet Species:",
            options=["Dog", "Cat"],
            variable=self.pet_type_var,
            info_text="Select the species of your pet to use the correct reference genome.",
        )

        # Reference Library Selector
        self.ref_entry = self.create_dir_selector(
            self,
            "Reference Library:",
            variable=self.main_app.ref_path_var,
            info_text="Path to the directory containing your reference genomes. Ensure the animal genomes are downloaded in the Library tab.",
        )

        # Output Directory Selector
        self.out_dir = self.create_dir_selector(
            self,
            "Out Dir:",
            variable=self.main_app.out_dir_var,
            info_text="Directory where the resulting BAM and VCF files will be saved.",
        )

        # FASTQ Inputs
        align_cmd = next(c for c in meta["commands"] if c["cmd"] == "pet-analysis")

        self.fastq_r1 = self.create_file_selector(
            self,
            "FASTQ R1:",
            button_text=align_cmd["label"],
            command=lambda: self.handle_button_click("pet-analysis"),
            info_text="First read file (R1) for alignment.",
        )
        self.cmd_buttons["pet-analysis"] = self.fastq_r1.action_button
        ToolTip(self.cmd_buttons["pet-analysis"], align_cmd["help"])

        self.fastq_r2 = self.create_file_selector(
            self,
            "FASTQ R2 (opt):",
            info_text="Second read file (R2) for paired-end alignment (optional).",
        )

        # Output format selection
        self.output_format_var = ctk.StringVar(value="BAM")
        self.create_option_menu(
            self,
            "Output Format:",
            options=["BAM", "CRAM"],
            variable=self.output_format_var,
            info_text="Choose whether to output a standard BAM or a more compressed CRAM file.",
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
