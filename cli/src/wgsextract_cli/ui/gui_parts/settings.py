import os
import shutil

import customtkinter as ctk

from wgsextract_cli.core.dependencies import get_jar_path
from wgsextract_cli.ui.gui_parts.common import ScrollableBaseFrame


class SettingsFrame(ScrollableBaseFrame):
    """Settings frame for configuring application paths, cache, and tool dependencies."""

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

        self.create_file_selector(
            content_frame,
            label_text="Yleaf Path:",
            variable=self.main_app.yleaf_path_var,
            info_text="Path to the Yleaf executable for Y-haplogroup prediction.",
        )

        self.create_file_selector(
            content_frame,
            label_text="Haplogrep Path:",
            variable=self.main_app.haplogrep_path_var,
            info_text="Path to the Haplogrep jar or executable for mitochondrial lineage.",
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

        # Section: Dependencies Check
        self.create_section_title(
            content_frame,
            "Dependencies Check",
            "Checks whether required external tools are available on your system path.",
        )

        self.dep_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        self.dep_frame.pack(fill="x", pady=5)

        refresh_btn_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        refresh_btn_frame.pack(fill="x", pady=5)
        ctk.CTkButton(
            refresh_btn_frame,
            text="Refresh Dependencies",
            command=self.populate_dependencies,
            font=("Courier", 11, "bold"),
            width=150,
        ).pack(side="left", padx=10)

        self.populate_dependencies()

    def populate_dependencies(self) -> None:
        """Check all dependencies and populate the UI grid."""
        import re
        import subprocess

        # Clear existing
        for widget in self.dep_frame.winfo_children():
            widget.destroy()

        tools = [
            "samtools",
            "bcftools",
            "tabix",
            "bgzip",
            "htsfile",
            "bwa",
            "minimap2",
            "fastp",
            "fastqc",
            "delly",
            "freebayes",
            "vep",
            "java",
            "python3",
            "curl",
            "wget",
            "tar",
            "gzip",
            "gatk-package-4.1.9.0-local.jar",
        ]

        def check_tool_version(t: str) -> tuple[bool, str]:
            if t == "python3":
                try:
                    res = subprocess.run(
                        [t, "--version"], capture_output=True, text=True, timeout=2
                    )
                    match = re.search(r"Python (\d+)\.(\d+)", res.stdout)
                    if match:
                        major, minor = int(match.group(1)), int(match.group(2))
                        if major == 3 and minor >= 11:
                            return True, f" (v{major}.{minor})"
                        return False, f" (v{major}.{minor}, need >=3.11)"
                except Exception:
                    pass
            elif t == "java":
                try:
                    res = subprocess.run(
                        [t, "-version"], capture_output=True, text=True, timeout=2
                    )
                    match = re.search(r"version \"?(\d+)", res.stderr + res.stdout)
                    if match:
                        major = int(match.group(1))
                        if major >= 8:
                            return True, f" (v{major})"
                        return False, f" (v{major}, need >=8)"
                except Exception:
                    pass
            return True, ""

        # Use a grid layout for dependencies
        row = 0
        col = 0
        max_cols = 6

        for tool in tools:
            is_jar = tool.endswith(".jar")
            if is_jar:
                is_installed = get_jar_path(tool) is not None
            else:
                is_installed = shutil.which(tool) is not None

            version_ok = True
            version_text = ""
            if is_installed and tool in ["python3", "java"]:
                version_ok, version_text = check_tool_version(tool)

            is_valid = is_installed and version_ok
            color = "#4CAF50" if is_valid else "#F44336"
            symbol = "✓" if is_valid else "✗"

            tool_frame = ctk.CTkFrame(self.dep_frame, fg_color="transparent")
            tool_frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")

            symbol_lbl = ctk.CTkLabel(
                tool_frame, text=symbol, text_color=color, font=("Courier", 14, "bold")
            )
            symbol_lbl.pack(side="left", padx=(0, 5))

            name_lbl = ctk.CTkLabel(tool_frame, text=f"{tool}{version_text}")
            name_lbl.pack(side="left")

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

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
        yleaf_path = self.main_app.yleaf_path_var.get()
        haplogrep_path = self.main_app.haplogrep_path_var.get()

        # Read existing or create new
        lines = []
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()

        # Update or append variables
        new_lines = []
        ref_updated = False
        out_updated = False
        yleaf_updated = False
        haplogrep_updated = False

        for line in lines:
            if line.startswith("WGSE_REF="):
                new_lines.append(f'WGSE_REF="{ref_path}"\n')
                ref_updated = True
            elif line.startswith("WGSE_OUTDIR="):
                new_lines.append(f'WGSE_OUTDIR="{out_dir}"\n')
                out_updated = True
            elif line.startswith("WGSE_YLEAF_PATH="):
                new_lines.append(f'WGSE_YLEAF_PATH="{yleaf_path}"\n')
                yleaf_updated = True
            elif line.startswith("WGSE_HAPLOGREP_PATH="):
                new_lines.append(f'WGSE_HAPLOGREP_PATH="{haplogrep_path}"\n')
                haplogrep_updated = True
            else:
                new_lines.append(line)

        if not ref_updated and ref_path:
            new_lines.append(f'WGSE_REF="{ref_path}"\n')
        if not out_updated and out_dir:
            new_lines.append(f'WGSE_OUTDIR="{out_dir}"\n')
        if not yleaf_updated and yleaf_path:
            new_lines.append(f'WGSE_YLEAF_PATH="{yleaf_path}"\n')
        if not haplogrep_updated and haplogrep_path:
            new_lines.append(f'WGSE_HAPLOGREP_PATH="{haplogrep_path}"\n')

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
