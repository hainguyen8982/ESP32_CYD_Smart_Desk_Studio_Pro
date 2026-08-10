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

WIDGET_TYPES = [
    ("Digital Clock & Lunar", "clock", 180, 65),
    ("Weather City & Forecast", "weather", 110, 65),
    ("CPU Arc Gauge", "gauge_cpu", 145, 80),
    ("RAM Load Meter", "gauge_ram", 145, 80),
    ("SJC Gold & XAUUSD", "gold_sjc", 300, 80),
    ("Hardware Line Chart", "line_chart", 300, 55)
]

class SkinDesignerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎨 Smart Desk Studio - Dashboard Skin Designer (Drag & Drop)")
        self.geometry("1180x760")
        self.resizable(True, True)

        self.skin_data = {
            "skin_name": "Custom Skin",
            "author": "User Designer",
            "version": "1.0",
            "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "bg_color": "#000000"},
            "widgets": []
        }

        self.selected_widget_id = None
        self.drag_data = {"x": 0, "y": 0, "widget": None, "handle": None}

        self.create_layout()
        self.load_preset("Cyberpunk Neon HUD")

    def create_layout(self):
        # ── Main Container ─────────────────────────────────────────────
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Header Bar ────────────────────────────────────────────────
        hdr = ctk.CTkFrame(main_frame, fg_color="#161b22", corner_radius=8, height=50)
        hdr.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            hdr, text="🎨 Smart Desk Studio — Interactive Layout & Skin Designer (320x240)",
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

        # ── Body Grid (3 Columns: Left Toolbox, Center Canvas, Right Properties)
        body = ctk.CTkFrame(main_frame, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # 1. Left Toolbox (Presets & Widget Library)
        left_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=220)
        left_box.pack(side="left", fill="y", padx=(0, 10))

        t_lbl = ctk.CTkLabel(left_box, text="📦 Preset Skins", font=ctk.CTkFont(size=14, weight="bold"))
        t_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.preset_combo = ctk.CTkOptionMenu(
            left_box,
            values=["Cyberpunk Neon HUD", "Nordic Minimalist Studio", "Luxury Gold & Finance"],
            command=self.load_preset
        )
        self.preset_combo.set("Cyberpunk Neon HUD")
        self.preset_combo.pack(fill="x", padx=10, pady=5)

        ctk.CTkFrame(left_box, fg_color="#30363d", height=1).pack(fill="x", padx=10, pady=10)

        w_lbl = ctk.CTkLabel(left_box, text="➕ Add Widgets", font=ctk.CTkFont(size=14, weight="bold"))
        w_lbl.pack(anchor="w", padx=12, pady=(5, 5))

        for name, wtype, def_w, def_h in WIDGET_TYPES:
            btn = ctk.CTkButton(
                left_box, text=f"+ {name}", anchor="w",
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda t=wtype, n=name, w=def_w, h=def_h: self.add_widget(n, t, w, h)
            )
            btn.pack(fill="x", padx=10, pady=3)

        # 2. Center Interactive Canvas (2.5x Scale = 800x600)
        center_box = ctk.CTkFrame(body, fg_color="#090d16", corner_radius=10)
        center_box.pack(side="left", fill="both", expand=True)

        c_info = ctk.CTkLabel(
            center_box, text="📺 Interactive Canvas (Scaled 2.5x - 320x240 TFT Ratio) | Drag to move, grab corner to resize",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        )
        c_info.pack(pady=(8, 2))

        # Tkinter Canvas
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
        right_box = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=10, width=240)
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

        apply_geom_btn = ctk.CTkButton(right_box, text="Apply Geometry", width=200, command=self.apply_manual_geometry)
        apply_geom_btn.pack(padx=10, pady=8)

        # Color Pickers
        col_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        col_frame.pack(fill="x", padx=10, pady=5)

        self.bg_col_btn = ctk.CTkButton(col_frame, text="Card BG Color", width=200, fg_color="#21262d", command=self.pick_bg_color)
        self.bg_col_btn.pack(pady=4)

        self.accent_col_btn = ctk.CTkButton(col_frame, text="Accent Color", width=200, fg_color="#21262d", command=self.pick_accent_color)
        self.accent_col_btn.pack(pady=4)

        # Delete Widget
        self.del_btn = ctk.CTkButton(
            right_box, text="🗑️ Delete Widget", width=200, fg_color="#da3633", hover_color="#f85149",
            command=self.delete_selected_widget
        )
        self.del_btn.pack(side="bottom", padx=10, pady=15)

    def load_preset(self, preset_name):
        filename_map = {
            "Cyberpunk Neon HUD": "cyberpunk_neon.json",
            "Nordic Minimalist Studio": "nordic_minimalist.json",
            "Luxury Gold & Finance": "luxury_gold.json"
        }
        fname = filename_map.get(preset_name, "cyberpunk_neon.json")
        path = os.path.join(PRESET_DIR, fname)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.skin_data = json.load(f)
                self.selected_widget_id = None
                self.redraw_canvas()
            except Exception as e:
                print(f"Error loading preset: {e}")

    def redraw_canvas(self):
        self.canvas.delete("all")
        bg_col = self.skin_data.get("canvas", {}).get("bg_color", "#000000")
        self.canvas.configure(bg=bg_col)

        # Draw subtle 10px grid lines
        for x in range(0, int(CANVAS_WIDTH * SCALE), int(20 * SCALE)):
            self.canvas.create_line(x, 0, x, int(CANVAS_HEIGHT * SCALE), fill="#161b22", dash=(2, 4))
        for y in range(0, int(CANVAS_HEIGHT * SCALE), int(20 * SCALE)):
            self.canvas.create_line(0, y, int(CANVAS_WIDTH * SCALE), y, fill="#161b22", dash=(2, 4))

        # Render Widgets
        for w in self.skin_data.get("widgets", []):
            wx = int(w["x"] * SCALE)
            wy = int(w["y"] * SCALE)
            ww = int(w["w"] * SCALE)
            wh = int(w["h"] * SCALE)
            wid = w["id"]

            is_selected = (wid == self.selected_widget_id)
            outline_col = "#58a6ff" if is_selected else "#30363d"
            outline_w = 3 if is_selected else 1

            # Card BG
            card_bg = w.get("bg_color", "#161b22")
            accent = w.get("accent_color", "#00D4FF")

            # Draw Card Rectangle
            self.canvas.create_rectangle(wx, wy, wx + ww, wy + wh, fill=card_bg, outline=outline_col, width=outline_w, tags=("widget", wid))

            # Widget Visual Simulation Mockup
            wtype = w.get("type", "")
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
                # Sample trendline
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

        # Check if clicked on a resize handle first
        for w in self.skin_data.get("widgets", []):
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
        for w in reversed(self.skin_data.get("widgets", [])):
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

    def update_inspector(self):
        w = self.get_selected_widget()
        if w:
            self.sel_name_lbl.configure(text=f"Selected: {w['name']}", text_color="#58a6ff")
            self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(w["x"]))
            self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(w["y"]))
            self.entry_w.delete(0, tk.END); self.entry_w.insert(0, str(w["w"]))
            self.entry_h.delete(0, tk.END); self.entry_h.insert(0, str(w["h"]))
            self.bg_col_btn.configure(fg_color=w.get("bg_color", "#161b22"))
            self.accent_col_btn.configure(fg_color=w.get("accent_color", "#00D4FF"))
        else:
            self.sel_name_lbl.configure(text="No widget selected", text_color="#8b949e")
            self.entry_x.delete(0, tk.END)
            self.entry_y.delete(0, tk.END)
            self.entry_w.delete(0, tk.END)
            self.entry_h.delete(0, tk.END)

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
            color = colorchooser.askcolor(title="Choose Accent Color", color=w.get("accent_color", "#00D4FF"))[1]
            if color:
                w["accent_color"] = color
                self.redraw_canvas()

    def add_widget(self, name, wtype, def_w, def_h):
        new_id = f"w_{len(self.skin_data['widgets']) + 1}_{wtype}"
        new_w = {
            "id": new_id,
            "name": name,
            "type": wtype,
            "x": 20,
            "y": 20,
            "w": def_w,
            "h": def_h,
            "bg_color": "#161b22",
            "accent_color": "#00D4FF",
            "text_color": "#FFFFFF"
        }
        self.skin_data["widgets"].append(new_w)
        self.selected_widget_id = new_id
        self.redraw_canvas()

    def delete_selected_widget(self):
        if self.selected_widget_id:
            self.skin_data["widgets"] = [w for w in self.skin_data["widgets"] if w["id"] != self.selected_widget_id]
            self.selected_widget_id = None
            self.redraw_canvas()

    def get_selected_widget(self):
        for w in self.skin_data.get("widgets", []):
            if w["id"] == self.selected_widget_id:
                return w
        return None

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Skin Layout", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.skin_data, f, indent=2, ensure_ascii=False)
                tk.messagebox.showinfo("Export Success", f"Skin Layout JSON successfully saved to:\n{path}")
            except Exception as e:
                tk.messagebox.showerror("Export Error", f"Failed to save JSON file: {e}")

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Skin Layout", "*.json")])
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.skin_data = json.load(f)
                self.selected_widget_id = None
                self.redraw_canvas()
                tk.messagebox.showinfo("Import Success", "Skin Layout JSON successfully loaded!")
            except Exception as e:
                tk.messagebox.showerror("Import Error", f"Failed to load JSON file: {e}")

if __name__ == "__main__":
    app = SkinDesignerApp()
    app.mainloop()
