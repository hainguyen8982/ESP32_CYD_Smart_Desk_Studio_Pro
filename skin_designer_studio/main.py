import sys
import os
import json
import math
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

# Set CustomTkinter Theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CANVAS_WIDTH = 320
CANVAS_HEIGHT = 240
SCALE = 2.5  # 2.5x Display scale for crisp PC editing (800x600 canvas)

PRESET_DIR = os.path.join(os.path.dirname(__file__), "preset_skins")

PAGE_NAMES = [
    "Page 0: Clock & Weather",
    "Page 1: Lunar Calendar",
    "Page 2: Financial Market",
    "Page 3: PC Monitor (CPU & RAM)",
    "Page 4: PC Monitor (Net & Storage)",
    "Page 5: Desk Utilities (Pomodoro)",
    "Page 6: Media Remote Control",
    "Page 7: System Settings"
]

# 5x7 Dot Matrix Character Bitmaps
DOT_MATRIX_5X7 = {
    '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    '3': [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    ':': [0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000],
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'M': [0b10001, 0b11011, 0b10101, 0b10001, 0b10001, 0b10001, 0b10001],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000]
}

# 7-Segment Digit Segment Bitmasks (a, b, c, d, e, f, g)
SEGMENT7_MASKS = {
    '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
    '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F,
    '-': 0x40, ' ': 0x00
}

WIDGET_TYPES = [
    ("Digital Clock & Lunar", "clock", 180, 65),
    ("Weather City & Forecast", "weather", 110, 65),
    ("Dot Matrix Morning Clock", "clock_dot_matrix", 290, 85),
    ("Dot Matrix Evening Clock", "clock_dot_matrix_evening", 290, 85),
    ("Dot Matrix Red Line Divider", "dot_matrix_divider", 290, 10),
    ("CPU Arc Gauge", "gauge_cpu", 145, 80),
    ("RAM Load Meter", "gauge_ram", 145, 80),
    ("SJC Gold & XAUUSD", "gold_sjc", 300, 80),
    ("Hardware Line Chart", "line_chart", 300, 55)
]

class SkinDesignerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎨 Smart Desk Studio - Dashboard Multi-Page Skin Designer")
        self.geometry("1260x840")
        self.resizable(True, True)

        self.current_page_idx = 0

        self.skin_data = {
            "skin_name": "Custom Multi-Page Skin",
            "author": "User Designer",
            "version": "1.0",
            "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "bg_color": "#000000"},
            "pages": {}
        }

        # Initialize 8 empty pages 0..7
        for i in range(8):
            self.skin_data["pages"][str(i)] = {"name": PAGE_NAMES[i], "widgets": []}

        self.selected_widget_id = None
        self.drag_data = {"x": 0, "y": 0, "widget": None, "handle": None}

        self.create_layout()
        self.bind_keyboard_shortcuts()
        self.load_preset("Retro Dot Matrix LED Clock")

    def bind_keyboard_shortcuts(self):
        # Delete / Backspace shortcuts to delete selected widget
        self.bind("<Delete>", lambda e: self.delete_selected_widget())
        self.bind("<BackSpace>", lambda e: self.delete_selected_widget())

        # Arrow key shortcuts for 1px fine-grained movement
        self.bind("<Up>", lambda e: self.nudge_selected_widget(0, -1))
        self.bind("<Down>", lambda e: self.nudge_selected_widget(0, 1))
        self.bind("<Left>", lambda e: self.nudge_selected_widget(-1, 0))
        self.bind("<Right>", lambda e: self.nudge_selected_widget(1, 0))

        # Shift + Arrow key shortcuts for 5px fast movement
        self.bind("<Shift-Up>", lambda e: self.nudge_selected_widget(0, -5))
        self.bind("<Shift-Down>", lambda e: self.nudge_selected_widget(0, 5))
        self.bind("<Shift-Left>", lambda e: self.nudge_selected_widget(-5, 0))
        self.bind("<Shift-Right>", lambda e: self.nudge_selected_widget(5, 0))

    def create_layout(self):
        # ── Main Container ─────────────────────────────────────────────
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Header Bar ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(main_frame, fg_color="#161b22", corner_radius=8, height=50)
        hdr.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            hdr, text="🎨 Smart Desk Studio — Multi-Page Layout & Font Designer (Pages 0..7)",
            font=ctk.CTkFont(size=16, weight="bold"), text_color="#58a6ff"
        )
        title_lbl.pack(side="left", padx=15, pady=8)

        export_btn = ctk.CTkButton(
            hdr, text="💾 Export Skin JSON", width=140, fg_color="#238636", hover_color="#2ea043",
            command=self.export_json
        )
        export_btn.pack(side="right", padx=10, pady=8)

        import_btn = ctk.CTkButton(
            hdr, text="📂 Load Skin JSON", width=140, fg_color="#21262d", hover_color="#30363d",
            command=self.import_json
        )
        import_btn.pack(side="right", padx=5, pady=8)

        # ── Shortcuts Banner Bar ──────────────────────────────────────
        banner = ctk.CTkFrame(main_frame, fg_color="#0d1117", border_width=1, border_color="#30363d", corner_radius=6)
        banner.pack(fill="x", pady=(0, 10))

        b_text = "💡 Phím Tắt: 🖱️ Click chọn | 🖱️ Kéo di chuyển | 🔲 Resize núm góc | ⬅️⬆️➡️⬇️ Mũi Tên: Vi chỉnh 1px (Shift: 5px) | ⌨️ Delete: Xóa Widget"
        b_lbl = ctk.CTkLabel(banner, text=b_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        b_lbl.pack(padx=10, pady=6)

        # ── Body Grid (3 Columns: Left Toolbox, Center Canvas, Right Properties)
        body = ctk.CTkFrame(main_frame, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # 1. Left Toolbox (Presets & Widget Library)
        left_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=230)
        left_box.pack(side="left", fill="y", padx=(0, 10))

        t_lbl = ctk.CTkLabel(left_box, text="📦 Preset Skins", font=ctk.CTkFont(size=14, weight="bold"))
        t_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.preset_combo = ctk.CTkOptionMenu(
            left_box,
            values=["Retro Dot Matrix LED Clock", "Cyberpunk Neon HUD", "Nordic Minimalist Studio", "Luxury Gold & Finance"],
            command=self.load_preset
        )
        self.preset_combo.set("Retro Dot Matrix LED Clock")
        self.preset_combo.pack(fill="x", padx=10, pady=5)

        ctk.CTkFrame(left_box, fg_color="#30363d", height=1).pack(fill="x", padx=10, pady=10)

        w_lbl = ctk.CTkLabel(left_box, text="➕ Add Widgets to Current Page", font=ctk.CTkFont(size=12, weight="bold"))
        w_lbl.pack(anchor="w", padx=12, pady=(5, 5))

        for name, wtype, def_w, def_h in WIDGET_TYPES:
            btn = ctk.CTkButton(
                left_box, text=f"+ {name}", anchor="w",
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda t=wtype, n=name, w=def_w, h=def_h: self.add_widget(n, t, w, h)
            )
            btn.pack(fill="x", padx=10, pady=3)

        # 2. Center Interactive Canvas (With Page Switcher Tabs at top)
        center_box = ctk.CTkFrame(body, fg_color="#090d16", corner_radius=10)
        center_box.pack(side="left", fill="both", expand=True)

        # Dashboard Page Switcher Bar
        page_hdr = ctk.CTkFrame(center_box, fg_color="#161b22", height=40)
        page_hdr.pack(fill="x", padx=10, pady=(10, 5))

        p_title = ctk.CTkLabel(page_hdr, text="🖥️ Select Dashboard Page:", font=ctk.CTkFont(size=12, weight="bold"))
        p_title.pack(side="left", padx=10, pady=5)

        self.page_combo = ctk.CTkOptionMenu(
            page_hdr,
            values=PAGE_NAMES,
            command=self.on_page_select, width=240
        )
        self.page_combo.set(PAGE_NAMES[0])
        self.page_combo.pack(side="left", padx=10, pady=5)

        # Tkinter Canvas (2.5x Scale)
        self.canvas = tk.Canvas(
            center_box, width=int(CANVAS_WIDTH * SCALE), height=int(CANVAS_HEIGHT * SCALE),
            bg="#000000", highlightthickness=2, highlightbackground="#30363d"
        )
        self.canvas.pack(padx=15, pady=10)

        # Canvas Mouse Binds for Drag & Drop and Resizing
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # 3. Right Properties Panel
        right_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=250)
        right_box.pack(side="right", fill="y", padx=(10, 0))

        p_lbl = ctk.CTkLabel(right_box, text="⚙️ Widget Inspector", font=ctk.CTkFont(size=14, weight="bold"))
        p_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.sel_name_lbl = ctk.CTkLabel(right_box, text="Select a widget to edit", text_color="#8b949e")
        self.sel_name_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        # Geometry controls (X, Y, W, H)
        geom_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        geom_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(geom_frame, text="X:").grid(row=0, column=0, padx=2, pady=2)
        self.entry_x = ctk.CTkEntry(geom_frame, width=60)
        self.entry_x.grid(row=0, column=1, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="Y:").grid(row=0, column=2, padx=2, pady=2)
        self.entry_y = ctk.CTkEntry(geom_frame, width=60)
        self.entry_y.grid(row=0, column=3, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="W:").grid(row=1, column=0, padx=2, pady=2)
        self.entry_w = ctk.CTkEntry(geom_frame, width=60)
        self.entry_w.grid(row=1, column=1, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="H:").grid(row=1, column=2, padx=2, pady=2)
        self.entry_h = ctk.CTkEntry(geom_frame, width=60)
        self.entry_h.grid(row=1, column=3, padx=2, pady=2)

        apply_geom_btn = ctk.CTkButton(right_box, text="Apply Geometry", width=210, command=self.apply_manual_geometry)
        apply_geom_btn.pack(padx=10, pady=6)

        # Font Style Dropdown Selector
        f_lbl = ctk.CTkLabel(right_box, text="🔤 Font & Display Style", font=ctk.CTkFont(size=12, weight="bold"))
        f_lbl.pack(anchor="w", padx=12, pady=(8, 2))

        self.font_combo = ctk.CTkOptionMenu(
            right_box,
            values=["Dot Matrix LED", "7-Segment Digital", "Monospace Code", "Default Sans"],
            command=self.on_font_change, width=210
        )
        self.font_combo.set("Dot Matrix LED")
        self.font_combo.pack(padx=10, pady=4)

        # Color Pickers
        col_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        col_frame.pack(fill="x", padx=10, pady=5)

        self.bg_col_btn = ctk.CTkButton(col_frame, text="Card BG Color", width=210, fg_color="#21262d", command=self.pick_bg_color)
        self.bg_col_btn.pack(pady=4)

        self.accent_col_btn = ctk.CTkButton(col_frame, text="LED Dot / Accent Color", width=210, fg_color="#21262d", command=self.pick_accent_color)
        self.accent_col_btn.pack(pady=4)

        # Delete Widget
        self.del_btn = ctk.CTkButton(
            right_box, text="🗑️ Delete Widget (Del)", width=210, fg_color="#da3633", hover_color="#f85149",
            command=self.delete_selected_widget
        )
        self.del_btn.pack(side="bottom", padx=10, pady=15)

    def on_page_select(self, val):
        for i, name in enumerate(PAGE_NAMES):
            if name == val:
                self.current_page_idx = i
                break
        self.selected_widget_id = None
        self.redraw_canvas()

    def load_preset(self, preset_name):
        filename_map = {
            "Retro Dot Matrix LED Clock": "dot_matrix_led.json",
            "Cyberpunk Neon HUD": "cyberpunk_neon.json",
            "Nordic Minimalist Studio": "nordic_minimalist.json",
            "Luxury Gold & Finance": "luxury_gold.json"
        }
        fname = filename_map.get(preset_name, "dot_matrix_led.json")
        path = os.path.join(PRESET_DIR, fname)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Ensure data has pages 0..7
                if "pages" in data:
                    self.skin_data = data
                else:
                    # Legacy 1-page json conversion
                    widgets = data.get("widgets", [])
                    self.skin_data = {
                        "skin_name": data.get("skin_name", "Preset"),
                        "canvas": data.get("canvas", {"width": 320, "height": 240, "bg_color": "#000000"}),
                        "pages": {}
                    }
                    for i in range(8):
                        self.skin_data["pages"][str(i)] = {"name": PAGE_NAMES[i], "widgets": list(widgets) if i == 0 else []}

                self.selected_widget_id = None
                self.redraw_canvas()
            except Exception as e:
                print(f"Error loading preset: {e}")

    def get_current_widgets(self):
        pg_str = str(self.current_page_idx)
        if pg_str not in self.skin_data.get("pages", {}):
            self.skin_data.setdefault("pages", {})[pg_str] = {"name": PAGE_NAMES[self.current_page_idx], "widgets": []}
        return self.skin_data["pages"][pg_str]["widgets"]

    def draw_dot_matrix_text(self, text, start_x, start_y, dot_size, pitch, on_color, off_color="#121212", wid_tag=""):
        cur_x = start_x
        for ch in text.upper():
            bm = DOT_MATRIX_5X7.get(ch, DOT_MATRIX_5X7.get(' '))
            for row in range(7):
                row_bits = bm[row]
                for col in range(5):
                    is_on = (row_bits >> (4 - col)) & 1
                    dx = cur_x + col * pitch
                    dy = start_y + row * pitch
                    col_fill = on_color if is_on else off_color
                    self.canvas.create_oval(
                        dx, dy, dx + dot_size, dy + dot_size,
                        fill=col_fill, outline="", tags=("widget", wid_tag)
                    )
            cur_x += 6 * pitch

    def draw_7segment_text(self, text, start_x, start_y, seg_w, seg_h, color, wid_tag=""):
        """Draw 7-segment digital display numbers"""
        cur_x = start_x
        for ch in text:
            if ch == ':':
                # Draw Colon Dots
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.3), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.3) + 4, fill=color, outline="", tags=("widget", wid_tag))
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.7), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.7) + 4, fill=color, outline="", tags=("widget", wid_tag))
                cur_x += int(seg_w * 0.5)
                continue

            mask = SEGMENT7_MASKS.get(ch, 0x00)
            off_col = "#151820"
            t = 4  # thickness

            # Segments: a (top), b (top-right), c (bot-right), d (bot), e (bot-left), f (top-left), g (center)
            # a: top horizontal
            self.canvas.create_rectangle(cur_x + t, start_y, cur_x + seg_w - t, start_y + t, fill=color if (mask & 0x01) else off_col, outline="", tags=("widget", wid_tag))
            # b: top right
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + t, cur_x + seg_w, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x02) else off_col, outline="", tags=("widget", wid_tag))
            # c: bot right
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), cur_x + seg_w, start_y + seg_h - t, fill=color if (mask & 0x04) else off_col, outline="", tags=("widget", wid_tag))
            # d: bot horizontal
            self.canvas.create_rectangle(cur_x + t, start_y + seg_h - t, cur_x + seg_w - t, start_y + seg_h, fill=color if (mask & 0x08) else off_col, outline="", tags=("widget", wid_tag))
            # e: bot left
            self.canvas.create_rectangle(cur_x, start_y + int(seg_h/2) + int(t/2), cur_x + t, start_y + seg_h - t, fill=color if (mask & 0x10) else off_col, outline="", tags=("widget", wid_tag))
            # f: top left
            self.canvas.create_rectangle(cur_x, start_y + t, cur_x + t, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x20) else off_col, outline="", tags=("widget", wid_tag))
            # g: center horizontal
            self.canvas.create_rectangle(cur_x + t, start_y + int(seg_h/2) - int(t/2), cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), fill=color if (mask & 0x40) else off_col, outline="", tags=("widget", wid_tag))

            cur_x += seg_w + 6

    def draw_pixel_sun(self, start_x, start_y, dot_size, pitch, color, wid_tag=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b1111111, 0b1111111, 0b0111110, 0b0011100]
        for r in range(7):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch
                    dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("widget", wid_tag))

    def draw_pixel_sunrise(self, start_x, start_y, dot_size, pitch, color, wid_tag=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b0000000, 0b1111111]
        for r in range(5):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch
                    dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("widget", wid_tag))

    def redraw_canvas(self):
        self.canvas.delete("all")
        bg_col = self.skin_data.get("canvas", {}).get("bg_color", "#000000")
        self.canvas.configure(bg=bg_col)

        # Draw subtle grid lines
        for x in range(0, int(CANVAS_WIDTH * SCALE), int(20 * SCALE)):
            self.canvas.create_line(x, 0, x, int(CANVAS_HEIGHT * SCALE), fill="#141418", dash=(2, 4))
        for y in range(0, int(CANVAS_HEIGHT * SCALE), int(20 * SCALE)):
            self.canvas.create_line(0, y, int(CANVAS_WIDTH * SCALE), y, fill="#141418", dash=(2, 4))

        # Render Active Page Widgets
        widgets = self.get_current_widgets()

        if not widgets:
            self.canvas.create_text(
                int(CANVAS_WIDTH * SCALE / 2), int(CANVAS_HEIGHT * SCALE / 2),
                text=f"[{PAGE_NAMES[self.current_page_idx]}]\nTrang chưa có Widget. Nhấp +Add Widget bên trái để thêm.",
                fill="#484f58", font=("Segoe UI", 13), justify="center"
            )

        for w in widgets:
            wx = int(w["x"] * SCALE)
            wy = int(w["y"] * SCALE)
            ww = int(w["w"] * SCALE)
            wh = int(w["h"] * SCALE)
            wid = w["id"]

            is_selected = (wid == self.selected_widget_id)
            outline_col = "#58a6ff" if is_selected else "#222222"
            outline_w = 3 if is_selected else 1

            # Card BG & Accent
            card_bg = w.get("bg_color", "#0C0C0C")
            accent = w.get("accent_color", "#FFFFFF")
            font_style = w.get("font_style", "dot_matrix")

            # Draw Card Rectangle
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=card_bg, outline=outline_col, width=outline_w, tags=("widget", wid))

            # Widget Visual Simulation Mockup
            wtype = w.get("type", "")

            if font_style == "segment7":
                # 7-Segment Digital Font
                if wtype in ["clock", "clock_dot_matrix", "clock_dot_matrix_evening"]:
                    self.draw_7segment_text("14:35:08", wx + 15, wy + 15, seg_w=18, seg_h=36, color=accent, wid_tag=wid)
                elif "gauge" in wtype:
                    self.draw_7segment_text("42-68", wx + 15, wy + 15, seg_w=16, seg_h=32, color=accent, wid_tag=wid)
                else:
                    self.draw_7segment_text("12:00", wx + 15, wy + 15, seg_w=18, seg_h=36, color=accent, wid_tag=wid)
            elif font_style == "mono":
                # Monospace Code Font
                self.canvas.create_text(wx + 10, wy + 18, text=f"> {w.get('name','')}", fill=accent, font=("Consolas", int(7 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                self.canvas.create_text(wx + 10, wy + 42, text="sys.status: [OK]", fill="#39FF14", font=("Consolas", int(5.5 * SCALE)), anchor="w", tags=("widget", wid))
            elif font_style == "dot_matrix" or wtype in ["clock_dot_matrix", "clock_dot_matrix_evening"]:
                # Dot Matrix LED Font
                if wtype == "clock_dot_matrix":
                    self.draw_pixel_sun(wx + 20, wy + 18, dot_size=5, pitch=7, color="#FFCC00", wid_tag=wid)
                    self.draw_dot_matrix_text("4:40 AM", wx + 90, wy + 18, dot_size=5, pitch=7, on_color=accent, off_color="#181818", wid_tag=wid)
                elif wtype == "clock_dot_matrix_evening":
                    self.draw_pixel_sunrise(wx + 20, wy + 18, dot_size=5, pitch=7, color="#FF9900", wid_tag=wid)
                    self.draw_dot_matrix_text("7:32 PM", wx + 90, wy + 18, dot_size=5, pitch=7, on_color=accent, off_color="#181818", wid_tag=wid)
                elif wtype == "dot_matrix_divider":
                    line_y = wy + int(wh / 2) - 2
                    for dx in range(wx + 10, wx + ww - 10, 8):
                        self.canvas.create_oval(dx, line_y, dx + 5, line_y + 5, fill=accent, outline="", tags=("widget", wid))
                else:
                    self.draw_dot_matrix_text("14:35:08", wx + 15, wy + 15, dot_size=4, pitch=6, on_color=accent, off_color="#181818", wid_tag=wid)
            else:
                # Standard Vector / Default Sans Rendering
                if wtype == "clock":
                    self.canvas.create_text(wx + 15, wy + 20, text="14:35:08", fill=accent, font=("Consolas", int(14 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_text(wx + 15, wy + 42, text="Thứ Hai, 10/08 • 18/07 Âm", fill="#8b949e", font=("Segoe UI", int(5 * SCALE)), anchor="w", tags=("widget", wid))
                elif wtype == "weather":
                    self.canvas.create_text(wx + 10, wy + 18, text="🌤️ 28°C", fill=accent, font=("Segoe UI", int(9 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_text(wx + 10, wy + 42, text="Hà Nội | Hum:80%", fill="#8b949e", font=("Segoe UI", int(4.5 * SCALE)), anchor="w", tags=("widget", wid))
                elif wtype == "gauge_cpu":
                    self.canvas.create_text(wx + 10, wy + 15, text="CPU LOAD", fill="#8b949e", font=("Segoe UI", int(4.5 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_text(wx + 10, wy + 45, text="42%", fill=accent, font=("Consolas", int(12 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_arc(wx + ww - 50, wy + 15, wx + ww - 10, wy + 55, start=0, extent=240, outline=accent, width=4, style="arc", tags=("widget", wid))
                elif wtype == "gauge_ram":
                    self.canvas.create_text(wx + 10, wy + 15, text="RAM LOAD", fill="#8b949e", font=("Segoe UI", int(4.5 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_text(wx + 10, wy + 45, text="68%", fill=accent, font=("Consolas", int(12 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_rectangle(wx + 70, wy + 40, wx + ww - 15, wy + 50, fill="#21262d", outline="", tags=("widget", wid))
                    self.canvas.create_rectangle(wx + 70, wy + 40, wx + 70 + int((ww - 85) * 0.68), wy + 50, fill=accent, outline="", tags=("widget", wid))
                elif wtype == "gold_sjc":
                    self.canvas.create_text(wx + 15, wy + 20, text="SJC GOLD: 137.5M / 141.5M (+0.5M)", fill=accent, font=("Segoe UI", int(6.5 * SCALE), "bold"), anchor="w", tags=("widget", wid))
                    self.canvas.create_text(wx + 15, wy + 45, text="XAUUSD Spot: $4,064.00/oz", fill="#8b949e", font=("Segoe UI", int(5.5 * SCALE)), anchor="w", tags=("widget", wid))
                elif wtype == "line_chart":
                    self.canvas.create_text(wx + 10, wy + 12, text="REALTIME HARDWARE TREND", fill="#8b949e", font=("Segoe UI", int(4 * SCALE)), anchor="w", tags=("widget", wid))
                    pts = [(wx + 10, wy + wh - 10), (wx + 40, wy + wh - 25), (wx + 80, wy + wh - 15), (wx + 130, wy + wh - 35), (wx + 180, wy + wh - 20), (wx + ww - 10, wy + wh - 30)]
                    for i in range(len(pts) - 1):
                        self.canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], fill=accent, width=2, tags=("widget", wid))

            # Resize Handle (bottom-right corner)
            if is_selected:
                self.canvas.create_rectangle(
                    wx + ww - 10, wy + wh - 10, wx + ww, wy + wh,
                    fill="#58a6ff", outline="#ffffff", tags=("handle", wid)
                )

        self.update_inspector()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        widgets = self.get_current_widgets()

        # Check if clicked on a resize handle first
        for w in widgets:
            wx = int(w["x"] * SCALE)
            wy = int(w["y"] * SCALE)
            ww = int(w["w"] * SCALE)
            wh = int(w["h"] * SCALE)

            if (wx + ww - 12 <= x <= wx + ww + 2) and (wy + wh - 12 <= y <= wy + wh + 2):
                self.selected_widget_id = w["id"]
                self.drag_data["handle"] = "resize"
                self.drag_data["widget"] = w
                self.drag_data["x"] = x
                self.drag_data["y"] = y
                self.redraw_canvas()
                return

        # Check if clicked inside a widget rectangle
        for w in reversed(widgets):
            wx = int(w["x"] * SCALE)
            wy = int(w["y"] * SCALE)
            ww = int(w["w"] * SCALE)
            wh = int(w["h"] * SCALE)

            if wx <= x <= wx + ww and wy <= y <= wy + wh:
                self.selected_widget_id = w["id"]
                self.drag_data["handle"] = "move"
                self.drag_data["widget"] = w
                self.drag_data["x"] = x - wx
                self.drag_data["y"] = y - wy
                self.redraw_canvas()
                return

        # Clicked empty canvas space
        self.selected_widget_id = None
        self.redraw_canvas()

    def on_canvas_drag(self, event):
        w = self.drag_data.get("widget")
        if not w:
            return

        if self.drag_data.get("handle") == "move":
            new_x = int((event.x - self.drag_data["x"]) / SCALE)
            new_y = int((event.y - self.drag_data["y"]) / SCALE)
            w["x"] = max(0, min(CANVAS_WIDTH - w["w"], new_x))
            w["y"] = max(0, min(CANVAS_HEIGHT - w["h"], new_y))
            self.redraw_canvas()
        elif self.drag_data.get("handle") == "resize":
            new_w = int((event.x - int(w["x"] * SCALE)) / SCALE)
            new_h = int((event.y - int(w["y"] * SCALE)) / SCALE)
            w["w"] = max(40, min(CANVAS_WIDTH - w["x"], new_w))
            w["h"] = max(30, min(CANVAS_HEIGHT - w["y"], new_h))
            self.redraw_canvas()

    def on_canvas_release(self, event):
        self.drag_data["widget"] = None
        self.drag_data["handle"] = None

    def nudge_selected_widget(self, dx, dy):
        w = self.get_selected_widget()
        if w:
            w["x"] = max(0, min(CANVAS_WIDTH - w["w"], w["x"] + dx))
            w["y"] = max(0, min(CANVAS_HEIGHT - w["h"], w["y"] + dy))
            self.redraw_canvas()

    def update_inspector(self):
        w = self.get_selected_widget()
        if w:
            self.sel_name_lbl.configure(text=f"Selected: {w['name']}", text_color="#58a6ff")
            self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(w["x"]))
            self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(w["y"]))
            self.entry_w.delete(0, tk.END); self.entry_w.insert(0, str(w["w"]))
            self.entry_h.delete(0, tk.END); self.entry_h.insert(0, str(w["h"]))

            font_val_map = {
                "dot_matrix": "Dot Matrix LED",
                "segment7": "7-Segment Digital",
                "mono": "Monospace Code",
                "default": "Default Sans"
            }
            cur_font = w.get("font_style", "dot_matrix" if "dot_matrix" in w.get("type","") else "default")
            self.font_combo.set(font_val_map.get(cur_font, "Dot Matrix LED"))

            self.bg_col_btn.configure(fg_color=w.get("bg_color", "#161b22"))
            self.accent_col_btn.configure(fg_color=w.get("accent_color", "#00D4FF"))
        else:
            self.sel_name_lbl.configure(text="No widget selected", text_color="#8b949e")
            self.entry_x.delete(0, tk.END)
            self.entry_y.delete(0, tk.END)
            self.entry_w.delete(0, tk.END)
            self.entry_h.delete(0, tk.END)

    def on_font_change(self, val):
        w = self.get_selected_widget()
        if w:
            font_key_map = {
                "Dot Matrix LED": "dot_matrix",
                "7-Segment Digital": "segment7",
                "Monospace Code": "mono",
                "Default Sans": "default"
            }
            w["font_style"] = font_key_map.get(val, "default")
            self.redraw_canvas()

    def apply_manual_geometry(self):
        w = self.get_selected_widget()
        if w:
            try:
                w["x"] = int(self.entry_x.get())
                w["y"] = int(self.entry_y.get())
                w["w"] = int(self.entry_w.get())
                w["h"] = int(self.entry_h.get())
                self.redraw_canvas()
            except Exception:
                pass

    def pick_bg_color(self):
        w = self.get_selected_widget()
        if w:
            color = colorchooser.askcolor(title="Choose Card Background Color", color=w.get("bg_color", "#161b22"))[1]
            if color:
                w["bg_color"] = color
                self.redraw_canvas()

    def pick_accent_color(self):
        w = self.get_selected_widget()
        if w:
            color = colorchooser.askcolor(title="Choose Accent / LED Dot Color", color=w.get("accent_color", "#00D4FF"))[1]
            if color:
                w["accent_color"] = color
                self.redraw_canvas()

    def add_widget(self, name, wtype, def_w, def_h):
        widgets = self.get_current_widgets()
        new_id = f"w_{len(widgets) + 1}_{wtype}"
        is_matrix = ("dot_matrix" in wtype)
        new_w = {
            "id": new_id,
            "name": name,
            "type": wtype,
            "font_style": "dot_matrix" if is_matrix else "default",
            "x": 20,
            "y": 20,
            "w": def_w,
            "h": def_h,
            "bg_color": "#0C0C0C" if is_matrix else "#161b22",
            "accent_color": "#FF3333" if wtype == "dot_matrix_divider" else ("#FFFFFF" if is_matrix else "#00D4FF"),
            "text_color": "#FFFFFF"
        }
        widgets.append(new_w)
        self.selected_widget_id = new_id
        self.redraw_canvas()

    def delete_selected_widget(self):
        if self.selected_widget_id:
            widgets = self.get_current_widgets()
            self.skin_data["pages"][str(self.current_page_idx)]["widgets"] = [w for w in widgets if w["id"] != self.selected_widget_id]
            self.selected_widget_id = None
            self.redraw_canvas()

    def get_selected_widget(self):
        for w in self.get_current_widgets():
            if w["id"] == self.selected_widget_id:
                return w
        return None

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Skin Layout", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.skin_data, f, indent=2, ensure_ascii=False)
                tk.messagebox.showinfo("Export Success", f"Multi-Page Skin Layout JSON successfully saved to:\n{path}")
            except Exception as e:
                tk.messagebox.showerror("Export Error", f"Failed to save JSON file: {e}")

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Skin Layout", "*.json")])
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "pages" in data:
                    self.skin_data = data
                else:
                    widgets = data.get("widgets", [])
                    self.skin_data = {
                        "skin_name": data.get("skin_name", "Preset"),
                        "canvas": data.get("canvas", {"width": 320, "height": 240, "bg_color": "#000000"}),
                        "pages": {}
                    }
                    for i in range(8):
                        self.skin_data["pages"][str(i)] = {"name": PAGE_NAMES[i], "widgets": list(widgets) if i == 0 else []}

                self.selected_widget_id = None
                self.redraw_canvas()
                tk.messagebox.showinfo("Import Success", "Skin Layout JSON successfully loaded!")
            except Exception as e:
                tk.messagebox.showerror("Import Error", f"Failed to load JSON file: {e}")

if __name__ == "__main__":
    app = SkinDesignerApp()
    app.mainloop()
