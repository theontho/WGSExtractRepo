"""Settings frame for configuring application paths, cache, and tool dependencies."""

import os
import shutil

import customtkinter as ctk

from wgsextract_cli.core.dependencies import get_jar_path
from wgsextract_cli.ui.gui_parts.common import ScrollableBaseFrame, ToolTip


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

        self.create_file_selector(
            content_frame,
            label_text="Input VCF:",
            variable=self.main_app.vcf_path_var,
            info_text="Default primary VCF file path.",
        )

        self.create_file_selector(
            content_frame,
            label_text="Mother VCF:",
            variable=self.main_app.vcf_mother_var,
            info_text="Default mother VCF file path for trio analysis.",
        )

        self.create_file_selector(
            content_frame,
            label_text="Father VCF:",
            variable=self.main_app.vcf_father_var,
            info_text="Default father VCF file path for trio analysis.",
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
            width=200,
        ).pack(side="right", padx=30)

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
            "gatk",
            "run_deepvariant",
        ]

        def check_tool_functional(t: str) -> tuple[bool, str, str]:
            """Perform a smoke test to ensure the tool actually runs."""
            if t == "python3":
                try:
                    res = subprocess.run(
                        [t, "--version"], capture_output=True, text=True, timeout=2
                    )
                    match = re.search(r"Python (\d+)\.(\d+)", res.stdout)
                    if match:
                        major, minor = int(match.group(1)), int(match.group(2))
                        if major == 3 and minor >= 11:
                            return (
                                True,
                                f" (v{major}.{minor})",
                                f"Success: Python {major}.{minor} detected.",
                            )
                        return (
                            False,
                            f" (v{major}.{minor}, need >=3.11)",
                            f"Python version too old: {res.stdout}",
                        )
                except Exception as e:
                    return False, " (python error)", str(e)
            elif t == "java":
                try:
                    res = subprocess.run(
                        [t, "-version"], capture_output=True, text=True, timeout=2
                    )
                    # Java outputs version to stderr
                    out = res.stderr + res.stdout
                    match = re.search(r"version \"?(\d+)", out)
                    if match:
                        major = int(match.group(1))
                        if major >= 8:
                            return (
                                True,
                                f" (v{major})",
                                f"Success: Java {major} detected.",
                            )
                        return (
                            False,
                            f" (v{major}, need >=8)",
                            f"Java version too old: {out}",
                        )
                except Exception as e:
                    return False, " (java error)", str(e)
            elif t.endswith(".jar"):
                p = get_jar_path(t)
                return True, "", f"Success: JAR found at {p}"
            else:
                # Some tools need specific flags or no flags to check functionality
                if t == "bwa":
                    flags = [""]
                elif t == "delly":
                    flags = ["-v"]
                else:
                    flags = ["--version", "-v", "--help", "-h"]

                # Try flags until one works
                last_err = ""
                for flag in flags:
                    try:
                        cmd = [t]
                        if flag:
                            cmd.append(flag)
                        res = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=1
                        )

                        err_out = (res.stderr + res.stdout).strip()

                        # Success if exit code 0
                        if res.returncode == 0:
                            return (
                                True,
                                "",
                                f"Success: Functional check '{t} {flag}' passed (Exit 0).",
                            )

                        # Special case: bwa returns 1 when run without args, but it's functional
                        if t == "bwa" and res.returncode == 1 and "Usage:" in err_out:
                            return (
                                True,
                                "",
                                "Success: BWA functional check passed (Usage output detected).",
                            )

                        # Special case: gatk returns non-zero when run without args
                        if t == "gatk" and "Usage:" in err_out:
                            return (
                                True,
                                "",
                                "Success: GATK functional check passed (Usage output detected).",
                            )

                        # Special case: run_deepvariant returns non-zero when run without args
                        if t == "run_deepvariant" and (
                            "Usage:" in err_out or "run_deepvariant" in err_out
                        ):
                            return (
                                True,
                                "",
                                "Success: DeepVariant functional check passed.",
                            )

                        last_err = f"Exit code {res.returncode}\n{err_out}"
                        if (
                            "library not loaded" in err_out.lower()
                            or "dyld" in err_out.lower()
                        ):
                            return False, " (lib error)", err_out
                    except subprocess.TimeoutExpired:
                        return (
                            True,
                            "",
                            f"Success: Tool '{t}' started successfully (timeout before exit).",
                        )
                    except Exception as e:
                        last_err = str(e)
                        continue

                return False, " (exec error)", last_err
            return True, "", "Success: Tool is present in PATH."

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
            details = ""
            if is_installed:
                version_ok, version_text, details = check_tool_functional(tool)
            else:
                details = f"Error: Tool '{tool}' not found in system PATH."

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

            if details:
                ToolTip(name_lbl, details)
                ToolTip(symbol_lbl, details)

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
        vcf_path = self.main_app.vcf_path_var.get()
        mother_vcf = self.main_app.vcf_mother_var.get()
        father_vcf = self.main_app.vcf_father_var.get()

        # Read existing or create new
        lines = []
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                lines = f.readlines()

        # Update or append variables
        new_lines = []
        updates = {
            "WGSE_REF": ref_path,
            "WGSE_OUTDIR": out_dir,
            "WGSE_YLEAF_PATH": yleaf_path,
            "WGSE_HAPLOGREP_PATH": haplogrep_path,
            "WGSE_INPUT_VCF": vcf_path,
            "WGSE_MOTHER_VCF": mother_vcf,
            "WGSE_FATHER_VCF": father_vcf,
        }
        updated_keys = set()

        for line in lines:
            matched = False
            for key in updates:
                if line.startswith(f"{key}="):
                    new_lines.append(f'{key}="{updates[key]}"\n')
                    updated_keys.add(key)
                    matched = True
                    break
            if not matched:
                new_lines.append(line)

        for key, value in updates.items():
            if key not in updated_keys and value:
                new_lines.append(f'{key}="{value}"\n')

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
