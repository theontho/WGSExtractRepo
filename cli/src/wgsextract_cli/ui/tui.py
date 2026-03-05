import os
import subprocess
import sys
import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
    SelectionList,
    TabbedContent,
    TabPane,
)
from textual.widgets.selection_list import Selection

from wgsextract_cli.ui.constants import MICROARRAY_FORMATS, UI_METADATA


class WGSExtractTUI(App):
    """A metadata-driven TUI for WGS Extract."""

    CSS = """
    TabPane { padding: 1; }
    .field { margin-bottom: 1; }
    .field Label { width: 15; }
    .sub-section { border: tall $accent; margin-bottom: 1; padding: 1; }
    #output { height: 1fr; border: solid green; margin-top: 1; }
    #lib_progress_container { height: auto; margin-top: 1; display: none; }
    #lib_progress_container.active { display: block; }
    #vep_progress_container { height: auto; margin-top: 1; display: none; }
    #vep_progress_container.active { display: block; }
    """
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        from wgsextract_cli.core.ref_library import (
            get_available_genomes,
            get_genome_status,
        )

        yield Header()
        with TabbedContent():
            for key, meta in UI_METADATA.items():
                with TabPane(meta["title"], id=f"{key}_tab"):
                    yield Label(meta["help"])
                    if key == "lib":
                        ld = os.environ.get("WGSE_REF", "")
                        yield Horizontal(
                            Label("Library Dir:"),
                            Input(value=ld, id="lib_dest"),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("Input:"),
                            Input(value=os.environ.get("WGSE_INPUT", ""), id="lib_in"),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("Ref:"),
                            Input(value=os.environ.get("WGSE_REF", ""), id="lib_ref"),
                            classes="field",
                        )

                        with Vertical(classes="sub-section"):
                            yield Label("Reference Management", classes="field")
                            for cm in meta["commands"]:
                                yield Button(cm["label"], id=f"btn_{cm['cmd']}")

                        with Vertical(classes="sub-section"):
                            yield Label("VEP Cache Management", classes="field")
                            yield Label(
                                "VEP determines how variants affect genes. This cache is stored in your library.",
                                classes="field",
                            )
                            dv = (
                                os.path.join(ld, "vep")
                                if ld and os.path.isdir(ld)
                                else os.path.expanduser("~/.vep")
                            )
                            yield Horizontal(
                                Label("VEP Cache:"),
                                Input(value=dv, id="vep_cache"),
                                classes="field",
                            )
                            for cm in meta["vep_commands"]:
                                yield Button(cm["label"], id=f"btn_{cm['cmd']}")
                            yield Button(
                                "Cancel VEP Download",
                                id="btn_vep_cancel",
                                variant="warning",
                            )
                            with Vertical(id="vep_progress_container"):
                                yield Label(
                                    "VEP Cache Progress...", id="vep_progress_label"
                                )
                                yield ProgressBar(
                                    id="vep_progress_bar",
                                    total=100,
                                    show_percentage=True,
                                )

                        yield Label("Reference Genomes", classes="field")
                        from wgsextract_cli.core.ref_library import get_genome_size

                        ag = get_available_genomes()
                        sel = []
                        for i, g in enumerate(ag):
                            s = get_genome_status(g["final"], ld)
                            st = (
                                "[INSTALLED] "
                                if s == "installed"
                                else "[INCOMPLETE] "
                                if s == "incomplete"
                                else ""
                            )
                            sz = get_genome_size(g["final"], ld)
                            sl = f" ({sz})" if sz else ""
                            lt = g["label"]
                            (
                                lt := lt.replace("(Rec)", "").strip()
                                + " [on green]Recommended[/]"
                            ) if "(Rec)" in lt else None
                            sel.append(Selection(f"{st}{lt}{sl}", i))
                        yield SelectionList(*sel, id="lib_selection")
                        yield Horizontal(
                            Button("Download / Resume", id="btn_lib_download"),
                            Button(
                                "Restart Download",
                                id="btn_lib_restart",
                                variant="warning",
                            ),
                            Button(
                                "Delete Selected", id="btn_lib_delete", variant="error"
                            ),
                            Button("Cancel", id="btn_lib_cancel", variant="warning"),
                        )
                        with Vertical(id="lib_progress_container"):
                            yield Label("Downloading...", id="lib_progress_label")
                            yield ProgressBar(
                                id="lib_progress_bar", total=100, show_percentage=True
                            )
                        continue
                    if key == "micro":
                        yield Horizontal(
                            Label("Input:"),
                            Input(
                                value=os.environ.get("WGSE_INPUT", ""), id="micro_in"
                            ),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("Ref:"),
                            Input(value=os.environ.get("WGSE_REF", ""), id="micro_ref"),
                            classes="field",
                        )
                        yield Label("Select Target Formats:", classes="field")
                        fmts = [
                            Selection(f["label"], f["id"], f.get("recommended", False))
                            for f in MICROARRAY_FORMATS
                        ]
                        yield SelectionList(*fmts, id="micro_formats")
                        yield Horizontal(
                            Button("Select All", id="btn_micro_all"),
                            Button("Unselect All", id="btn_micro_none"),
                            Button("Select Recommended", id="btn_micro_rec"),
                        )
                        with Vertical(classes="sub-section"):
                            for cm in meta["commands"]:
                                yield Button(cm["label"], id=f"btn_{cm['cmd']}")
                        continue
                    if key in ["gen", "bam", "ext", "anc", "qc", "vcf"]:
                        yield Horizontal(
                            Label("Input:"),
                            Input(
                                value=os.environ.get("WGSE_INPUT", ""), id=f"{key}_in"
                            ),
                            classes="field",
                        )
                    if key in ["gen", "bam", "vcf"]:
                        yield Horizontal(
                            Label("Ref:"),
                            Input(
                                value=os.environ.get("WGSE_REF", ""), id=f"{key}_ref"
                            ),
                            classes="field",
                        )
                    if key == "gen":
                        yield Horizontal(
                            Label("Region:"),
                            Input(placeholder="e.g. chrM", id="gen_region"),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("FASTQ R1:"), Input(id="align_r1"), classes="field"
                        )
                    elif key == "bam":
                        yield Horizontal(
                            Label("Extra (Frac):"),
                            Input(id="bam_extra"),
                            classes="field",
                        )
                    elif key == "ext":
                        yield Horizontal(
                            Label("Out Dir:"),
                            Input(
                                value=os.environ.get("WGSE_OUTDIR", ""), id="ext_out"
                            ),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("Custom Reg:"),
                            Input(id="ext_region"),
                            classes="field",
                        )
                    elif key == "anc":
                        yield Horizontal(
                            Label("Yleaf Path:"),
                            Input(id="yleaf_path"),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("Pos File:"), Input(id="yleaf_pos"), classes="field"
                        )
                        yield Horizontal(
                            Label("Haplogrep:"),
                            Input(id="haplogrep_path"),
                            classes="field",
                        )
                    elif key == "vcf":
                        yield Horizontal(
                            Label("Mother/Ann:"), Input(id="vcf_e1"), classes="field"
                        )
                        yield Horizontal(
                            Label("Father/Expr:"), Input(id="vcf_e2"), classes="field"
                        )
                        yield Horizontal(
                            Label("Gene/Reg:"), Input(id="vcf_e3"), classes="field"
                        )
                        yield Horizontal(
                            Label("VEP Cache:"),
                            Input(
                                value=os.path.expanduser("~/.vep"), id="vcf_vep_cache"
                            ),
                            classes="field",
                        )
                        yield Horizontal(
                            Label("VEP Args:"),
                            Input(id="vcf_vep_args"),
                            classes="field",
                        )
                    with Vertical(classes="sub-section"):
                        for cm in meta["commands"]:
                            yield Button(cm["label"], id=f"btn_{cm['cmd']}")
        yield Log(id="output")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib_cancel":
            if hasattr(self, "lib_cancel_event"):
                self.lib_cancel_event.set()
                self.query_one("#output", Log).write_line("Cancellation requested...")
            return
        if event.button.id == "btn_vep_cancel":
            if hasattr(self, "vep_cancel_event") and self.vep_cancel_event:
                self.vep_cancel_event.set()
                self.query_one("#output", Log).write_line(
                    "VEP Cancellation requested..."
                )
            return
        if event.button.id in ["btn_lib_download", "btn_lib_delete", "btn_lib_restart"]:
            indices = self.query_one("#lib_selection", SelectionList).selected
            dest = self.query_one("#lib_dest", Input).value
            if not indices:
                return
            from wgsextract_cli.core.ref_library import (
                download_and_process_genome,
                get_available_genomes,
            )

            ag = get_available_genomes()
            log = self.query_one("#output", Log)
            pbc = self.query_one("#lib_progress_container")
            pb = self.query_one("#lib_progress_bar", ProgressBar)
            pl = self.query_one("#lib_progress_label", Label)

            def cb(d, t, s):
                pct = (d / t * 100) if t > 0 else 0
                st = (
                    f"{s / (1024 * 1024):.1f} MB/s"
                    if s > 1024 * 1024
                    else f"{s / 1024:.1f} KB/s"
                )
                self.call_from_thread(
                    lambda: (
                        setattr(pb, "progress", pct),
                        pl.update(f"Downloading: {pct:.1f}% at {st}"),
                    )
                )

            self.lib_cancel_event = threading.Event()

            def run():
                self.call_from_thread(pbc.add_class, "active")
                for idx in indices:
                    if self.lib_cancel_event.is_set():
                        self.call_from_thread(log.write_line, "Batch cancelled.")
                        break
                    g = ag[idx]
                    rs = event.button.id == "btn_lib_restart"
                    self.call_from_thread(
                        log.write_line,
                        f"{'Restarting' if rs else 'Downloading'} {g['final']}...",
                    )
                    success = download_and_process_genome(
                        g,
                        dest,
                        interactive=False,
                        progress_callback=cb,
                        cancel_event=self.lib_cancel_event,
                        restart=rs,
                    )
                    self.call_from_thread(
                        log.write_line,
                        f"Result: {'Success' if success else 'Failed/Cancelled'}",
                    )
                self.call_from_thread(pbc.remove_class, "active")
                self.call_from_thread(log.write_line, "Tasks completed.")

            threading.Thread(target=run, daemon=True).start()
            return
        if event.button.id == "btn_micro_all":
            self.query_one("#micro_formats", SelectionList).select_all()
            return
        if event.button.id == "btn_micro_none":
            self.query_one("#micro_formats", SelectionList).deselect_all()
            return
        if event.button.id == "btn_micro_rec":
            sel = self.query_one("#micro_formats", SelectionList)
            sel.deselect_all()
            for f in MICROARRAY_FORMATS:
                (sel.select(f["id"]) if f.get("recommended") else None)
                return
        if not event.button.id.startswith("btn_"):
            return
        self.run_dispatch(event.button.id.replace("btn_", ""))

    def run_dispatch(self, cmd):
        bc = [sys.executable, "-m", "wgsextract_cli.main"]
        log = self.query_one("#output", Log)

        def val(id):
            try:
                return self.query_one(f"#{id}", Input).value
            except:
                return ""

        c = bc
        if cmd == "vep-download":
            pbc = self.query_one("#vep_progress_container")
            pb = self.query_one("#vep_progress_bar", ProgressBar)
            pl = self.query_one("#vep_progress_label", Label)

            def cb(d, t, s):
                pct = (d / t * 100) if t > 0 else 0
                st = (
                    f"{s / (1024 * 1024):.1f} MB/s"
                    if s > 1024 * 1024
                    else f"{s / 1024:.1f} KB/s"
                )
                self.call_from_thread(
                    lambda: (
                        setattr(pb, "progress", pct),
                        pl.update(f"Downloading: {pct:.1f}% at {st}"),
                    )
                )

            def run():
                from wgsextract_cli.commands.vep import cmd_vep_download

                class Args:
                    pass

                a = Args()
                a.vep_version = "115"
                a.species = "homo_sapiens"
                a.assembly = "GRCh38"
                a.mirror = "uk"
                a.vep_cache = val("vep_cache")
                a.ref = val("lib_ref")
                a.progress_callback = cb
                self.vep_cancel_event = threading.Event()
                a.cancel_event = self.vep_cancel_event
                self.call_from_thread(pbc.add_class, "active")
                self.call_from_thread(log.write_line, "Starting VEP cache download...")
                try:
                    success = cmd_vep_download(a)
                    self.call_from_thread(
                        log.write_line,
                        f"VEP Download {'Succeeded' if success else 'Failed/Cancelled'}",
                    )
                except Exception as e:
                    self.call_from_thread(log.write_line, f"Error: {e}")
                finally:
                    self.call_from_thread(pbc.remove_class, "active")
                    self.vep_cancel_event = None

            threading.Thread(target=run, daemon=True).start()
            return
        if cmd == "info":
            c += [
                "info",
                "--input",
                val("gen_in"),
                "--ref",
                val("gen_ref"),
                "--detailed",
            ]
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c += ["info", cmd, "--input", val("gen_in")]
            (c.extend(["-r", val("gen_region")]) if val("gen_region") else None)
        elif cmd == "align":
            c += ["align", "--input", val("align_r1"), "--ref", val("gen_ref")]
        elif cmd in [
            "sort",
            "index",
            "unindex",
            "unsort",
            "to-cram",
            "to-bam",
            "unalign",
            "subset",
            "mt-extract",
        ]:
            c += ["bam", cmd, "--input", val("bam_in")]
            (c.extend(["--ref", val("bam_ref")]) if val("bam_ref") else None)
            (
                c.append(val("bam_extra"))
                if cmd == "subset" and val("bam_extra")
                else None
            )
        elif cmd.startswith("repair-"):
            c += ["repair", cmd.replace("repair-", ""), "--input", val("bam_in")]
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c += ["extract"]
            (
                c.extend(["--input", val("ext_in"), "-r", val("ext_region")])
                if cmd == "custom"
                else c.extend([cmd, "--input", val("ext_in")])
            )
            (c.extend(["--outdir", val("ext_out")]) if val("ext_out") else None)
        elif cmd in [
            "snp",
            "indel",
            "sv",
            "cnv",
            "freebayes",
            "gatk",
            "deepvariant",
            "annotate",
            "filter",
            "trio",
            "vcf-qc",
            "vep-run",
        ]:
            sub = (
                "qc"
                if cmd == "vcf-qc"
                else cmd.replace("vep-", "")
                if "vep-" in cmd
                else cmd
            )
            c += ["vep" if "vep-" in cmd else "vcf", sub]
            if sub == "trio":
                c += [
                    "--proband",
                    val("vcf_in"),
                    "--mother",
                    val("vcf_e1"),
                    "--father",
                    val("vcf_e2"),
                ]
            elif sub == "run":
                c += ["--input", val("vcf_in"), "--ref", val("vcf_ref")]
            else:
                c += ["--input", val("vcf_in")]
            if val("vcf_ref"):
                c += ["--ref", val("vcf_ref")]
            if sub == "annotate" and val("vcf_e1"):
                c += ["--ann-vcf", val("vcf_e1")]
            if sub == "filter":
                (c.extend(["--expr", val("vcf_e2")]) if val("vcf_e2") else None)
                (c.extend(["--gene", val("vcf_e3")]) if val("vcf_e3") else None)
            if sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"] and val(
                "vcf_e3"
            ):
                c += ["-r", val("vcf_e3")]
            if "vep" in cmd:
                cv = val("vep_cache") if "vep" in cmd else val("vcf_vep_cache")
                if cv:
                    c += ["--vep-cache", cv]
                if sub == "run" and val("vcf_vep_args"):
                    c += ["--vep-args", val("vcf_vep_args")]
        elif cmd == "microarray":
            s = self.query_one("#micro_formats", SelectionList).selected
            if not s:
                self.query_one("#output", Log).write_line("Error: No formats selected.")
                return
            c += [
                "microarray",
                "--input",
                val("micro_in"),
                "--ref",
                val("micro_ref"),
                "--formats",
                ",".join(s),
            ]
        elif cmd == "lineage-y":
            c += [
                "lineage",
                "y-dna",
                "--input",
                val("anc_in"),
                "--yleaf-path",
                val("yleaf_path"),
                "--pos-file",
                val("yleaf_pos"),
            ]
        elif cmd == "lineage-mt":
            c += [
                "lineage",
                "mt-dna",
                "--input",
                val("anc_in"),
                "--haplogrep-path",
                val("haplogrep_path"),
            ]
        elif cmd in ["fastqc", "fastp"]:
            c += ["qc", cmd, "--input", val("qc_in")]
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c += ["ref", sub]
            if sub == "identify":
                c += ["--input", val("lib_in")]
            if sub not in ["download", "download-genes"] and val("lib_ref"):
                c += ["--ref", val("lib_ref")]

        def run_t():
            p = subprocess.Popen(
                c,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            for l in p.stdout:
                self.call_from_thread(
                    self.query_one("#output", Log).write_line, l.strip()
                )
            p.wait()
            self.call_from_thread(
                self.query_one("#output", Log).write_line,
                f"Finished (Exit {p.returncode})",
            )

        self.query_one("#output", Log).write_line(f"Running: {' '.join(c)}")
        threading.Thread(target=run_t, daemon=True).start()

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark


def main():
    WGSExtractTUI().run()


if __name__ == "__main__":
    main()
