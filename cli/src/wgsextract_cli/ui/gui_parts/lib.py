"""Library management tab frame for reference genomes and VEP cache."""

import re
from typing import Any

import customtkinter as ctk

from wgsextract_cli.core.messages import GUI_LABELS, GUI_TOOLTIPS
from wgsextract_cli.ui.constants import BUTTON_FONT

from .common import ScrollableBaseFrame, ToolTip


class LibFrame(ScrollableBaseFrame):
    """
    A frame for managing reference genomes (downloading, deleting, indexing)
    and VEP (Variant Effect Predictor) caches.
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the library frame."""
        from wgsextract_cli.core.ref_library import (
            get_genome_size,
            get_genome_status,
            get_grouped_genomes,
        )

        # Clear existing widgets if refreshing
        for widget in self.winfo_children():
            widget.destroy()

        super().setup_ui()
        meta = self.meta

        # Action Buttons registry
        self.cmd_buttons: dict[str, ctk.CTkButton] = {}

        # 1. VEP Management Section
        self._setup_vep_mgmt_section(meta["vep_commands"])

        # 2. Reference Management Section
        # This section now contains the library directory selector and general buttons
        self._setup_ref_mgmt_section(meta["commands"])

        # 3. Reference Genome List Section
        self._setup_ref_list_section(
            get_grouped_genomes, get_genome_status, get_genome_size
        )

    def _setup_ref_mgmt_section(self, commands: list[dict[str, Any]]) -> None:
        """Set up the action buttons for general reference management."""
        bf = ctk.CTkFrame(self, fg_color="transparent")
        bf.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            bf,
            text="Reference Management",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(pady=(0, 5))

        # Library Directory selector moved here
        self.lib_dest = self.create_dir_selector(
            self,
            GUI_LABELS["ref_library_path"],
            variable=self.main_app.ref_path_var,
            info_text="Main directory where reference genomes are stored.",
        )

        from wgsextract_cli.core.gene_map import are_gene_maps_installed

        reflib = self.main_app.ref_path_var.get()
        is_gene_map_installed = are_gene_maps_installed(reflib)

        gf = ctk.CTkFrame(self, fg_color="transparent")
        gf.pack(fill="x", padx=20)
        for i, cm in enumerate(commands):
            label = cm["label"]
            cmd = cm["cmd"]
            fg_color = None
            hover_color = None

            if cmd == "ref-gene-map":
                if is_gene_map_installed:
                    label = GUI_LABELS["btn_delete_gm"]
                    fg_color = "#AA3333"
                    hover_color = "#CC4444"
                else:
                    label = GUI_LABELS["btn_download_gm"]

            r, c = divmod(i, 3)
            gf.grid_columnconfigure(c, weight=1)
            btn = ctk.CTkButton(
                gf,
                text=label,
                fg_color=fg_color,
                hover_color=hover_color,
                command=lambda cc=cmd: self.handle_button_click(cc),
                font=BUTTON_FONT,
            )
            btn.grid(row=r, column=c, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cm["help"])
            self.cmd_buttons[cmd] = btn

    def _setup_vep_mgmt_section(self, vep_commands: list[dict[str, Any]]) -> None:
        """Set up the VEP cache management controls and progress bars."""
        vep_f = ctk.CTkFrame(self, fg_color="transparent")
        vep_f.pack(fill="x", padx=20, pady=(20, 10))
        vep_h = ctk.CTkFrame(vep_f, fg_color="transparent")
        vep_h.pack(fill="x")
        ctk.CTkLabel(
            vep_h,
            text=GUI_LABELS["vep_cache_mgmt"],
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")
        v_info = ctk.CTkLabel(
            vep_h,
            text=" ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#55aaff",
            cursor="hand2",
        )
        v_info.pack(side="left", padx=5)
        ToolTip(
            v_info,
            GUI_TOOLTIPS["vep_mgmt_tip"],
        )

        verify_cmd = next(c for c in vep_commands if c["cmd"] == "vep-verify")
        self.vep_cache = self.create_read_only_entry_with_info(
            self,
            GUI_LABELS["vep_cache_path"],
            self.main_app.vep_cache_var,
            GUI_TOOLTIPS["vep_cache_tip"],
            button_text=verify_cmd["label"],
            command=lambda: self.main_app.run_dispatch("vep-verify", self),
        )
        self.cmd_buttons["vep-verify"] = self.vep_cache.action_button
        ToolTip(self.cmd_buttons["vep-verify"], verify_cmd["help"])

        vep_btn_f = ctk.CTkFrame(self, fg_color="transparent")
        vep_btn_f.pack(fill="x", padx=20)

        # Filter out vep-verify as it's now beside the entry
        other_vep_cmds = [c for c in vep_commands if c["cmd"] != "vep-verify"]
        for i, cm in enumerate(other_vep_cmds):
            vep_btn_f.grid_columnconfigure(i, weight=1)
            btn = ctk.CTkButton(
                vep_btn_f,
                text=cm["label"],
                command=lambda cc=cm["cmd"]: self.handle_button_click(cc),
                font=BUTTON_FONT,
            )
            btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
            ToolTip(btn, cm["help"])
            self.cmd_buttons[cm["cmd"]] = btn

        # VEP Progress UI
        self.vep_prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.vep_prog_var = ctk.DoubleVar(value=0)
        self.vep_stat_var = ctk.StringVar(value="")
        self.vep_pbar = ctk.CTkProgressBar(
            self.vep_prog_frame, variable=self.vep_prog_var, width=300
        )
        self.vep_stat_lbl = ctk.CTkLabel(
            self.vep_prog_frame,
            textvariable=self.vep_stat_var,
            font=ctk.CTkFont(size=11),
        )
        self.vep_cancel_btn = ctk.CTkButton(
            self.vep_prog_frame,
            text=GUI_LABELS["btn_cancel"].split("|")[0].strip(),
            width=60,
            fg_color="#666666",
            command=self.main_app.cancel_vep_download,
            font=BUTTON_FONT,
        )

    def _setup_ref_list_section(
        self, get_grouped_genomes: Any, get_genome_status: Any, get_genome_size: Any
    ) -> None:
        """Set up the interactive list of available reference genomes."""
        hf = ctk.CTkFrame(self, fg_color="transparent")
        hf.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            hf,
            text=GUI_LABELS["ref_genomes_list"],
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")
        ii = ctk.CTkLabel(
            hf,
            text=" ⓘ",
            font=ctk.CTkFont(size=14),
            text_color="#55aaff",
            cursor="hand2",
        )
        ii.pack(side="left", padx=5)
        ToolTip(ii, GUI_TOOLTIPS["ref_genomes_tip"])

        # Refresh List button moved here
        ctk.CTkButton(
            hf,
            text=GUI_LABELS["refresh_list"],
            width=100,
            command=self.setup_ui,
            font=BUTTON_FONT,
        ).pack(side="right", padx=10)

        dest = self.main_app.ref_path_var.get()
        grouped = get_grouped_genomes()
        for group in grouped:
            self._create_genome_row(group, dest, get_genome_status, get_genome_size)

    def _create_genome_row(
        self,
        group: dict[str, Any],
        dest: str,
        get_genome_status: Any,
        get_genome_size: Any,
    ) -> None:
        """Create a single row for a reference genome in the list."""
        row = ctk.CTkFrame(self)
        row.pack(fill="x", padx=20, pady=5)
        fn = group["final"]
        lt = group["label"]
        s = get_genome_status(fn, dest)
        sz = get_genome_size(fn, dest)
        sl = f" ({sz})" if sz else ""

        # Tags processing
        tags = []
        if "(Rec)" in lt:
            tags.append((GUI_LABELS["recommended_tag"], "#228822"))
            lt = lt.replace("(Rec)", "").strip()
        lt = re.sub(r"\s+", " ", lt).strip(" -_")

        ctk.CTkLabel(
            row, text=f"{lt}{sl}", anchor="w", font=ctk.CTkFont(weight="bold")
        ).pack(side="left", padx=10)

        for tt, tc in tags:
            ctk.CTkLabel(
                row,
                text=tt,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=tc,
                text_color="white",
                corner_radius=10,
                padx=6,
                pady=0,
                height=16,
            ).pack(side="left", padx=2)

        if fn in self.main_app.active_downloads:
            self._add_download_status(row, fn)
        elif s == "installed":
            self._add_installed_controls(row, group)
        elif s == "unindexed":
            self._add_unindexed_controls(row, group)
        elif s == "incomplete":
            self._add_incomplete_controls(row, group)
        else:
            self._add_available_controls(row, group)

    def _add_download_status(self, row: ctk.CTkFrame, fn: str) -> None:
        di = self.main_app.active_downloads[fn]
        dc = ctk.CTkFrame(row, fg_color="transparent")
        dc.pack(side="right", padx=10)

        pbar = ctk.CTkProgressBar(dc, variable=di["progress_var"], width=150)
        pbar.pack(side="left", padx=5)
        di["pbar_widget"] = pbar

        ctk.CTkLabel(dc, textvariable=di["status_var"], font=ctk.CTkFont(size=10)).pack(
            side="left", padx=5
        )
        cbtn = ctk.CTkButton(
            dc,
            text=GUI_LABELS["btn_cancel"],
            width=80,
            fg_color=("#cfd8dc", "#455a64"),
            hover_color=("#b0bec5", "#37474f"),
            text_color=("#000000", "#ffffff"),
            command=lambda f=fn: self.main_app.cancel_lib_download(f),
            font=BUTTON_FONT,
        )
        cbtn.pack(side="left", padx=5)

        # Register for spinner
        cmd_key = f"cancel-dl-{fn}"
        self.cmd_buttons[cmd_key] = cbtn
        self.running_spinners[cmd_key] = True
        self._animate_spinner(cmd_key)

    def _add_installed_controls(self, row: ctk.CTkFrame, group: dict[str, Any]) -> None:
        from wgsextract_cli.core.ref_library import has_ref_ns

        dest = self.main_app.ref_path_var.get()
        fn = group["final"]

        # Delete button
        del_btn = ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_delete"],
            width=60,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_lib_delete(g, self),
            font=BUTTON_FONT,
        )
        del_btn.pack(side="right", padx=5)
        ToolTip(del_btn, f"Remove {group['final']} and index files.")

        # Verify button
        ver_btn = ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_verify"],
            width=60,
            command=lambda g=group: self.main_app.run_ref_verify(g, self),
            font=BUTTON_FONT,
        )
        ver_btn.pack(side="right", padx=5)
        ToolTip(ver_btn, f"Verify integrity of {group['final']}.")
        self.cmd_buttons[f"verify-{group['final']}"] = ver_btn

        # Unindex button
        unidx_btn = ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_unindex"],
            width=65,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_ref_unindex(g, self),
            font=BUTTON_FONT,
        )
        unidx_btn.pack(side="right", padx=5)
        ToolTip(unidx_btn, f"Remove index files for {group['final']}.")

        # Count Ns / Del Ns button
        if has_ref_ns(fn, dest):
            ns_btn = ctk.CTkButton(
                row,
                text=GUI_LABELS["btn_del_ns"],
                width=70,
                fg_color="#992222",
                hover_color="#bb3333",
                command=lambda g=group: self.main_app.run_ref_del_ns(g, self),
                font=BUTTON_FONT,
            )
            ToolTip(ns_btn, f"Remove N-count CSV files for {group['final']}.")
            self.cmd_buttons[f"del-ns-{group['final']}"] = ns_btn
        else:
            ns_btn = ctk.CTkButton(
                row,
                text=GUI_LABELS["btn_count_ns"],
                width=70,
                command=lambda g=group: self.main_app.run_ref_count_ns(g, self),
                font=BUTTON_FONT,
            )
            ToolTip(ns_btn, f"Analyze N segments in {group['final']}.")
            self.cmd_buttons[f"count-ns-{group['final']}"] = ns_btn
        ns_btn.pack(side="right", padx=5)

    def _add_unindexed_controls(self, row: ctk.CTkFrame, group: dict[str, Any]) -> None:
        from wgsextract_cli.core.ref_library import has_ref_ns

        dest = self.main_app.ref_path_var.get()
        fn = group["final"]

        # Delete button
        del_btn = ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_delete"],
            width=60,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_lib_delete(g, self),
            font=BUTTON_FONT,
        )
        del_btn.pack(side="right", padx=5)

        # Index button (required)
        idx_btn = ctk.CTkButton(
            row,
            text="Index",
            width=60,
            fg_color="#aa6622",
            hover_color="#cc8844",
            command=lambda g=group: self.main_app.run_ref_index(g, self),
            font=BUTTON_FONT,
        )
        idx_btn.pack(side="right", padx=5)
        ToolTip(idx_btn, f"Generate required index for {group['final']}.")
        self.cmd_buttons[f"index-{group['final']}"] = idx_btn

        # Count Ns / Del Ns button
        if has_ref_ns(fn, dest):
            ns_btn = ctk.CTkButton(
                row,
                text=GUI_LABELS["btn_del_ns"],
                width=70,
                fg_color="#992222",
                hover_color="#bb3333",
                command=lambda g=group: self.main_app.run_ref_del_ns(g, self),
                font=BUTTON_FONT,
            )
            ToolTip(ns_btn, f"Remove N-count CSV files for {group['final']}.")
            self.cmd_buttons[f"del-ns-{group['final']}"] = ns_btn
        else:
            ns_btn = ctk.CTkButton(
                row,
                text=GUI_LABELS["btn_count_ns"],
                width=70,
                command=lambda g=group: self.main_app.run_ref_count_ns(g, self),
                font=BUTTON_FONT,
            )
            ToolTip(ns_btn, f"Analyze N segments in {group['final']}.")
            self.cmd_buttons[f"count-ns-{group['final']}"] = ns_btn
        ns_btn.pack(side="right", padx=5)

        ctk.CTkLabel(
            row,
            text=GUI_LABELS["needs_index_tag"],
            text_color="#ffaa00",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="right", padx=10)

    def _add_incomplete_controls(
        self, row: ctk.CTkFrame, group: dict[str, Any]
    ) -> None:
        ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_delete"],
            width=70,
            fg_color="#992222",
            hover_color="#bb3333",
            command=lambda g=group: self.main_app.run_lib_delete(g, self),
            font=BUTTON_FONT,
        ).pack(side="right", padx=10)
        ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_restart"],
            width=70,
            fg_color="#aa6622",
            hover_color="#cc8844",
            command=lambda g=group: self.main_app.run_lib_download(
                g["sources"][0], self, restart=True
            ),
            font=BUTTON_FONT,
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            row,
            text=GUI_LABELS["btn_resume"],
            width=70,
            fg_color="#228822",
            hover_color="#33aa33",
            command=lambda g=group: self.main_app.run_lib_download(
                g["sources"][0], self
            ),
            font=BUTTON_FONT,
        ).pack(side="right", padx=5)
        ctk.CTkLabel(
            row,
            text=GUI_LABELS["incomplete_tag"],
            text_color="#ffaa00",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="right", padx=10)

    def _add_available_controls(self, row: ctk.CTkFrame, group: dict[str, Any]) -> None:
        for sd in reversed(group["sources"]):
            sb = ctk.CTkButton(
                row,
                text=sd["source"],
                width=60,
                command=lambda s=sd: self.main_app.run_lib_download(s, self),
                font=BUTTON_FONT,
            )
            sb.pack(side="right", padx=5)
            ToolTip(sb, f"Download from {sd['source']}")
        ctk.CTkLabel(
            row, text="download from", font=ctk.CTkFont(size=11, slant="italic")
        ).pack(side="right", padx=5)

    def show_vep_progress(self) -> None:
        """Display the VEP progress bar and status labels."""
        if self.winfo_exists():
            self.vep_prog_frame.pack(fill="x", padx=20, pady=5)
            self.vep_pbar.pack(side="left", padx=5)
            self.vep_stat_lbl.pack(side="left", padx=5)
            self.vep_cancel_btn.pack(side="left", padx=5)

            # Start spinner on VEP cancel button
            cmd_key = "vep-cancel"
            self.cmd_buttons[cmd_key] = self.vep_cancel_btn
            self.vep_cancel_btn.configure(
                text=GUI_LABELS["btn_cancel"],
                fg_color=("#cfd8dc", "#455a64"),
                hover_color=("#b0bec5", "#37474f"),
                text_color=("#000000", "#ffffff"),
            )
            self.running_spinners[cmd_key] = True
            self._animate_spinner(cmd_key)

    def hide_vep_progress(self) -> None:
        """Hide the VEP progress UI elements."""
        if self.winfo_exists():
            if "vep-cancel" in self.running_spinners:
                del self.running_spinners["vep-cancel"]
            self.vep_prog_frame.pack_forget()
            self.vep_pbar.pack_forget()
            self.vep_stat_lbl.pack_forget()
            self.vep_cancel_btn.pack_forget()

    def set_button_state(self, cmd_key: str, state: str) -> None:
        """Update button text and color based on execution state."""
        if not self.winfo_exists() or cmd_key not in self.cmd_buttons:
            return

        btn = self.cmd_buttons[cmd_key]
        if state == "running":
            self.running_spinners[cmd_key] = True
            btn.configure(
                text=GUI_LABELS["btn_cancel"],
                fg_color=("#cfd8dc", "#455a64"),
                hover_color=("#b0bec5", "#37474f"),
                text_color=("#000000", "#ffffff"),
                command=lambda: self.main_app.controller.cancel_cmd(cmd_key),
            )
            self._animate_spinner(cmd_key)
        else:
            if cmd_key in self.running_spinners:
                del self.running_spinners[cmd_key]
            # Restore original label and color
            label = ""
            if cmd_key.startswith("verify-"):
                label = GUI_LABELS["btn_verify"]
            elif cmd_key.startswith("index-"):
                label = "Index"
            elif cmd_key.startswith("count-ns-"):
                label = GUI_LABELS["btn_count_ns"]
            elif cmd_key.startswith("del-ns-"):
                label = GUI_LABELS["btn_del_ns"]
            else:
                all_cmds = self.meta["commands"] + self.meta["vep_commands"]
                label = next(c["label"] for c in all_cmds if c["cmd"] == cmd_key)

            orig_color = ("#3a7ebf", "#1f538d")
            orig_hover = ("#325882", "#14375e")
            orig_text = "#ffffff"

            if cmd_key.startswith("index-"):
                orig_color = ("#aa6622", "#aa6622")
                orig_hover = ("#cc8844", "#cc8844")
            elif (
                cmd_key.startswith("del-ns-")
                or cmd_key == "lib-delete"
                or "delete" in cmd_key
                or cmd_key.startswith("unindex-")
                or "unindex" in cmd_key
            ):
                orig_color = ("#992222", "#992222")
                orig_hover = ("#bb3333", "#bb3333")

            # Restore original command
            if cmd_key.startswith("verify-"):
                fname = cmd_key.replace("verify-", "")

                def cmd_func_v():
                    return self.main_app.run_ref_verify({"final": fname}, self)

                cmd_func = cmd_func_v
            elif cmd_key.startswith("index-"):
                fname = cmd_key.replace("index-", "")

                def cmd_func_i():
                    return self.main_app.run_ref_index({"final": fname}, self)

                cmd_func = cmd_func_i
            elif cmd_key.startswith("count-ns-"):
                fname = cmd_key.replace("count-ns-", "")

                def cmd_func_ns():
                    return self.main_app.run_ref_count_ns({"final": fname}, self)

                cmd_func = cmd_func_ns
            elif cmd_key.startswith("del-ns-"):
                fname = cmd_key.replace("del-ns-", "")

                def cmd_func_dns():
                    return self.main_app.run_ref_del_ns({"final": fname}, self)

                cmd_func = cmd_func_dns
            else:

                def cmd_func_d(cc=cmd_key):
                    if cc == "vep-verify":
                        return self.main_app.run_dispatch("vep-verify", self)
                    return self.main_app.run_dispatch(cc, self)

                cmd_func = cmd_func_d

            btn.configure(
                text=label,
                fg_color=orig_color,
                hover_color=orig_hover,
                text_color=orig_text,
                command=cmd_func,
            )
