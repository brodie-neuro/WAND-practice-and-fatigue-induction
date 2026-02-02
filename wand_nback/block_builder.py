#!/usr/bin/env python3
"""
WAND Block Builder - Visual Block Ordering Interface

Horizontal drag-and-drop with dark theme matching WAND launcher.
Blocks wrap to next row if window is too narrow.

Author: Brodie E. Mangan
Version: 1.1.3
"""

import tkinter as tk
from tkinter import ttk

# =============================================================================
# Dark Theme (matching WAND launcher splash)
# =============================================================================
COLORS = {
    "bg": "#0a0a0a",
    "bg_alt": "#1a1a1a",
    "border": "#333333",
    "text": "#ffffff",
    "text_secondary": "#888888",
    "accent": "#00d4ff",
    "accent_dark": "#0097a7",
    "block_bg": "#2a2a2a",
    "block_border": "#444444",
    "block_hover": "#3a3a3a",
    "drag_bg": "#00d4ff",
    "original_pos": "#333333",
    "drop_target": "#00d4ff",
    "start_color": "#4caf50",
    "end_color": "#f44336",
    # Type-specific colors (muted, professional palette)
    "seq_bg": "#1e3a5f",  # Dark blue - Sequential
    "spa_bg": "#2a2045",  # Muted purple - Spatial
    "dual_bg": "#402030",  # Muted maroon - Dual
    "break_bg": "#707070",  # Medium gray - Break (non-task)
    "measures_bg": "#1e5f4d",  # Dark teal - Subjective measures (matches WAND)
}

# Block dimensions by type
BLOCK_WIDTH = 70
BLOCK_WIDTH_NARROW = 50  # For breaks (fits "Break")
BLOCK_HEIGHT = 45
BLOCK_PAD_X = 6
BLOCK_PAD_Y = 6


class BlockBuilderWindow:
    """
    Horizontal drag-and-drop block builder with wrapping rows.
    """

    def __init__(self, config):
        self.config = config
        self.result = None
        self.blocks = self._generate_default_blocks()
        self.block_widgets = []

        # Drag state
        self.dragging = False
        self.drag_index = None
        self.drag_label = None

        self._create_window()

    def _generate_default_blocks(self):
        """Initialize counts and return minimal main sequence (Start/End only)."""
        # Config parsing
        seq_enabled = self.config.get("sequential_enabled", True)
        spa_enabled = self.config.get("spatial_enabled", True)
        dual_enabled = self.config.get("dual_enabled", True)

        # Store counts for pool generation
        self.seq_count = (
            self.config.get("sequential", {}).get("blocks", 5) if seq_enabled else 0
        )
        self.spa_count = (
            self.config.get("spatial", {}).get("blocks", 4) if spa_enabled else 0
        )
        self.dual_count = (
            self.config.get("dual", {}).get("blocks", 4) if dual_enabled else 0
        )

        self.num_breaks = self.config.get("num_breaks", 2)
        self.num_measures = self.config.get("num_measures", 4)

        # Minimal start/end
        return [
            {"label": "Start", "type": "start", "movable": False},
            {"label": "End", "type": "end", "movable": False},
        ]

    def _generate_seq_pool(self):
        return [
            {"label": "SEQ", "type": "seq", "movable": True}
            for i in range(getattr(self, "seq_count", 0))
        ]

    def _generate_spa_pool(self):
        return [
            {"label": "SPA", "type": "spa", "movable": True}
            for i in range(getattr(self, "spa_count", 0))
        ]

    def _generate_dual_pool(self):
        return [
            {"label": "DUAL", "type": "dual", "movable": True}
            for i in range(getattr(self, "dual_count", 0))
        ]

    def _generate_break_pool(self):
        """Generate pool of break blocks based on count."""
        return [
            {"label": f"Break", "type": "break", "movable": True}
            for i in range(getattr(self, "num_breaks", 0))
        ]

    def _generate_measure_pool(self):
        """Generate pool of measure blocks based on count."""
        return [
            {"label": "Sub_M", "type": "measures", "movable": True}
            for i in range(getattr(self, "num_measures", 0))
        ]

    def _create_window(self):
        """Create the main window."""
        self.root = tk.Tk()
        self.root.title("WAND — Block Order")
        self.root.configure(bg=COLORS["bg"])

        # Calculate preferred size
        blocks_per_row = min(len(self.blocks), 12)  # Max 12 per row
        window_width = blocks_per_row * (BLOCK_WIDTH + BLOCK_PAD_X) + 60
        window_width = max(700, min(1000, window_width))

        # Calculate rows needed - add extra height for header + legend + new pools + buttons
        num_rows = (len(self.blocks) + blocks_per_row - 1) // blocks_per_row
        block_area_height = num_rows * (BLOCK_HEIGHT + BLOCK_PAD_Y) + 30
        window_height = block_area_height + 550  # Increased for 5 pools

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - window_width) // 2
        y = (screen_h - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(500, 450)
        self.root.resizable(True, True)  # Ensure window can be resized

        # Bind window close button (X) to exit entire application
        self.root.protocol("WM_DELETE_WINDOW", self._exit_all)

        # Main container
        main = tk.Frame(self.root, bg=COLORS["bg"], padx=20, pady=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(main, bg=COLORS["bg"])
        header.pack(fill=tk.X, pady=(0, 8))

        title = tk.Label(
            header,
            text="Block Order",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["accent"],
        )
        title.pack(side=tk.LEFT)

        # Block count label - stored for dynamic updates
        self.count_label = tk.Label(
            header,
            text="   (0 task blocks, excl. breaks/measures)",
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["text_secondary"],
        )
        self.count_label.pack(side=tk.LEFT)

        subtitle = tk.Label(
            header,
            text="   Drag to reorder · Double-click to remove",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["text_secondary"],
        )
        subtitle.pack(side=tk.LEFT)

        # Legend
        legend_frame = tk.Frame(main, bg=COLORS["bg"])
        legend_frame.pack(fill=tk.X, pady=(0, 8))

        legend_items = [
            ("Sequential", COLORS["seq_bg"]),
            ("Spatial", COLORS["spa_bg"]),
            ("Dual", COLORS["dual_bg"]),
            ("Break", COLORS["break_bg"]),
            ("Subj.", COLORS["measures_bg"]),
        ]

        for label_text, color in legend_items:
            item = tk.Frame(legend_frame, bg=COLORS["bg"])
            item.pack(side=tk.LEFT, padx=(0, 12))

            # Use Frame for solid color swatch (more consistent than Label)
            swatch = tk.Frame(item, bg=color, width=16, height=12)
            swatch.pack(side=tk.LEFT, padx=(0, 3))
            swatch.pack_propagate(False)

            lbl = tk.Label(
                item,
                text=label_text,
                font=("Segoe UI", 8),
                bg=COLORS["bg"],
                fg=COLORS["text_secondary"],
            )
            lbl.pack(side=tk.LEFT)

        # Main Block area - will hold the main sequence with wrapping
        main_label = tk.Label(
            main,
            text="Main Sequence (Drag blocks to reorder):",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["text_secondary"],
        )
        main_label.pack(anchor=tk.W, pady=(0, 4))

        self.block_area = tk.Frame(
            main,
            bg=COLORS["bg_alt"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
        )
        self.block_area.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Pool section label
        pool_label = tk.Label(
            main,
            text="Click items below to add them to the sequence:",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["text_secondary"],
        )
        pool_label.pack(anchor=tk.W, pady=(4, 4))

        # Define pools config
        self.pools_config = [
            ("Sequential:", "seq_bg", "seq_pool_area", "seq_pool", "seq"),
            ("Spatial:", "spa_bg", "spa_pool_area", "spa_pool", "spa"),
            ("Dual:", "dual_bg", "dual_pool_area", "dual_pool", "dual"),
            ("Breaks:", "break_bg", "break_pool_area", "break_pool", "break"),
            (
                "Subjective:",
                "measures_bg",
                "measure_pool_area",
                "measure_pool",
                "measure",
            ),
        ]

        # self.pool_areas = {} # Not strictly needed if using setattr

        for i, (label, color_key, area_attr, pool_attr, pool_type) in enumerate(
            self.pools_config
        ):
            # Container for label + pool
            frame = tk.Frame(main, bg=COLORS["bg"])

            # Extra spacing for the last item (Measures) to separate from buttons
            pady = (0, 20) if i == len(self.pools_config) - 1 else (0, 4)
            frame.pack(fill=tk.X, pady=pady)

            tk.Label(
                frame,
                text=label,
                font=("Segoe UI", 9),
                bg=COLORS["bg"],
                fg=COLORS["text"],
                width=10,
                anchor=tk.W,
            ).pack(side=tk.LEFT)

            area = tk.Frame(
                frame,
                bg=COLORS["bg_alt"],
                highlightbackground=COLORS.get(color_key, COLORS["border"]),
                highlightthickness=1,
                height=50,
            )
            area.pack(side=tk.LEFT, fill=tk.X, expand=True)
            area.pack_propagate(False)

            setattr(self, area_attr, area)

        # Initialize pools
        self.seq_pool = self._generate_seq_pool()
        self.spa_pool = self._generate_spa_pool()
        self.dual_pool = self._generate_dual_pool()
        self.break_pool = self._generate_break_pool()
        self.measure_pool = self._generate_measure_pool()

        # Bind resize to re-layout blocks
        self.block_area.bind("<Configure>", self._on_resize)

        # Render all blocks and pools
        self.root.after(10, self._render_all)

        # Button row
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack(fill=tk.X)

        back_btn = tk.Button(
            btn_frame,
            text="Back",
            font=("Segoe UI", 9),
            bg=COLORS["block_bg"],
            fg=COLORS["text"],
            activebackground=COLORS["block_hover"],
            activeforeground=COLORS["text"],
            relief=tk.FLAT,
            padx=14,
            pady=5,
            command=self._cancel,
        )
        back_btn.pack(side=tk.LEFT)

        reset_btn = tk.Button(
            btn_frame,
            text="Reset",
            font=("Segoe UI", 9),
            bg=COLORS["block_bg"],
            fg=COLORS["text"],
            activebackground=COLORS["block_hover"],
            activeforeground=COLORS["text"],
            relief=tk.FLAT,
            padx=14,
            pady=5,
            command=self._reset,
        )
        reset_btn.pack(side=tk.LEFT, padx=(8, 0))

        confirm_btn = tk.Button(
            btn_frame,
            text="Continue",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["accent"],
            fg=COLORS["bg"],
            activebackground=COLORS["accent_dark"],
            activeforeground=COLORS["bg"],
            relief=tk.FLAT,
            padx=18,
            pady=5,
            command=self._confirm,
        )
        confirm_btn.pack(side=tk.RIGHT)

    def _on_resize(self, event):
        """Re-layout blocks when window resizes."""
        if self.dragging:
            return

        # Debounce: only render if width changed
        if getattr(self, "_last_width", -1) == event.width:
            return
        self._last_width = event.width

        self._render_all()

    def _render_all(self):
        """Render main blocks and all pool areas."""
        self._render_blocks()

        pools = [
            (self.seq_pool_area, self.seq_pool, "seq"),
            (self.spa_pool_area, self.spa_pool, "spa"),
            (self.dual_pool_area, self.dual_pool, "dual"),
            (self.break_pool_area, self.break_pool, "break"),
            (self.measure_pool_area, self.measure_pool, "measure"),
        ]

        for area, pool, ptype in pools:
            self._render_pool(area, pool, ptype)

    def _render_pool(self, area, pool_blocks, pool_type):
        """Render a pool area with its blocks."""
        # Clear existing
        for widget in area.winfo_children():
            widget.destroy()

        if not pool_blocks:
            # Show placeholder text if pool is empty
            placeholder = tk.Label(
                area,
                text="All placed" if pool_type else "(none)",
                font=("Segoe UI", 8, "italic"),
                bg=COLORS["bg_alt"],
                fg=COLORS["text_secondary"],
            )
            placeholder.place(x=10, y=15)
            return

        # Place pool blocks horizontally, vertically centered
        # Pool height is 50, block height is 45, so y = (50-45)/2 = 2.5 ≈ 3
        x = 8
        y = 3
        for idx, block in enumerate(pool_blocks):
            width = BLOCK_WIDTH_NARROW if block.get("type") == "break" else BLOCK_WIDTH
            widget = self._create_pool_block(area, idx, block, x, y, pool_type)
            x += width + BLOCK_PAD_X

    def _create_pool_block(self, parent, index, block, x, y, pool_type):
        """Create a draggable block in a pool area."""
        block_type = block.get("type", "")
        width = BLOCK_WIDTH_NARROW if block_type == "break" else BLOCK_WIDTH

        # Get color
        color_key = f"{block_type}_bg" if block_type else "block_bg"
        bg_color = COLORS.get(color_key, COLORS["block_bg"])

        frame = tk.Frame(
            parent, bg=bg_color, width=width, height=BLOCK_HEIGHT, cursor="hand2"
        )
        frame.place(x=x, y=y)
        frame.pack_propagate(False)

        label = tk.Label(
            frame,
            text=block.get("label", "?"),
            font=("Segoe UI", 8, "bold"),
            bg=bg_color,
            fg=COLORS["text"],
        )
        label.pack(expand=True)

        # Bind drag from pool to main sequence
        def start_pool_drag(event, b=block, pt=pool_type, idx=index):
            self._start_pool_drag(event, b, pt, idx)

        frame.bind("<Button-1>", start_pool_drag)
        label.bind("<Button-1>", start_pool_drag)

        return frame

    def _start_pool_drag(self, event, block, pool_type, pool_index):
        """Start dragging a block from pool to main sequence (Click to Add)."""
        # Add block to main sequence at the end (before End block)
        insert_pos = len(self.blocks) - 1  # Before "End"
        self.blocks.insert(insert_pos, block.copy())

        # Remove from pool
        if pool_type == "seq":
            self.seq_pool.pop(pool_index)
        elif pool_type == "spa":
            self.spa_pool.pop(pool_index)
        elif pool_type == "dual":
            self.dual_pool.pop(pool_index)
        elif pool_type == "break":
            self.break_pool.pop(pool_index)
        elif pool_type == "measure":
            self.measure_pool.pop(pool_index)

        # Re-render
        self._render_all()

    def _move_to_pool(self, index):
        """Move block from main sequence back to its pool (Double Click)."""
        # Cancel any pending or active drag from the first click
        self.pending_drag = False
        if self.dragging:
            self.dragging = False
            self.drag_index = None
            if getattr(self, "drag_label", None):
                self.drag_label.destroy()
                self.drag_label = None

        if index >= len(self.blocks) or not self.blocks[index].get("movable", True):
            return

        block = self.blocks.pop(index)
        btype = block.get("type")

        # Add back to correct pool
        if btype == "seq":
            self.seq_pool.append(block)
        elif btype == "spa":
            self.spa_pool.append(block)
        elif btype == "dual":
            self.dual_pool.append(block)
        elif btype == "break":
            self.break_pool.append(block)
        # Note: 'measures' is the type string, 'measure' is the pool loop key. Check matches.
        elif btype == "measures":
            self.measure_pool.append(block)

        # Re-render
        self._render_all()

    def _render_blocks(self):
        """Render blocks with wrapping."""
        # Update block count label
        task_types = {"seq", "spa", "dual"}
        task_count = sum(1 for b in self.blocks if b.get("type") in task_types)
        self.count_label.configure(
            text=f"   ({task_count} task blocks, excl. breaks/measures)"
        )

        # Clear existing
        for widget in self.block_area.winfo_children():
            widget.destroy()
        self.block_widgets = []

        # Get available width
        self.block_area.update_idletasks()
        available_width = self.block_area.winfo_width() - 20
        if available_width < 100:
            available_width = 600  # Default if not yet sized

        # Calculate blocks per row
        slot_width = BLOCK_WIDTH + BLOCK_PAD_X
        blocks_per_row = max(1, available_width // slot_width)

        # Calculate and set required height for all rows
        num_rows = (len(self.blocks) + blocks_per_row - 1) // blocks_per_row
        req_height = max(80, num_rows * (BLOCK_HEIGHT + BLOCK_PAD_Y) + 20)
        self.block_area.configure(height=req_height)

        # Place blocks
        for idx, block in enumerate(self.blocks):
            row = idx // blocks_per_row
            col = idx % blocks_per_row

            x = 10 + col * slot_width
            y = 10 + row * (BLOCK_HEIGHT + BLOCK_PAD_Y)

            widget = self._create_block(idx, block, x, y)
            self.block_widgets.append(widget)

    def _create_block(self, index, block, x, y):
        """Create a block at position with type-specific styling."""
        is_movable = block.get("movable", True)
        block_type = block.get("type", "")

        # Determine dimensions based on type
        if block_type == "break":
            width = BLOCK_WIDTH_NARROW
        else:
            width = BLOCK_WIDTH

        # Determine background color based on type
        type_colors = {
            "seq": COLORS["seq_bg"],
            "spa": COLORS["spa_bg"],
            "dual": COLORS["dual_bg"],
            "break": COLORS["break_bg"],
            "measures": COLORS["measures_bg"],
        }
        bg_color = type_colors.get(block_type, COLORS["block_bg"])

        frame = tk.Frame(
            self.block_area,
            bg=bg_color,
            width=width,
            height=BLOCK_HEIGHT,
            highlightbackground=COLORS["block_border"],
            highlightthickness=1,
        )
        # Center narrow blocks within their slot
        x_offset = (BLOCK_WIDTH - width) // 2 if width < BLOCK_WIDTH else 0
        frame.place(x=x + x_offset, y=y)
        frame.pack_propagate(False)
        frame.block_index = index
        frame.block_type = block_type
        frame.original_bg = bg_color

        # Determine text color
        if block_type == "start":
            text_color = COLORS["start_color"]
        elif block_type == "end":
            text_color = COLORS["end_color"]
        else:
            text_color = COLORS["text"]

        # Display label
        display_label = block["label"]

        label = tk.Label(
            frame,
            text=display_label,
            font=("Segoe UI", 8 if block_type == "break" else 9),
            bg=bg_color,
            fg=text_color,
        )
        label.pack(expand=True)
        label.original_bg = bg_color

        if is_movable:
            frame.configure(cursor="hand2")

            frame.bind("<Double-Button-1>", lambda e, i=index: self._move_to_pool(i))
            label.bind("<Double-Button-1>", lambda e, i=index: self._move_to_pool(i))

            frame.bind("<ButtonPress-1>", lambda e, i=index: self._start_drag(e, i))
            frame.bind("<B1-Motion>", self._on_drag)
            frame.bind("<ButtonRelease-1>", self._end_drag)
            label.bind("<ButtonPress-1>", lambda e, i=index: self._start_drag(e, i))
            label.bind("<B1-Motion>", self._on_drag)
            label.bind("<ButtonRelease-1>", self._end_drag)

            # Hover - just highlight border, keep type color
            def enter(e, f=frame):
                if not self.dragging:
                    f.configure(
                        highlightbackground=COLORS["accent"], highlightthickness=2
                    )

            def leave(e, f=frame):
                if not self.dragging:
                    f.configure(
                        highlightbackground=COLORS["block_border"], highlightthickness=1
                    )

            frame.bind("<Enter>", enter)
            frame.bind("<Leave>", leave)
            label.bind("<Enter>", enter)
            label.bind("<Leave>", leave)

        return frame

    def _start_drag(self, event, index):
        """Record potential drag start."""
        if not self.blocks[index].get("movable", True):
            return

        # Prepare for potential drag, but don't start it yet (wait for movement)
        self.pending_drag = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.drag_index = index
        self.dragging = False

    def _on_drag(self, event):
        """Update floating label position and highlight drop target."""
        # 1. Check if we should elevate pending -> active drag
        if getattr(self, "pending_drag", False):
            import math

            dx = event.x_root - self.drag_start_x
            dy = event.y_root - self.drag_start_y
            dist = math.hypot(dx, dy)

            if dist > 5:  # 5 pixel threshold
                self.pending_drag = False
                self.dragging = True

                # --- Create visual drag state (moved from _start_drag) ---
                self.drag_label = tk.Label(
                    self.root,
                    text=self.blocks[self.drag_index]["label"],
                    font=("Segoe UI", 9, "bold"),
                    bg=COLORS["drag_bg"],
                    fg=COLORS["bg"],
                    padx=10,
                    pady=8,
                )
                self.drag_label.place(
                    x=event.x_root - self.root.winfo_rootx() - 30,
                    y=event.y_root - self.root.winfo_rooty() - 15,
                )
                self.drag_label.lift()

                # Gray out original
                if self.drag_index < len(self.block_widgets):
                    self.block_widgets[self.drag_index].configure(
                        bg=COLORS["original_pos"]
                    )
                    for child in self.block_widgets[self.drag_index].winfo_children():
                        child.configure(
                            bg=COLORS["original_pos"], fg=COLORS["text_secondary"]
                        )
            else:
                return  # Ignored until threshold met

        # 2. Handle active drag
        if not self.dragging or not getattr(self, "drag_label", None):
            return

        x = event.x_root - self.root.winfo_rootx() - 30
        y = event.y_root - self.root.winfo_rooty() - 15
        self.drag_label.place(x=x, y=y)

        # Get current hover target
        target = self._get_drop_index(event.x_root, event.y_root)

        # Update highlight if target changed
        if target != getattr(self, "current_hover_target", None):
            # Reset previous target
            if (
                hasattr(self, "current_hover_target")
                and self.current_hover_target is not None
            ):
                if (
                    self.current_hover_target != self.drag_index
                    and self.current_hover_target < len(self.block_widgets)
                ):
                    self.block_widgets[self.current_hover_target].configure(
                        highlightbackground=COLORS["block_border"]
                    )

            # Highlight new target
            if target != self.drag_index and target < len(self.block_widgets):
                self.block_widgets[target].configure(
                    highlightbackground=COLORS["drop_target"], highlightthickness=2
                )

            self.current_hover_target = target

    def _get_drop_index(self, x_root, y_root):
        """Get drop index from mouse position."""
        area_x = self.block_area.winfo_rootx()
        area_y = self.block_area.winfo_rooty()

        rel_x = x_root - area_x - 10
        rel_y = y_root - area_y - 10

        # Calculate grid position
        available_width = self.block_area.winfo_width() - 20
        slot_width = BLOCK_WIDTH + BLOCK_PAD_X
        slot_height = BLOCK_HEIGHT + BLOCK_PAD_Y
        blocks_per_row = max(1, available_width // slot_width)

        col = max(0, int(rel_x / slot_width))
        row = max(0, int(rel_y / slot_height))

        col = min(col, blocks_per_row - 1)

        index = row * blocks_per_row + col
        index = max(0, min(len(self.blocks) - 1, index))

        # Don't drop on locked blocks (Start or End)
        if not self.blocks[index].get("movable", True):
            # If trying to drop on Start, move to first movable position
            if index == 0:
                index = 1
            # If trying to drop on End, move to last movable position
            elif index == len(self.blocks) - 1:
                index = len(self.blocks) - 2

        return index

    def _end_drag(self, event):
        """End drag."""
        # Clean up pending
        self.pending_drag = False

        if not self.dragging:
            return

        if getattr(self, "drag_label", None):
            self.drag_label.destroy()
            self.drag_label = None

        target = self._get_drop_index(event.x_root, event.y_root)

        if target != self.drag_index:
            block = self.blocks.pop(self.drag_index)
            self.blocks.insert(target, block)

        self.dragging = False
        self.drag_index = None

        self._render_blocks()

    def _reset(self):
        """Reset order."""
        self.blocks = self._generate_default_blocks()
        self.seq_pool = self._generate_seq_pool()
        self.spa_pool = self._generate_spa_pool()
        self.dual_pool = self._generate_dual_pool()
        self.break_pool = self._generate_break_pool()
        self.measure_pool = self._generate_measure_pool()
        self._render_all()

    def _confirm(self):
        """Confirm."""
        self.result = self.blocks.copy()
        self.root.quit()
        self.root.destroy()

    def _cancel(self):
        """Cancel and go back to previous launcher page."""
        self.result = None
        self.root.quit()
        self.root.destroy()

    def _exit_all(self):
        """Exit the entire application."""
        import sys

        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """Run and return result."""
        self.root.mainloop()
        return self.result


def show_block_builder(config):
    """Entry point."""
    builder = BlockBuilderWindow(config)
    return builder.run()


if __name__ == "__main__":
    test_config = {
        "sequential_enabled": True,
        "spatial_enabled": True,
        "dual_enabled": True,
        "counterbalance_spatial_dual": False,
        "sequential": {"blocks": 5},
        "spatial": {"blocks": 4},
        "dual": {"blocks": 4},
        "breaks_schedule": [2, 4],
        "measures_schedule": [2, 3, 4, 5],
    }

    result = show_block_builder(test_config)

    if result:
        print("\nFinal Order:")
        for i, b in enumerate(result):
            print(f"  {i+1}. {b['label']}")
    else:
        print("\nCancelled.")
