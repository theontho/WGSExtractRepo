"""Workflow graph visualization for the WGS Extract GUI."""

import tkinter as tk

import customtkinter as ctk

from wgsextract_cli.core.messages import FLOW_EDGES, FLOW_NODES

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
                FLOW_NODES["sequencer"]["label"],
                FLOW_NODES["sequencer"]["tip"],
                200,
                50,
                None,
                False,
            ),
            (
                "fastq",
                FLOW_NODES["fastq"]["label"],
                FLOW_NODES["fastq"]["tip"],
                200,
                200,
                "fastq",
                True,
            ),
            (
                "library",
                FLOW_NODES["library"]["label"],
                FLOW_NODES["library"]["tip"],
                450,
                50,
                "lib",
                True,
            ),
            (
                "bam",
                FLOW_NODES["bam"]["label"],
                FLOW_NODES["bam"]["tip"],
                450,
                200,
                "gen",
                True,
            ),
            (
                "vcf",
                FLOW_NODES["vcf"]["label"],
                FLOW_NODES["vcf"]["tip"],
                750,
                50,
                "vcf",
                True,
            ),
            (
                "extract",
                FLOW_NODES["extract"]["label"],
                FLOW_NODES["extract"]["tip"],
                750,
                150,
                "ext",
                True,
            ),
            (
                "ancestry",
                FLOW_NODES["ancestry"]["label"],
                FLOW_NODES["ancestry"]["tip"],
                750,
                250,
                "anc",
                True,
            ),
            (
                "micro",
                FLOW_NODES["micro"]["label"],
                FLOW_NODES["micro"]["tip"],
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
                FLOW_EDGES["sequencer_fastq"]["label"],
                FLOW_EDGES["sequencer_fastq"]["tip"],
            ),
            (
                "fastq",
                "bam",
                True,
                FLOW_EDGES["fastq_bam"]["label"],
                FLOW_EDGES["fastq_bam"]["tip"],
            ),
            (
                "library",
                "bam",
                False,
                FLOW_EDGES["library_bam"]["label"],
                FLOW_EDGES["library_bam"]["tip"],
            ),
            (
                "library",
                "vcf",
                False,
                FLOW_EDGES["library_vcf"]["label"],
                FLOW_EDGES["library_vcf"]["tip"],
            ),
            (
                "bam",
                "vcf",
                False,
                FLOW_EDGES["bam_vcf"]["label"],
                FLOW_EDGES["bam_vcf"]["tip"],
            ),
            (
                "bam",
                "extract",
                False,
                FLOW_EDGES["bam_extract"]["label"],
                FLOW_EDGES["bam_extract"]["tip"],
            ),
            (
                "bam",
                "ancestry",
                False,
                FLOW_EDGES["bam_ancestry"]["label"],
                FLOW_EDGES["bam_ancestry"]["tip"],
            ),
            (
                "bam",
                "micro",
                False,
                FLOW_EDGES["bam_micro"]["label"],
                FLOW_EDGES["bam_micro"]["tip"],
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
        for key, widget_info in self.node_widgets.items():
            x_raw, y_raw, label, tt, target, is_btn = widget_info
            x, y = int(x_raw), int(y_raw)
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
