import os

import customtkinter as ctk

from wgsextract_cli.ui.gui_parts.common import BaseFrame


class SettingsFrame(BaseFrame):
    """Settings frame for configuring application paths and cache."""

    def setup_ui(self) -> None:
        """Set up the settings UI elements."""
        super().setup_ui()

        # Content frame for better alignment
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Section: Application Paths
        self.create_section_title(
            content_frame,
            "Application Paths",
            "Configure default paths used across the application.",
        )

        self.create_dir_selector(
            content_frame,
            label_text="Reference Library:",
            variable=self.main_app.ref_path_var,
            info_text="Directory where reference genome files (e.g. FASTA) are stored.",
        )

        self.create_dir_selector(
            content_frame,
            label_text="Output Directory:",
            variable=self.main_app.out_dir_var,
            info_text="Default directory for saving outputs.",
        )

        # Section: Settings Cache
        self.create_section_title(
            content_frame,
            "Settings Cache",
            "The .env.local file stores environment variables like paths.",
        )

        self.create_file_selector(
            content_frame,
            label_text=".env.local File:",
            variable=self.main_app.env_local_var,
            info_text="Path to the .env.local configuration cache file.",
        )

        # Save Button
        btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)

        ctk.CTkButton(
            btn_frame,
            text="Save to .env.local",
            command=self.save_settings,
            font=("Courier", 13, "bold"),
            fg_color="#3a7ebf",
            hover_color="#325882",
        ).pack(side="right", padx=30)

        # Status Label
        self.status_label = ctk.CTkLabel(btn_frame, text="", text_color="green")
        self.status_label.pack(side="right", padx=10)

    def save_settings(self) -> None:
        """Save current paths to .env.local."""
        env_path = self.main_app.env_local_var.get()
        if not env_path:
            self.status_label.configure(
                text="Error: No .env.local path set.", text_color="red"
            )
            return

        ref_path = self.main_app.ref_path_var.get()
        out_dir = self.main_app.out_dir_var.get()

        # Read existing or create new
        lines = []
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()

        # Update or append variables
        new_lines = []
        ref_updated = False
        out_updated = False

        for line in lines:
            if line.startswith("WGSE_REF="):
                new_lines.append(f"WGSE_REF={ref_path}\n")
                ref_updated = True
            elif line.startswith("WGSE_OUTDIR="):
                new_lines.append(f"WGSE_OUTDIR={out_dir}\n")
                out_updated = True
            else:
                new_lines.append(line)

        if not ref_updated:
            new_lines.append(f"WGSE_REF={ref_path}\n")
        if not out_updated:
            new_lines.append(f"WGSE_OUTDIR={out_dir}\n")

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            self.status_label.configure(
                text="Settings saved successfully!", text_color="green"
            )
            # Clear status after 3 seconds
            self.after(3000, lambda: self.status_label.configure(text=""))
            self.main_app.log(f"Saved settings to {env_path}")
        except Exception as e:
            self.status_label.configure(text=f"Error saving: {e}", text_color="red")
            self.main_app.log(f"Error saving settings: {e}")
