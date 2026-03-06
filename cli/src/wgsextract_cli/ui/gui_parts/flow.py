"""Workflow graph visualization for the WGS Extract GUI."""

import tkinter as tk

import customtkinter as ctk

from .common import BaseFrame, ToolTip


class FlowFrame(BaseFrame):
    """
    A frame that displays a workflow graph to help users understand
    the relationship between different file types and data stages.
    """

    def setup_ui(self) -> None:
        """Set up the UI elements for the workflow graph."""
        super().setup_ui()

        # Canvas for drawing lines
        # We use standard tk.Canvas because ctk doesn't have a specialized one.
        # Match the default CustomTkinter dark frame color (#2b2b2b) to blend in.
        self.canvas = tk.Canvas(
            self,
            bg="#2b2b2b",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Node definitions: (key, label, tooltip, x, y, target_frame, is_button)
        self.nodes = [
            (
                "sequencer",
                "Sequencer",
                "The machine that reads your DNA and produces raw reads.",
                200,
                50,
                None,
                False,
            ),
            (
                "fastq",
                "FASTQ",
                "Raw sequence data and quality scores from the sequencer.",
                200,
                200,
                "fastq",
                True,
            ),
            (
                "library",
                "Library",
                "Reference genomes (FASTA) and gene maps required for alignment and calling.",
                450,
                50,
                "lib",
                True,
            ),
            (
                "bam",
                "BAM / CRAM",
                "Aligned sequence data, mapped to a reference genome.",
                450,
                200,
                "gen",
                True,
            ),
            (
                "vcf",
                "VCF / VEP",
                "Variant calls (SNPs, InDels) and their predicted biological effects.",
                750,
                50,
                "vcf",
                True,
            ),
            (
                "extract",
                "Extract",
                "Subsets of data (e.g., MT-only, Y-only) for targeted analysis.",
                750,
                150,
                "ext",
                True,
            ),
            (
                "ancestry",
                "Ancestry",
                "Haplogroup and lineage prediction (Y-DNA and Mitochondrial).",
                750,
                250,
                "anc",
                True,
            ),
            (
                "micro",
                "Microarray",
                "Simulated consumer DNA test data (e.g., 23andMe, AncestryDNA formats).",
                750,
                350,
                "micro",
                True,
            ),
        ]

        # Edges: (from_key, to_key, bidirectional, label, label_tooltip)
        self.edges = [
            (
                "sequencer",
                "fastq",
                False,
                "Creates",
                "The sequencer generates raw FASTQ files containing nucleotide sequences and quality scores.",
            ),
            (
                "fastq",
                "bam",
                True,
                "Align / Unalign",
                "Convert raw FASTQ reads into an aligned BAM file using a reference genome, or revert a BAM back to FASTQ.",
            ),
            (
                "library",
                "bam",
                False,
                "Reference",
                "Standardized genomic sequences (FASTA) used as a coordinate system for alignment.",
            ),
            (
                "library",
                "vcf",
                False,
                "Reference",
                "Genomic annotations and reference sequences used for variant calling and effect prediction.",
            ),
            (
                "bam",
                "vcf",
                False,
                "Variant Calling",
                "Identify genetic variations (SNPs, InDels) by comparing aligned reads to the reference genome.",
            ),
            (
                "bam",
                "extract",
                False,
                "Subsetting",
                "Isolate specific chromosomes (like chrM or chrY) or regions for focused analysis.",
            ),
            (
                "bam",
                "ancestry",
                False,
                "Lineage Analysis",
                "Determine maternal (mtDNA) and paternal (Y-DNA) haplogroups to trace deep ancestry.",
            ),
            (
                "bam",
                "micro",
                False,
                "Simulation",
                "Convert high-density WGS data into the sparse format used by consumer DNA tests.",
            ),
        ]

        # Store widget metadata for drawing
        self.node_widgets: dict[
            str, tuple[float, float, str, str, str | None, bool]
        ] = {}

        # Bind resize event to redraw and center
        self.canvas.bind("<Configure>", lambda e: self.draw_graph())

        # Draw nodes and edges after a short delay to ensure initial size is known
        self.after(100, self.draw_graph)

    def draw_graph(self) -> None:
        """Draw the edges and nodes on the canvas, centered dynamically."""
        if not self.winfo_exists():
            return

        self.canvas.delete("all")
        self.node_widgets.clear()

        # 1. Calculate bounding box and centering offset
        min_x = float(min(n[3] for n in self.nodes))
        max_x = float(max(n[3] for n in self.nodes))
        min_y = float(min(n[4] for n in self.nodes))
        max_y = float(max(n[4] for n in self.nodes))

        graph_w = max_x - min_x
        graph_h = max_y - min_y

        # Get current canvas size
        self.update_idletasks()
        cw = float(self.canvas.winfo_width())
        ch = float(self.canvas.winfo_height())

        # Default to no offset if canvas isn't mapped yet
        offset_x = (cw - graph_w) / 2.0 - min_x if cw > 1.0 else 0.0
        offset_y = (ch - graph_h) / 2.0 - min_y if ch > 1.0 else 0.0

        # 2. Pre-calculate positions with centering offset
        for key, label, tt, x, y, target, is_btn in self.nodes:
            self.node_widgets[key] = (
                float(x) + offset_x,
                float(y) + offset_y,
                label,
                tt,
                target,
                is_btn,
            )

        # 3. Draw edges (lines) FIRST so they are behind buttons
        for from_key, to_key, bi, label, ltt in self.edges:
            if from_key in self.node_widgets and to_key in self.node_widgets:
                x1, y1, _, _, _, _ = self.node_widgets[from_key]
                x2, y2, _, _, _, _ = self.node_widgets[to_key]

                # Adjust endpoints to edge of buttons (120x40) so that arrows are visible
                def get_edge_point(
                    ax: float, ay: float, bx: float, by: float
                ) -> tuple[float, float]:
                    dx, dy = bx - ax, by - ay
                    if dx == 0 and dy == 0:
                        return bx, by
                    # Add a small buffer (2px) to ensure arrows aren't clipped by the widget
                    tx = abs(62 / dx) if dx != 0 else float("inf")
                    ty = abs(22 / dy) if dy != 0 else float("inf")
                    t = min(tx, ty)
                    return bx - t * dx, by - t * dy

                ex2, ey2 = get_edge_point(x1, y1, x2, y2)
                if bi:
                    ex1, ey1 = get_edge_point(x2, y2, x1, y1)
                else:
                    ex1, ey1 = x1, y1

                # Draw the line
                self.canvas.create_line(
                    ex1,
                    ey1,
                    ex2,
                    ey2,
                    fill="#55aaff",
                    width=2,
                    arrow=tk.LAST if not bi else tk.BOTH,
                    arrowshape=(12, 15, 6),  # Larger, more visible arrows
                )

                # Draw label if present
                if label:
                    lx, ly = (x1 + x2) / 2, (y1 + y2) / 2
                    # Offset label slightly if it's a vertical or horizontal line to avoid overlap
                    if abs(x1 - x2) < 1:
                        lx += 60
                    elif abs(y1 - y2) < 1:
                        ly -= 25
                    else:
                        ly -= 20

                    # Use a CTkLabel for the edge label to easily add a tooltip
                    lbl = ctk.CTkLabel(
                        self.canvas,
                        text=label,
                        font=("Arial", 11, "italic"),
                        text_color="#aaaaaa",
                        fg_color="transparent",
                    )
                    self.canvas.create_window(lx, ly, window=lbl)
                    if ltt:
                        ToolTip(lbl, ltt)

        # 4. Place the nodes ON TOP
        for key, (x, y, label, tt, target, is_btn) in self.node_widgets.items():
            if is_btn:
                widget = ctk.CTkButton(
                    self.canvas,
                    text=label,
                    width=120,
                    height=40,
                    command=lambda t=target: self.navigate_to(t) if t else None,
                )
            else:
                widget = ctk.CTkLabel(
                    self.canvas,
                    text=label,
                    width=120,
                    height=40,
                    fg_color=("#cfd8dc", "#455a64"),
                    corner_radius=0,
                )

            # Create a window on the canvas for the widget
            self.canvas.create_window(x, y, window=widget, tags=key)
            ToolTip(widget, tt)

    def navigate_to(self, frame_name: str) -> None:
        """Navigate to the specified frame in the main app."""
        self.main_app.show_frame(frame_name)
