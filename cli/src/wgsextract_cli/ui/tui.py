from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane, Input, Button, Label, Log, SelectionList, ProgressBar
from textual.widgets.selection_list import Selection
from textual.containers import Vertical, Horizontal
import subprocess
import threading
import os
import sys
from wgsextract_cli.ui.constants import UI_METADATA

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
    """
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        from wgsextract_cli.core.ref_library import get_available_genomes, get_genome_status
        yield Header()
        with TabbedContent():
            for key, meta in UI_METADATA.items():
                with TabPane(meta["title"], id=f"{key}_tab"):
                    yield Label(meta["help"])
                    
                    if key == "lib":
                        lib_dir = os.environ.get("WGSE_REF", "")
                        yield Horizontal(Label("Library Dir:"), Input(value=lib_dir, id="lib_dest"), classes="field")
                        yield Horizontal(Label("Input:"), Input(value=os.environ.get("WGSE_INPUT", ""), id="lib_in"), classes="field")
                        yield Horizontal(Label("Ref:"), Input(value=os.environ.get("WGSE_REF", ""), id="lib_ref"), classes="field")
                        
                        with Vertical(classes="sub-section"):
                            yield Label("Reference Management", classes="field")
                            for cmd_meta in meta["commands"]:
                                yield Button(cmd_meta["label"], id=f"btn_{cmd_meta['cmd']}")

                        all_genomes = get_available_genomes()
                        selections = []
                        import re
                        for i, g in enumerate(all_genomes):
                            status = get_genome_status(g["final"], lib_dir)
                            if status == "installed": status_txt = "[INSTALLED] "
                            elif status == "incomplete": status_txt = "[INCOMPLETE] "
                            else: status_txt = ""
                            
                            label_txt = g['label']
                            description = g.get('description', '')
                            code = g.get('code', '')

                            # Determine Tags (for rich text styling)
                            tags = []
                            # 1. Recommended
                            if "(Rec)" in label_txt:
                                tags.append("[on green]Recommended[/]")
                                label_txt = label_txt.replace("(Rec)", "").strip()
                            
                            # Final label cleanup
                            label_txt = re.sub(r'\s+', ' ', label_txt).strip(" -_")
                            
                            tag_str = " ".join(tags)
                            full_label = f"{status_txt}{label_txt} {tag_str}"
                            selections.append(Selection(full_label, i))
                        
                        yield SelectionList(*selections, id="lib_selection")
                        yield Horizontal(
                            Button("Download / Resume", id="btn_lib_download"),
                            Button("Restart Download", id="btn_lib_restart", variant="warning"),
                            Button("Delete Selected", id="btn_lib_delete", variant="error"),
                            Button("Cancel", id="btn_lib_cancel", variant="warning")
                        )
                        with Vertical(id="lib_progress_container"):
                            yield Label("Downloading...", id="lib_progress_label")
                            yield ProgressBar(id="lib_progress_bar", total=100, show_percentage=True)
                        
                        continue

                    # Common Inputs
                    if key in ["gen", "bam", "ext", "vcf", "anc", "qc", "lib"]:
                        yield Horizontal(Label("Input:"), Input(value=os.environ.get("WGSE_INPUT", ""), id=f"{key}_in"), classes="field")
                    if key in ["gen", "bam", "vcf", "lib"]:
                        yield Horizontal(Label("Ref:"), Input(value=os.environ.get("WGSE_REF", ""), id=f"{key}_ref"), classes="field")
                    
                    # Specialized Inputs
                    if key == "gen":
                        yield Horizontal(Label("Region:"), Input(placeholder="e.g. chrM", id="gen_region"), classes="field")
                        yield Horizontal(Label("FASTQ R1:"), Input(id="align_r1"), classes="field")
                    elif key == "bam":
                        yield Horizontal(Label("Extra (Frac):"), Input(id="bam_extra"), classes="field")
                    elif key == "ext":
                        yield Horizontal(Label("Out Dir:"), Input(value=os.environ.get("WGSE_OUTDIR", ""), id="ext_out"), classes="field")
                        yield Horizontal(Label("Custom Reg:"), Input(id="ext_region"), classes="field")
                    elif key == "vcf":
                        yield Horizontal(Label("Mother/Ann:"), Input(id="vcf_e1"), classes="field")
                        yield Horizontal(Label("Father/Expr:"), Input(id="vcf_e2"), classes="field")
                        yield Horizontal(Label("Gene/Reg:"), Input(id="vcf_e3"), classes="field")
                        yield Horizontal(Label("VEP Cache:"), Input(value=os.path.expanduser("~/.vep"), id="vep_cache"), classes="field")
                        yield Horizontal(Label("VEP Args:"), Input(id="vep_args"), classes="field")
                    elif key == "anc":
                        yield Horizontal(Label("Yleaf Path:"), Input(id="yleaf_path"), classes="field")
                        yield Horizontal(Label("Pos File:"), Input(id="yleaf_pos"), classes="field")
                        yield Horizontal(Label("Haplogrep:"), Input(id="haplogrep_path"), classes="field")

                    with Vertical(classes="sub-section"):
                        for cmd_meta in meta["commands"]:
                            yield Button(cmd_meta["label"], id=f"btn_{cmd_meta['cmd']}")

        yield Log(id="output")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_lib_cancel":
            if hasattr(self, "lib_cancel_event"):
                self.lib_cancel_event.set()
                log = self.query_one("#output", Log)
                log.write_line("Cancellation requested...")
            return

        if event.button.id in ["btn_lib_download", "btn_lib_delete", "btn_lib_restart"]:
            indices = self.query_one("#lib_selection", SelectionList).selected
            dest = self.query_one("#lib_dest", Input).value
            if not indices: return
            
            from wgsextract_cli.core.ref_library import get_available_genomes, download_and_process_genome, delete_genome
            all_genomes = get_available_genomes()
            log = self.query_one("#output", Log)
            
            pbar_container = self.query_one("#lib_progress_container")
            pbar = self.query_one("#lib_progress_bar", ProgressBar)
            plabel = self.query_one("#lib_progress_label", Label)

            def progress_cb(downloaded, total, speed):
                pct = (downloaded / total * 100) if total > 0 else 0
                if speed > 1024 * 1024:
                    speed_txt = f"{speed / (1024 * 1024):.1f} MB/s"
                else:
                    speed_txt = f"{speed / 1024:.1f} KB/s"
                
                def update_ui():
                    pbar.progress = pct
                    plabel.update(f"Downloading: {int(pct)}% at {speed_txt}")
                self.call_from_thread(update_ui)

            self.lib_cancel_event = threading.Event()

            def run():
                self.call_from_thread(pbar_container.add_class, "active")
                for idx in indices:
                    if self.lib_cancel_event.is_set():
                        self.call_from_thread(log.write_line, "Batch cancelled.")
                        break
                    g = all_genomes[idx]
                    if event.button.id in ["btn_lib_download", "btn_lib_restart"]:
                        restart = (event.button.id == "btn_lib_restart")
                        action = "Restarting" if restart else "Downloading/Resuming"
                        self.call_from_thread(log.write_line, f"{action} {g['final']}...")
                        self.call_from_thread(plabel.update, f"{action} {g['final']}...")
                        success = download_and_process_genome(g, dest, interactive=False, 
                                                              progress_callback=progress_cb,
                                                              cancel_event=self.lib_cancel_event,
                                                              restart=restart)
                        self.call_from_thread(log.write_line, f"Result: {'Success' if success else 'Failed/Cancelled'}")
                    else:
                        self.call_from_thread(log.write_line, f"Deleting {g['final']}...")
                        delete_genome(g['final'], dest)
                
                self.call_from_thread(pbar_container.remove_class, "active")
                self.call_from_thread(log.write_line, "Tasks completed. (Select tab again to refresh list status)")
                if hasattr(self, "lib_cancel_event"):
                    del self.lib_cancel_event

            threading.Thread(target=run, daemon=True).start()
            return

        if not event.button.id.startswith("btn_"): return
        cmd = event.button.id.replace("btn_", "")
        self.run_dispatch(cmd)

    def run_dispatch(self, cmd):
        base_cmd = [sys.executable, "-m", "wgsextract_cli.main"]
        log = self.query_one("#output", Log)
        
        def val(id):
            try: return self.query_one(f"#{id}", Input).value
            except: return ""

        c = base_cmd
        if cmd == "info": 
            c += ["info", "--input", val("gen_in"), "--ref", val("gen_ref"), "--detailed"]
        elif cmd in ["calculate-coverage", "coverage-sample"]:
            c += ["info", cmd, "--input", val("gen_in")]
            if val("gen_region"): c += ["-r", val("gen_region")]
        elif cmd == "align":
            c += ["align", "--input", val("align_r1"), "--ref", val("gen_ref")]
        elif cmd in ["sort", "index", "unindex", "unsort", "to-cram", "to-bam", "unalign", "subset", "mt-extract"]:
            c += ["bam", cmd, "--input", val("bam_in")]
            if val("bam_ref"): c += ["--ref", val("bam_ref")]
            if cmd == "subset" and val("bam_extra"): c += [val("bam_extra")]
        elif cmd.startswith("repair-"):
            c += ["repair", cmd.replace("repair-", ""), "--input", val("bam_in")]
        elif cmd in ["mito", "ydna", "unmapped", "custom"]:
            c += ["extract"]
            if cmd == "custom": c += ["--input", val("ext_in"), "-r", val("ext_region")]
            else: c += [cmd, "--input", val("ext_in")]
            if val("ext_out"): c += ["--outdir", val("ext_out")]
        elif cmd in ["snp", "indel", "sv", "cnv", "freebayes", "gatk", "deepvariant", "annotate", "filter", "trio", "vcf-qc"]:
            sub = "qc" if cmd == "vcf-qc" else cmd
            c += ["vcf", sub]
            if sub == "trio": c += ["--proband", val("vcf_in"), "--mother", val("vcf_e1"), "--father", val("vcf_e2")]
            else: c += ["--input", val("vcf_in")]
            if val("vcf_ref"): c += ["--ref", val("vcf_ref")]
            if sub == "annotate" and val("vcf_e1"): c += ["--ann-vcf", val("vcf_e1")]
            if sub == "filter":
                if val("vcf_e2"): c += ["--expr", val("vcf_e2")]
                if val("vcf_e3"): c += ["--gene", val("vcf_e3")]
            if sub in ["snp", "indel", "freebayes", "gatk", "deepvariant"] and val("vcf_e3"): c += ["-r", val("vcf_e3")]
        elif cmd.startswith("vep-"):
            sub = cmd.replace("vep-", "")
            c += ["vep"]
            if sub == "run":
                c += ["--input", val("vcf_in"), "--ref", val("vcf_ref")]
                if val("vep_cache"): c += ["--vep-cache", val("vep_cache")]
                if val("vep_args"): c += ["--vep-args", val("vep_args")]
            else:
                c += [sub]
                if val("vep_cache"): c += ["--vep-cache", val("vep_cache")]
        elif cmd == "microarray":
            c += ["microarray", "--input", val("anc_in")]
        elif cmd == "lineage-y":
            c += ["lineage", "y-dna", "--input", val("anc_in"), "--yleaf-path", val("yleaf_path"), "--pos-file", val("yleaf_pos")]
        elif cmd == "lineage-mt":
            c += ["lineage", "mt-dna", "--input", val("anc_in"), "--haplogrep-path", val("haplogrep_path")]
        elif cmd in ["fastqc", "fastp"]:
            c += ["qc", cmd, "--input", val("qc_in")]
        elif cmd.startswith("ref-"):
            sub = cmd.replace("ref-", "")
            c += ["ref", sub]
            if sub == "identify":
                c += ["--input", val("lib_in")]
            if sub not in ["download", "download-genes"]: c += ["--ref", val("lib_ref")]
        elif cmd in ["coverage-wgs", "coverage-wes"]:
            c += ["info", "calculate-coverage", "--input", val("qc_in")]

        self.execute_cmd(c)

    def execute_cmd(self, cmd):
        log = self.query_one("#output", Log)
        log.write_line(f"Running: {' '.join(cmd)}")
        def run_thread():
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in p.stdout: self.call_from_thread(log.write_line, line.strip())
            p.wait()
            self.call_from_thread(log.write_line, f"Finished (Exit {p.returncode})")
        threading.Thread(target=run_thread, daemon=True).start()

    def action_toggle_dark(self) -> None: self.dark = not self.dark

def main(): WGSExtractTUI().run()
if __name__ == "__main__": main()
