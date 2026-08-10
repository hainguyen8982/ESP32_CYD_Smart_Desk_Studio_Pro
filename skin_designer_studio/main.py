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

ELEMENT_PRESETS = [
    ("WiFi Signal Icon (Dynamic RSSI)", "wifi_signal", "📶 -54dBm", 55, 14, "#00E676", "mono"),
    ("WiFi IP Address Text", "text", "192.168.1.13", 75, 14, "#00E676", "mono"),
    ("PC Serial Status Icon", "text", "💻 USB", 45, 14, "#38BDF8", "mono"),
    ("Page Title & Icon", "text", "🌤️ Weather Clock", 110, 14, "#FFD700", "default"),
    ("Page Counter Index", "text", "0/7", 30, 14, "#8B949E", "mono"),
    ("Status Bar Current Time", "status_time", "⏰ 14:35", 55, 14, "#FFFFFF", "mono"),
    ("Digital Clock Digits", "matrix_text", "14:35:08", 170, 35, "#00F5FF", "dot_matrix"),
    ("Solar & Lunar Date", "text", "Thứ Hai 10/08 • 18/07 Âm", 170, 18, "#8B949E", "default"),
    ("Dot Matrix Sun Icon", "pixel_sun", "sun", 50, 50, "#FFCC00", "dot_matrix"),
    ("Dot Matrix Sunrise Icon", "pixel_sunrise", "sunrise", 50, 50, "#FF9900", "dot_matrix"),
    ("Dot Matrix Red Divider Line", "dot_matrix_divider", "line", 290, 10, "#FF3333", "dot_matrix"),
    ("Weather City & Temp", "text", "🌤️ 28°C Hà Nội", 110, 30, "#FFFFFF", "default"),
    ("Hardware History Line Chart", "line_chart", "chart", 300, 55, "#CC00FF", "mono")
]

class SkinDesignerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎨 Smart Desk Studio - Direct Granular Sub-Element Designer")
        self.geometry("1300x880")
        self.resizable(True, True)

        self.current_page_idx = 0

        self.skin_data = {
            "skin_name": "Custom Multi-Page Skin",
            "author": "User Designer",
            "version": "2.1",
            "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "bg_color": "#000000"},
            "pages": {}
        }

        # Initialize 8 empty pages 0..7
        for i in range(8):
            self.skin_data["pages"][str(i)] = {"name": PAGE_NAMES[i], "elements": []}

        self.selected_elem_id = None
        self.drag_data = {"x": 0, "y": 0, "elem": None, "handle": None}

        self.create_layout()
        self.bind_keyboard_shortcuts()
        self.load_preset("Retro Dot Matrix LED Clock")

    def bind_keyboard_shortcuts(self):
        self.bind("<Delete>", lambda e: self.delete_selected_element())
        self.bind("<BackSpace>", lambda e: self.delete_selected_element())

        self.bind("<Up>", lambda e: self.nudge_selected_element(0, -1))
        self.bind("<Down>", lambda e: self.nudge_selected_element(0, 1))
        self.bind("<Left>", lambda e: self.nudge_selected_element(-1, 0))
        self.bind("<Right>", lambda e: self.nudge_selected_element(1, 0))

        self.bind("<Shift-Up>", lambda e: self.nudge_selected_element(0, -5))
        self.bind("<Shift-Down>", lambda e: self.nudge_selected_element(0, 5))
        self.bind("<Shift-Left>", lambda e: self.nudge_selected_element(-5, 0))
        self.bind("<Shift-Right>", lambda e: self.nudge_selected_element(5, 0))

    def create_layout(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Header Bar ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(main_frame, fg_color="#161b22", corner_radius=8, height=50)
        hdr.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            hdr, text="🎯 Smart Desk Studio — Direct Click & Granular Sub-Element Inspector",
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

        b_text = "💡 Click trực tiếp lên từng đối tượng (WiFi Icon, IP, Time, Title, Page Index...) để chỉnh sửa hoặc xóa trên Menu Phải! | 📶 WiFi Icon tự động nhảy vạch theo signal thực tế!"
        b_lbl = ctk.CTkLabel(banner, text=b_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        b_lbl.pack(padx=10, pady=6)

        # ── Body Grid (3 Columns: Left Toolbox, Center Canvas, Right Properties)
        body = ctk.CTkFrame(main_frame, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # 1. Left Toolbox (Presets & Sub-Element Add Buttons)
        left_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=240)
        left_box.pack(side="left", fill="y", padx=(0, 10))

        t_lbl = ctk.CTkLabel(left_box, text="📦 Preset Skins", font=ctk.CTkFont(size=14, weight="bold"))
        t_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.preset_combo = ctk.CTkOptionMenu(
            left_box,
            values=["Retro Dot Matrix LED Clock", "Cyberpunk Neon HUD"],
            command=self.load_preset
        )
        self.preset_combo.set("Retro Dot Matrix LED Clock")
        self.preset_combo.pack(fill="x", padx=10, pady=5)

        ctk.CTkFrame(left_box, fg_color="#30363d", height=1).pack(fill="x", padx=10, pady=10)

        w_lbl = ctk.CTkLabel(left_box, text="➕ Add Sub-Elements", font=ctk.CTkFont(size=12, weight="bold"))
        w_lbl.pack(anchor="w", padx=12, pady=(5, 5))

        for name, etype, content, def_w, def_h, def_col, font_st in ELEMENT_PRESETS:
            btn = ctk.CTkButton(
                left_box, text=f"+ {name}", anchor="w",
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda n=name, t=etype, c=content, w=def_w, h=def_h, col=def_col, f=font_st: self.add_sub_element(n, t, c, w, h, col, f)
            )
            btn.pack(fill="x", padx=10, pady=3)

        # 2. Center Interactive Canvas
        center_box = ctk.CTkFrame(body, fg_color="#090d16", corner_radius=10)
        center_box.pack(side="left", fill="both", expand=True)

        page_hdr = ctk.CTkFrame(center_box, fg_color="#161b22", height=40)
        page_hdr.pack(fill="x", padx=10, pady=(10, 5))

        p_title = ctk.CTkLabel(page_hdr, text="🖥️ Dashboard Page:", font=ctk.CTkFont(size=12, weight="bold"))
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

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # 3. Right Sub-Element Direct Inspector Panel
        right_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=270)
        right_box.pack(side="right", fill="y", padx=(10, 0))

        p_lbl = ctk.CTkLabel(right_box, text="⚙️ Sub-Element Inspector", font=ctk.CTkFont(size=14, weight="bold"))
        p_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.sel_name_lbl = ctk.CTkLabel(right_box, text="Click an object on canvas to edit", text_color="#8b949e", font=ctk.CTkFont(weight="bold"))
        self.sel_name_lbl.pack(anchor="w", padx=12, pady=(0, 5))

        # Text Content Edit Field
        c_lbl = ctk.CTkLabel(right_box, text="✏️ Text / Content:", font=ctk.CTkFont(size=11, weight="bold"))
        c_lbl.pack(anchor="w", padx=12, pady=(4, 1))

        self.entry_content = ctk.CTkEntry(right_box, width=240)
        self.entry_content.pack(padx=10, pady=2)

        apply_content_btn = ctk.CTkButton(right_box, text="Update Text Content", width=240, command=self.apply_text_content)
        apply_content_btn.pack(padx=10, pady=4)

        # Geometry controls (X, Y, W, H)
        geom_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        geom_frame.pack(fill="x", padx=10, pady=3)

        ctk.CTkLabel(geom_frame, text="X:").grid(row=0, column=0, padx=2, pady=2)
        self.entry_x = ctk.CTkEntry(geom_frame, width=65)
        self.entry_x.grid(row=0, column=1, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="Y:").grid(row=0, column=2, padx=2, pady=2)
        self.entry_y = ctk.CTkEntry(geom_frame, width=65)
        self.entry_y.grid(row=0, column=3, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="W:").grid(row=1, column=0, padx=2, pady=2)
        self.entry_w = ctk.CTkEntry(geom_frame, width=65)
        self.entry_w.grid(row=1, column=1, padx=2, pady=2)

        ctk.CTkLabel(geom_frame, text="H:").grid(row=1, column=2, padx=2, pady=2)
        self.entry_h = ctk.CTkEntry(geom_frame, width=65)
        self.entry_h.grid(row=1, column=3, padx=2, pady=2)

        apply_geom_btn = ctk.CTkButton(right_box, text="Apply Geometry (X,Y,W,H)", width=240, command=self.apply_manual_geometry)
        apply_geom_btn.pack(padx=10, pady=4)

        # Font Style Dropdown Selector
        f_lbl = ctk.CTkLabel(right_box, text="🔤 Font Style:", font=ctk.CTkFont(size=11, weight="bold"))
        f_lbl.pack(anchor="w", padx=12, pady=(4, 1))

        self.font_combo = ctk.CTkOptionMenu(
            right_box,
            values=["Dot Matrix LED", "7-Segment Digital", "Monospace Code", "Default Sans"],
            command=self.on_font_change, width=240
        )
        self.font_combo.set("Dot Matrix LED")
        self.font_combo.pack(padx=10, pady=2)

        # Color Picker Button
        self.color_btn = ctk.CTkButton(right_box, text="🎨 Element Color", width=240, fg_color="#21262d", command=self.pick_color)
        self.color_btn.pack(padx=10, pady=6)

        # Delete Element Button
        self.del_btn = ctk.CTkButton(
            right_box, text="🗑️ Delete Selected Sub-Element", width=240, fg_color="#da3633", hover_color="#f85149",
            command=self.delete_selected_element
        )
        self.del_btn.pack(side="bottom", padx=10, pady=15)

    def on_page_select(self, val):
        for i, name in enumerate(PAGE_NAMES):
            if name == val:
                self.current_page_idx = i
                break
        self.selected_elem_id = None
        self.redraw_canvas()

    def load_preset(self, preset_name):
        filename_map = {
            "Retro Dot Matrix LED Clock": "dot_matrix_led.json",
            "Cyberpunk Neon HUD": "cyberpunk_neon.json"
        }
        fname = filename_map.get(preset_name, "dot_matrix_led.json")
        path = os.path.join(PRESET_DIR, fname)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "pages" in data:
                    self.skin_data = data
                self.selected_elem_id = None
                self.redraw_canvas()
            except Exception as e:
                print(f"Error loading preset: {e}")

    def get_current_elements(self):
        pg_str = str(self.current_page_idx)
        if pg_str not in self.skin_data.get("pages", {}):
            self.skin_data.setdefault("pages", {})[pg_str] = {"name": PAGE_NAMES[self.current_page_idx], "elements": []}
        return self.skin_data["pages"][pg_str].setdefault("elements", [])

    def draw_dot_matrix_text(self, text, start_x, start_y, dot_size, pitch, on_color, off_color="#121212", elem_id=""):
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
                        fill=col_fill, outline="", tags=("element", elem_id)
                    )
            cur_x += 6 * pitch

    def draw_7segment_text(self, text, start_x, start_y, seg_w, seg_h, color, elem_id=""):
        cur_x = start_x
        for ch in text:
            if ch == ':':
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.3), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.3) + 4, fill=color, outline="", tags=("element", elem_id))
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.7), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.7) + 4, fill=color, outline="", tags=("element", elem_id))
                cur_x += int(seg_w * 0.5)
                continue

            mask = SEGMENT7_MASKS.get(ch, 0x00)
            off_col = "#151820"
            t = 4

            self.canvas.create_rectangle(cur_x + t, start_y, cur_x + seg_w - t, start_y + t, fill=color if (mask & 0x01) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + t, cur_x + seg_w, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x02) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), cur_x + seg_w, start_y + seg_h - t, fill=color if (mask & 0x04) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + t, start_y + seg_h - t, cur_x + seg_w - t, start_y + seg_h, fill=color if (mask & 0x08) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x, start_y + int(seg_h/2) + int(t/2), cur_x + t, start_y + seg_h - t, fill=color if (mask & 0x10) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x, start_y + t, cur_x + t, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x20) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + t, start_y + int(seg_h/2) - int(t/2), cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), fill=color if (mask & 0x40) else off_col, outline="", tags=("element", elem_id))

            cur_x += seg_w + 6

    def draw_wifi_signal_bars(self, ex, ey, color, elem_id):
        # Render 4 Dynamic WiFi Signal Bars (1..4 bars)
        for b in range(4):
            bx = ex + b * 5
            bh = 4 + b * 3
            by = ey + 12 - bh
            self.canvas.create_rectangle(bx, by, bx + 3, ey + 12, fill=color, outline="", tags=("element", elem_id))

    def draw_pixel_sun(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b1111111, 0b1111111, 0b0111110, 0b0011100]
        for r in range(7):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch
                    dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def draw_pixel_sunrise(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b0000000, 0b1111111]
        for r in range(5):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch
                    dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def redraw_canvas(self):
        self.canvas.delete("all")
        bg_col = self.skin_data.get("canvas", {}).get("bg_color", "#000000")
        self.canvas.configure(bg=bg_col)

        # Draw grid lines
        for x in range(0, int(CANVAS_WIDTH * SCALE), int(20 * SCALE)):
            self.canvas.create_line(x, 0, x, int(CANVAS_HEIGHT * SCALE), fill="#141418", dash=(2, 4))
        for y in range(0, int(CANVAS_HEIGHT * SCALE), int(20 * SCALE)):
            self.canvas.create_line(0, y, int(CANVAS_WIDTH * SCALE), y, fill="#141418", dash=(2, 4))

        elements = self.get_current_elements()

        if not elements:
            self.canvas.create_text(
                int(CANVAS_WIDTH * SCALE / 2), int(CANVAS_HEIGHT * SCALE / 2),
                text=f"[{PAGE_NAMES[self.current_page_idx]}]\nTrang chưa có Sub-Element. Nhấp +Add Sub-Elements bên trái.",
                fill="#484f58", font=("Segoe UI", 13), justify="center"
            )

        for elem in elements:
            ex = int(elem["x"] * SCALE)
            ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE)
            eh = int(elem["h"] * SCALE)
            eid = elem["id"]

            is_selected = (eid == self.selected_elem_id)
            color = elem.get("color", "#FFFFFF")
            font_style = elem.get("font_style", "default")
            etype = elem.get("type", "text")
            content = elem.get("content", "")

            # Render element visuals
            if etype == "wifi_signal":
                self.draw_wifi_signal_bars(ex, ey, color, eid)
                self.canvas.create_text(ex + 24, ey + int(eh/2), text="-54dBm", fill=color, font=("Consolas", int(4 * SCALE)), anchor="w", tags=("element", eid))
            elif etype == "status_time":
                self.canvas.create_text(ex, ey + int(eh/2), text="⏰ 14:35", fill=color, font=("Consolas", int(4.5 * SCALE), "bold"), anchor="w", tags=("element", eid))
            elif etype == "pixel_sun":
                self.draw_pixel_sun(ex, ey, dot_size=5, pitch=7, color=color, elem_id=eid)
            elif etype == "pixel_sunrise":
                self.draw_pixel_sunrise(ex, ey, dot_size=5, pitch=7, color=color, elem_id=eid)
            elif etype == "dot_matrix_divider":
                line_y = ey + int(eh / 2)
                for dx in range(ex, ex + ew, 8):
                    self.canvas.create_oval(dx, line_y, dx + 5, line_y + 5, fill=color, outline="", tags=("element", eid))
            elif etype == "line_chart":
                pts = [(ex, ey + eh), (ex + int(ew*0.25), ey + int(eh*0.4)), (ex + int(ew*0.5), ey + int(eh*0.7)), (ex + int(ew*0.75), ey + int(eh*0.2)), (ex + ew, ey + int(eh*0.5))]
                for i in range(len(pts) - 1):
                    self.canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], fill=color, width=2, tags=("element", eid))
            elif font_style == "dot_matrix" or etype == "matrix_text":
                self.draw_dot_matrix_text(content, ex, ey, dot_size=5, pitch=7, on_color=color, off_color="#121212", elem_id=eid)
            elif font_style == "segment7":
                self.draw_7segment_text(content, ex, ey, seg_w=18, seg_h=36, color=color, elem_id=eid)
            elif font_style == "mono":
                self.canvas.create_text(ex, ey + int(eh/2), text=content, fill=color, font=("Consolas", int(4.5 * SCALE), "bold"), anchor="w", tags=("element", eid))
            else:
                self.canvas.create_text(ex, ey + int(eh/2), text=content, fill=color, font=("Segoe UI", int(5.5 * SCALE), "bold"), anchor="w", tags=("element", eid))

            # Highlight selected element with crisp blue outline and corner handle
            if is_selected:
                self.canvas.create_rectangle(
                    ex - 3, ey - 3, ex + ew + 3, ey + eh + 3,
                    outline="#58a6ff", width=2, dash=(3, 3), tags=("selected", eid)
                )
                self.canvas.create_rectangle(
                    ex + ew - 4, ey + eh - 4, ex + ew + 6, ey + eh + 6,
                    fill="#58a6ff", outline="#ffffff", tags=("handle", eid)
                )

        self.update_inspector()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        elements = self.get_current_elements()

        # Check resize handle first
        for elem in elements:
            ex = int(elem["x"] * SCALE)
            ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE)
            eh = int(elem["h"] * SCALE)

            if (ex + ew - 6 <= x <= ex + ew + 8) and (ey + eh - 6 <= y <= ey + eh + 8):
                self.selected_elem_id = elem["id"]
                self.drag_data["handle"] = "resize"
                self.drag_data["elem"] = elem
                self.drag_data["x"] = x
                self.drag_data["y"] = y
                self.redraw_canvas()
                return

        # Check bounding box hit test for each sub-element directly!
        for elem in reversed(elements):
            ex = int(elem["x"] * SCALE)
            ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE)
            eh = int(elem["h"] * SCALE)

            if (ex - 4 <= x <= ex + ew + 4) and (ey - 4 <= y <= ey + eh + 4):
                self.selected_elem_id = elem["id"]
                self.drag_data["handle"] = "move"
                self.drag_data["elem"] = elem
                self.drag_data["x"] = x - ex
                self.drag_data["y"] = y - ey
                self.redraw_canvas()
                return

        self.selected_elem_id = None
        self.redraw_canvas()

    def on_canvas_drag(self, event):
        elem = self.drag_data.get("elem")
        if not elem:
            return

        if self.drag_data.get("handle") == "move":
            new_x = int((event.x - self.drag_data["x"]) / SCALE)
            new_y = int((event.y - self.drag_data["y"]) / SCALE)
            elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], new_x))
            elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], new_y))
            self.redraw_canvas()
        elif self.drag_data.get("handle") == "resize":
            new_w = int((event.x - int(elem["x"] * SCALE)) / SCALE)
            new_h = int((event.y - int(elem["y"] * SCALE)) / SCALE)
            elem["w"] = max(10, min(CANVAS_WIDTH - elem["x"], new_w))
            elem["h"] = max(8, min(CANVAS_HEIGHT - elem["y"], new_h))
            self.redraw_canvas()

    def on_canvas_release(self, event):
        self.drag_data["elem"] = None
        self.drag_data["handle"] = None

    def nudge_selected_element(self, dx, dy):
        elem = self.get_selected_element()
        if elem:
            elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], elem["x"] + dx))
            elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], elem["y"] + dy))
            self.redraw_canvas()

    def update_inspector(self):
        elem = self.get_selected_element()
        if elem:
            self.sel_name_lbl.configure(text=f"Selected: {elem['name']}", text_color="#58a6ff")
            self.entry_content.delete(0, tk.END); self.entry_content.insert(0, elem.get("content", ""))
            self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(elem["x"]))
            self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(elem["y"]))
            self.entry_w.delete(0, tk.END); self.entry_w.insert(0, str(elem["w"]))
            self.entry_h.delete(0, tk.END); self.entry_h.insert(0, str(elem["h"]))

            font_val_map = {
                "dot_matrix": "Dot Matrix LED",
                "segment7": "7-Segment Digital",
                "mono": "Monospace Code",
                "default": "Default Sans"
            }
            self.font_combo.set(font_val_map.get(elem.get("font_style", "default"), "Dot Matrix LED"))
            self.color_btn.configure(fg_color=elem.get("color", "#FFFFFF"))
        else:
            self.sel_name_lbl.configure(text="Click an object on canvas to edit", text_color="#8b949e")
            self.entry_content.delete(0, tk.END)
            self.entry_x.delete(0, tk.END)
            self.entry_y.delete(0, tk.END)
            self.entry_w.delete(0, tk.END)
            self.entry_h.delete(0, tk.END)

    def apply_text_content(self):
        elem = self.get_selected_element()
        if elem:
            elem["content"] = self.entry_content.get()
            self.redraw_canvas()

    def on_font_change(self, val):
        elem = self.get_selected_element()
        if elem:
            font_key_map = {
                "Dot Matrix LED": "dot_matrix",
                "7-Segment Digital": "segment7",
                "Monospace Code": "mono",
                "Default Sans": "default"
            }
            elem["font_style"] = font_key_map.get(val, "default")
            self.redraw_canvas()

    def apply_manual_geometry(self):
        elem = self.get_selected_element()
        if elem:
            try:
                elem["x"] = int(self.entry_x.get())
                elem["y"] = int(self.entry_y.get())
                elem["w"] = int(self.entry_w.get())
                elem["h"] = int(self.entry_h.get())
                self.redraw_canvas()
            except Exception:
                pass

    def pick_color(self):
        elem = self.get_selected_element()
        if elem:
            color = colorchooser.askcolor(title="Choose Sub-Element Color", color=elem.get("color", "#FFFFFF"))[1]
            if color:
                elem["color"] = color
                self.redraw_canvas()

    def add_sub_element(self, name, etype, content, def_w, def_h, def_col, font_st):
        elements = self.get_current_elements()
        new_id = f"elem_{len(elements) + 1}"
        new_elem = {
            "id": new_id,
            "name": name,
            "type": etype,
            "content": content,
            "font_style": font_st,
            "x": 10,
            "y": 10,
            "w": def_w,
            "h": def_h,
            "color": def_col
        }
        elements.append(new_elem)
        self.selected_elem_id = new_id
        self.redraw_canvas()

    def delete_selected_element(self):
        if self.selected_elem_id:
            elements = self.get_current_elements()
            self.skin_data["pages"][str(self.current_page_idx)]["elements"] = [el for el in elements if el["id"] != self.selected_elem_id]
            self.selected_elem_id = None
            self.redraw_canvas()

    def get_selected_element(self):
        for elem in self.get_current_elements():
            if elem["id"] == self.selected_elem_id:
                return elem
        return None

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Skin Layout", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.skin_data, f, indent=2, ensure_ascii=False)
                tk.messagebox.showinfo("Export Success", f"Granular Skin Layout JSON saved to:\n{path}")
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
                self.selected_elem_id = None
                self.redraw_canvas()
                tk.messagebox.showinfo("Import Success", "Skin Layout JSON successfully loaded!")
            except Exception as e:
                tk.messagebox.showerror("Import Error", f"Failed to load JSON file: {e}")

if __name__ == "__main__":
    app = SkinDesignerApp()
    app.mainloop()
