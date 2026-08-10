import sys
import os
import time
import string
import json
import traceback
import threading
import unicodedata
import requests
import psutil
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser
import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk
import socket
import ctypes

def remove_vietnamese_accents(text):
    if not text:
        return ""
    s = text.replace('đ', 'd').replace('Đ', 'D')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return unicodedata.normalize('NFC', s)

# Windows Virtual Key Definitions for Media Controls
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP       = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF

active_serial_conn = None
serial_lock = threading.Lock()
app_instance = None

CANVAS_WIDTH = 320
CANVAS_HEIGHT = 240
SCALE = 2.2

PAGE_ITEMS = [
    ("P0", "🌤️ Weather & Clock", "Realtime Clock, City Weather & SJC Gold", "#38BDF8"),
    ("P1", "📆 Lunar Calendar", "Solar Date, Lunar Calendar & Good Hours", "#F472B6"),
    ("P2", "📈 Finance & Trading", "SJC Gold Rates & World Stock Tickers", "#FBBF24"),
    ("P3", "💻 PC Hardware Stats", "Realtime CPU Load, RAM & GPU Gauges", "#A855F7"),
    ("P4", "🚀 Net & Storage Disks", "Network Speed & Disks C:/ D:/ Usage", "#34D399"),
    ("P5", "⏳ Pomodoro Desk", "Productivity Desk Timer & Alarm Clock", "#FB7185"),
    ("P6", "🎵 Media Remote", "Spotify Track Title, Artist & Volume", "#818CF8"),
    ("P7", "⚙️ System Settings", "WiFi RSSI, IP, LDR Brightness & Calib", "#94A3B8")
]

PAGE_NAMES = [f"{p[0]} • {p[1]}" for p in PAGE_ITEMS]

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

SEGMENT7_MASKS = {
    '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F, '4': 0x66,
    '5': 0x6D, '6': 0x7D, '7': 0x07, '8': 0x7F, '9': 0x6F,
    '-': 0x40, ' ': 0x00
}

ELEMENT_PRESETS = [
    ("WiFi Signal Icon", "wifi_signal", "RSSI -54dBm", 55, 14, "#00E676", "mono"),
    ("WiFi IP Address Text", "text", "192.168.1.13", 75, 14, "#00E676", "mono"),
    ("PC Serial Status Icon", "text", "[USB Connected]", 45, 14, "#38BDF8", "mono"),
    ("Page Title & Icon", "text", "Weather Clock", 110, 14, "#FFD700", "default"),
    ("Page Counter Index", "text", "0/7", 30, 14, "#8B949E", "mono"),
    ("Status Bar Time", "status_time", "14:35", 55, 14, "#FFFFFF", "mono"),
    ("Digital Clock Digits", "matrix_text", "14:35:08", 170, 35, "#00F5FF", "dot_matrix"),
    ("Solar & Lunar Date", "text", "Mon 10/08 • 18/07 Lunar", 170, 18, "#8B949E", "default"),
    ("Dot Matrix Sun Icon", "pixel_sun", "sun", 50, 50, "#FFCC00", "dot_matrix"),
    ("Dot Matrix Sunrise Icon", "pixel_sunrise", "sunrise", 50, 50, "#FF9900", "dot_matrix"),
    ("Dot Matrix Red Divider", "dot_matrix_divider", "line", 290, 10, "#FF3333", "dot_matrix"),
    ("Weather City & Temp", "text", "28°C Hanoi", 110, 30, "#FFFFFF", "default"),
    ("Hardware Line Chart", "line_chart", "chart", 300, 55, "#CC00FF", "mono")
]

COLOR_PALETTES = {
    "Cyberpunk Neon": {"accent": "#00F5FF", "sec": "#FF00CC", "bg": "#140026", "line": "#39FF14"},
    "Nordic Slate": {"accent": "#38BDF8", "sec": "#94A3B8", "bg": "#0F172A", "line": "#10B981"},
    "Luxury Gold": {"accent": "#FFD700", "sec": "#FFF8DC", "bg": "#0B0B0E", "line": "#FFA500"},
    "Retro CRT": {"accent": "#00FF41", "sec": "#009926", "bg": "#000000", "line": "#00FF41"}
}

VN_CITIES = [
    ("Hanoi", "Hà Nội"), ("Ho Chi Minh", "TP. Hồ Chí Minh"), ("Da Nang", "Đà Nẵng"),
    ("Hai Phong", "Hải Phòng"), ("Can Tho", "Cần Thơ"), ("Nha Trang", "Nha Trang"),
    ("Da Lat", "Đà Lạt"), ("Hue", "Hue"), ("Vung Tau", "Vũng Tàu")
]

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SmartDeskStudioProApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("👑 Smart Desk Studio Pro — Unified Dashboard & Skin Designer")
        self.geometry("1400x920")
        self.resizable(True, True)

        # Deep Obsidian Charcoal Theme (#0b0f19)
        self.configure(fg_color="#0b0f19")

        # Explicit Window Close Protocol to release Serial port & kill background Python process
        self.protocol("WM_DELETE_WINDOW", self.on_app_close)

        # Robust Window Maximization for CustomTkinter on Windows
        self.after(100, lambda: self._maximize_window())
        self.after(300, lambda: self._maximize_window())

        global app_instance
        app_instance = self

        self.esp32_ip = "192.168.1.13"
        self.cached_ip = "192.168.1.13"
        self.cached_com_port = ""
        self.selected_com_port = "AUTO"
        self.is_streaming = True
        self.active_cyd_page = 0
        self.last_net = None
        self.last_time = time.time()
        self.last_port_scan = 0

        # Thread-safe control dictionary for merging commands into Serial JSON stream
        self.pending_control = {}

        self.current_page_idx = 0
        self.selected_elem_id = None
        self.drag_data = {"x": 0, "y": 0, "elem": None, "handle": None}
        self.skin_data = {
            "skin_name": "Unified Studio Skin",
            "author": "Smart Desk Studio Pro",
            "version": "2.5",
            "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "bg_color": "#000000"},
            "pages": {}
        }
        for i in range(8):
            self.skin_data["pages"][str(i)] = {"name": PAGE_NAMES[i], "elements": []}

        self.create_unified_ui()
        self.bind_keyboard_shortcuts()
        self.refresh_com_ports()

        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

    def on_app_close(self):
        """Clean shutdown handler: close Serial port & terminate process immediately."""
        self.is_streaming = False
        global active_serial_conn
        with serial_lock:
            if active_serial_conn and active_serial_conn.is_open:
                try:
                    active_serial_conn.close()
                except Exception:
                    pass
                active_serial_conn = None
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _maximize_window(self):
        try:
            if sys.platform == "win32":
                self.state('zoomed')
        except Exception:
            pass

    def bind_keyboard_shortcuts(self):
        self.bind("<Delete>", lambda e: self.delete_selected_element())
        self.bind("<BackSpace>", lambda e: self.delete_selected_element())
        self.bind("<Up>", lambda e: self.nudge_selected_element(0, -1))
        self.bind("<Down>", lambda e: self.nudge_selected_element(0, 1))
        self.bind("<Left>", lambda e: self.nudge_selected_element(-1, 0))
        self.bind("<Right>", lambda e: self.nudge_selected_element(1, 0))

    def create_unified_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=12, pady=12)

        # ── Header Status Bar with Manual COM Selector ─────────────────
        hdr = ctk.CTkFrame(main_container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, height=55)
        hdr.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            hdr, text="👑 Smart Desk Studio Pro", font=ctk.CTkFont(size=18, weight="bold"), text_color="#38bdf8"
        )
        title_lbl.pack(side="left", padx=15, pady=8)

        # COM Selector Frame
        com_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        com_frame.pack(side="left", padx=20, pady=8)

        ctk.CTkLabel(com_frame, text="🔌 Port:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left", padx=(0, 5))
        self.com_combo = ctk.CTkOptionMenu(com_frame, values=["Auto Detect"], width=150, command=self.on_com_select)
        self.com_combo.pack(side="left", padx=2)

        ref_btn = ctk.CTkButton(com_frame, text="🔄", width=32, height=28, fg_color="#1f2937", hover_color="#374151", command=self.refresh_com_ports)
        ref_btn.pack(side="left", padx=4)

        self.status_lbl = ctk.CTkLabel(
            hdr, text="🟡 Standby Mode (Check Cable / COM Port)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#EAB308"
        )
        self.status_lbl.pack(side="right", padx=15, pady=8)

        # ── Full Width Custom Tab Segmented Header ──────────────────────
        self.tab_hdr_frame = ctk.CTkFrame(main_container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, height=45)
        self.tab_hdr_frame.pack(fill="x", pady=(0, 8))

        self.tab_btn_live = ctk.CTkButton(
            self.tab_hdr_frame, text="🖥️ Live Control Center", font=ctk.CTkFont(size=13, weight="bold"),
            height=36, fg_color="#1f2937", hover_color="#374151", text_color="#38bdf8",
            command=lambda: self.switch_main_tab("live")
        )
        self.tab_btn_live.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        self.tab_btn_designer = ctk.CTkButton(
            self.tab_hdr_frame, text="🎨 Skin Designer Studio", font=ctk.CTkFont(size=13, weight="bold"),
            height=36, fg_color="transparent", hover_color="#374151", text_color="#94a3b8",
            command=lambda: self.switch_main_tab("designer")
        )
        self.tab_btn_designer.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        self.tab_btn_settings = ctk.CTkButton(
            self.tab_hdr_frame, text="⚙️ System Settings", font=ctk.CTkFont(size=13, weight="bold"),
            height=36, fg_color="transparent", hover_color="#374151", text_color="#94a3b8",
            command=lambda: self.switch_main_tab("settings")
        )
        self.tab_btn_settings.pack(side="left", fill="x", expand=True, padx=4, pady=4)

        # Main Tab Body Stack Frame
        self.body_stack = ctk.CTkFrame(main_container, fg_color="transparent")
        self.body_stack.pack(fill="both", expand=True)

        self.view_live = ctk.CTkFrame(self.body_stack, fg_color="transparent")
        self.view_designer = ctk.CTkFrame(self.body_stack, fg_color="transparent")
        self.view_settings = ctk.CTkFrame(self.body_stack, fg_color="transparent")

        self.view_live.pack(fill="both", expand=True)

        self.build_tab_live()
        self.build_tab_designer()
        self.build_tab_settings()

    def switch_main_tab(self, tab_name):
        self.view_live.pack_forget()
        self.view_designer.pack_forget()
        self.view_settings.pack_forget()

        self.tab_btn_live.configure(fg_color="transparent", text_color="#94a3b8")
        self.tab_btn_designer.configure(fg_color="transparent", text_color="#94a3b8")
        self.tab_btn_settings.configure(fg_color="transparent", text_color="#94a3b8")

        if tab_name == "live":
            self.view_live.pack(fill="both", expand=True)
            self.tab_btn_live.configure(fg_color="#1f2937", text_color="#38bdf8")
        elif tab_name == "designer":
            self.view_designer.pack(fill="both", expand=True)
            self.tab_btn_designer.configure(fg_color="#1f2937", text_color="#38bdf8")
            self.redraw_canvas()
        elif tab_name == "settings":
            self.view_settings.pack(fill="both", expand=True)
            self.tab_btn_settings.configure(fg_color="#1f2937", text_color="#38bdf8")

    def refresh_com_ports(self):
        ports = list(serial.tools.list_ports.comports())
        val_list = ["Auto Detect"]
        for p in ports:
            p_desc = str(p.description)
            val_list.append(f"{p.device} ({p_desc})")
        self.com_combo.configure(values=val_list)

    def on_com_select(self, val):
        if val == "Auto Detect":
            self.selected_com_port = "AUTO"
        else:
            self.selected_com_port = val.split(" ")[0].strip()
        self.force_reconnect()

    # ── TAB 1: LIVE CONTROL CENTER ────────────────────────────────────
    def build_tab_live(self):
        container = ctk.CTkFrame(self.view_live, fg_color="transparent")
        container.pack(fill="both", expand=True)

        col_left = ctk.CTkScrollableFrame(container, fg_color="transparent")
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        col_right = ctk.CTkFrame(container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, width=540)
        col_right.pack(side="right", fill="both", expand=False, padx=(0, 0))

        # 1. Telemetry Cards
        tele_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        tele_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(tele_frame, text="📊 Live PC Telemetry Metrics", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        m_grid = ctk.CTkFrame(tele_frame, fg_color="transparent")
        m_grid.pack(fill="x", padx=10, pady=(0, 10))

        cpu_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        cpu_box.grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(cpu_box, text="CPU LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_cpu = ctk.CTkLabel(cpu_box, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#00F5FF")
        self.lbl_cpu.pack(anchor="w", padx=10, pady=1)
        self.bar_cpu = ctk.CTkProgressBar(cpu_box, height=5, progress_color="#00F5FF", fg_color="#1f2937")
        self.bar_cpu.set(0.0); self.bar_cpu.pack(fill="x", padx=10, pady=(0, 8))

        ram_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        ram_box.grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(ram_box, text="RAM LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_ram = ctk.CTkLabel(ram_box, text="0%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#AB47BC")
        self.lbl_ram.pack(anchor="w", padx=10, pady=1)
        self.bar_ram = ctk.CTkProgressBar(ram_box, height=5, progress_color="#AB47BC", fg_color="#1f2937")
        self.bar_ram.set(0.0); self.bar_ram.pack(fill="x", padx=10, pady=(0, 8))

        down_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        down_box.grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(down_box, text="NET DOWN", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_down = ctk.CTkLabel(down_box, text="0 KB/s", font=ctk.CTkFont(size=17, weight="bold"), text_color="#00E676")
        self.lbl_net_down.pack(anchor="w", padx=10, pady=1)
        self.bar_net_down = ctk.CTkProgressBar(down_box, height=5, progress_color="#00E676", fg_color="#1f2937")
        self.bar_net_down.set(0.0); self.bar_net_down.pack(fill="x", padx=10, pady=(0, 8))

        up_box = ctk.CTkFrame(m_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
        up_box.grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        ctk.CTkLabel(up_box, text="NET UP", font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_up = ctk.CTkLabel(up_box, text="0 KB/s", font=ctk.CTkFont(size=17, weight="bold"), text_color="#FFA726")
        self.lbl_net_up.pack(anchor="w", padx=10, pady=1)
        self.bar_net_up = ctk.CTkProgressBar(up_box, height=5, progress_color="#FFA726", fg_color="#1f2937")
        self.bar_net_up.set(0.0); self.bar_net_up.pack(fill="x", padx=10, pady=(0, 8))

        for c_i in range(4): m_grid.columnconfigure(c_i, weight=1)

        # 2. Rich Page Switcher Grid
        p_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        p_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(p_frame, text="🖥️ Switch Dashboard Page (Pages P0 .. P7)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 10))

        self.page_btns = []
        for pid in range(8):
            row = pid // 2; col = pid % 2
            p_code, p_title, p_sub, p_color = PAGE_ITEMS[pid]

            btn_box = ctk.CTkFrame(p_grid, fg_color="#030712", border_width=1, border_color="#1f2937", corner_radius=8)
            btn_box.grid(row=row, column=col, padx=4, pady=3, sticky="ew")

            btn_box.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))

            badge_lbl = ctk.CTkLabel(btn_box, text=f" {p_code} ", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1f2937", text_color=p_color, corner_radius=4)
            badge_lbl.pack(side="left", padx=8, pady=6)

            txt_inner = ctk.CTkFrame(btn_box, fg_color="transparent")
            txt_inner.pack(side="left", fill="x", expand=True, padx=2, pady=4)

            title_lbl = ctk.CTkLabel(txt_inner, text=p_title, font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFFFFF", anchor="w")
            title_lbl.pack(anchor="w", pady=0)

            sub_lbl = ctk.CTkLabel(txt_inner, text=p_sub, font=ctk.CTkFont(size=10), text_color="#94a3b8", anchor="w")
            sub_lbl.pack(anchor="w", pady=0)

            badge_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            txt_inner.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            title_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))
            sub_lbl.bind("<Button-1>", lambda e, p=pid: self.switch_page(p))

            self.page_btns.append(btn_box)

        for col_i in range(2): p_grid.columnconfigure(col_i, weight=1)

        self._highlight_page_button(0)

        # 3. Preset Theme Switcher
        th_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        th_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(th_frame, text="🎨 Preset Firmware Theme Switcher", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        th_grid = ctk.CTkFrame(th_frame, fg_color="transparent")
        th_grid.pack(fill="x", padx=10, pady=(0, 10))

        preset_themes = [
            ("Ocean Dark", "ocean_dark", "#38BDF8"),
            ("Cyberpunk Neon", "cyberpunk", "#FF00CC"),
            ("Forest Slate", "forest", "#10B981"),
            ("Cherry Blossom", "cherry", "#F472B6"),
            ("Light Day", "light_day", "#0284C7"),
            ("Retro Green", "retro_green", "#00FF41")
        ]

        for idx, (tname, tkey, acc_col) in enumerate(preset_themes):
            row = idx // 3; col = idx % 3
            t_btn = ctk.CTkButton(
                th_grid, text=f"✨ {tname}", font=ctk.CTkFont(size=12, weight="bold"),
                height=36, fg_color="#030712", hover_color="#1f2937", text_color=acc_col,
                border_width=1, border_color="#1f2937",
                command=lambda k=tkey: self.apply_theme(k)
            )
            t_btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

        for col_i in range(3): th_grid.columnconfigure(col_i, weight=1)

        # 4. Weather Location & Currency Settings
        w_frame = ctk.CTkFrame(col_left, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        w_frame.pack(fill="x", pady=6)

        ctk.CTkLabel(w_frame, text="🌤️ Weather Location & 💱 Foreign Exchange Currencies", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(10, 6))

        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 12))

        city_names = [c[1] for c in VN_CITIES]
        self.city_combo = ctk.CTkOptionMenu(w_inner, values=city_names, width=150)
        self.city_combo.set("Hà Nội"); self.city_combo.pack(side="left", padx=(0, 6))

        set_city_btn = ctk.CTkButton(w_inner, text="Set City", width=80, command=self.apply_city)
        set_city_btn.pack(side="left", padx=(0, 15))

        currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW"]
        self.cur1_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=75)
        self.cur1_combo.set("USD"); self.cur1_combo.pack(side="left", padx=(0, 4))

        self.cur2_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=75)
        self.cur2_combo.set("EUR"); self.cur2_combo.pack(side="left", padx=(0, 8))

        set_cur_btn = ctk.CTkButton(w_inner, text="Set FX", width=80, command=self.apply_currencies)
        set_cur_btn.pack(side="left")

        # ── RIGHT COLUMN CONTENTS (LIVE DIGITAL TWIN SIMULATION) ─────
        ctk.CTkLabel(col_right, text="📺 Digital Twin Simulation", font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(col_right, text="320x240 TFT LCD • Realtime Sync Hardware Preview", font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=15, pady=(0, 10))

        sim_canvas_frame = ctk.CTkFrame(col_right, fg_color="#000000", border_width=3, border_color="#1f2937", corner_radius=10)
        sim_canvas_frame.pack(padx=15, pady=5)

        self.sim_canvas = tk.Canvas(sim_canvas_frame, width=320, height=240, bg="#000000", highlightthickness=0)
        self.sim_canvas.pack(padx=6, pady=6)
        self.draw_sim_canvas_preview()

        act_frame = ctk.CTkFrame(col_right, fg_color="transparent")
        act_frame.pack(fill="x", padx=15, pady=15)

        sync_now_btn = ctk.CTkButton(
            act_frame, text="⚡ 1-Click Sync to Desk", font=ctk.CTkFont(weight="bold"),
            height=40, fg_color="#238636", hover_color="#2ea043", command=self.sync_to_cyd_desk
        )
        sync_now_btn.pack(fill="x", pady=4)

        recon_btn = ctk.CTkButton(
            act_frame, text="🔄 Force Reconnect USB/WiFi", font=ctk.CTkFont(weight="bold"),
            height=36, fg_color="#1f2937", hover_color="#374151", text_color="#38bdf8", command=self.force_reconnect
        )
        recon_btn.pack(fill="x", pady=4)

    def draw_sim_canvas_preview(self):
        if not hasattr(self, 'sim_canvas'): return
        self.sim_canvas.delete("all")
        self.sim_canvas.configure(bg="#000000")

        pid = self.active_cyd_page
        p_code, p_title, _, _ = PAGE_ITEMS[pid]
        self.sim_canvas.create_rectangle(0, 0, 320, 20, fill="#111827", outline="")
        self.sim_canvas.create_text(8, 10, text="RSSI -54dBm", fill="#00E676", font=("Consolas", 8), anchor="w")
        self.sim_canvas.create_text(160, 10, text=p_title, fill="#FFD700", font=("Segoe UI", 9, "bold"), anchor="center")
        self.sim_canvas.create_text(312, 10, text=f"{pid}/7", fill="#8B949E", font=("Consolas", 8), anchor="e")

        if pid == 0:
            self.sim_canvas.create_text(160, 100, text="14:35:08", fill="#00F5FF", font=("Consolas", 28, "bold"), anchor="center")
            self.sim_canvas.create_text(160, 150, text="Mon 10/08 • 18/07 Lunar", fill="#8B949E", font=("Segoe UI", 11), anchor="center")
            self.sim_canvas.create_text(160, 190, text="28°C Hanoi • Gold SJC 85.5M", fill="#FFFFFF", font=("Segoe UI", 11, "bold"), anchor="center")
        elif pid == 3:
            self.sim_canvas.create_text(80, 80, text="CPU: 34%", fill="#00F5FF", font=("Consolas", 14, "bold"), anchor="center")
            self.sim_canvas.create_text(240, 80, text="RAM: 70%", fill="#AB47BC", font=("Consolas", 14, "bold"), anchor="center")
            self.sim_canvas.create_rectangle(20, 120, 140, 140, fill="#1f2937", outline="")
            self.sim_canvas.create_rectangle(20, 120, 20 + int(120*0.34), 140, fill="#00F5FF", outline="")
            self.sim_canvas.create_rectangle(180, 120, 300, 140, fill="#1f2937", outline="")
            self.sim_canvas.create_rectangle(180, 120, 180 + int(120*0.70), 140, fill="#AB47BC", outline="")

    # ── TAB 2: SKIN DESIGNER STUDIO ───────────────────────────────────
    def build_tab_designer(self):
        body = ctk.CTkFrame(self.view_designer, fg_color="transparent")
        body.pack(fill="both", expand=True)

        pal_bar = ctk.CTkFrame(body, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=8, height=45)
        pal_bar.pack(fill="x", pady=(0, 8))

        p_lbl = ctk.CTkLabel(pal_bar, text="🎨 1-Click Theme:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        p_lbl.pack(side="left", padx=10, pady=6)

        for pal_name in COLOR_PALETTES:
            p_btn = ctk.CTkButton(
                pal_bar, text=f"✨ {pal_name}", width=110, height=24,
                fg_color="#030712", hover_color="#1f2937", text_color="#c9d1d9",
                border_width=1, border_color="#1f2937",
                command=lambda name=pal_name: self.apply_palette(name)
            )
            p_btn.pack(side="left", padx=3, pady=6)

        sync_btn = ctk.CTkButton(
            pal_bar, text="⚡ 1-Click Sync to Desk", width=160, fg_color="#238636", hover_color="#2ea043",
            font=ctk.CTkFont(weight="bold"), command=self.sync_to_cyd_desk
        )
        sync_btn.pack(side="right", padx=10, pady=6)

        grid_frame = ctk.CTkFrame(body, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        left_box = ctk.CTkFrame(grid_frame, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, width=220)
        left_box.pack(side="left", fill="y", padx=(0, 8))

        w_lbl = ctk.CTkLabel(left_box, text="+ Add Sub-Elements", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8")
        w_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        for name, etype, content, def_w, def_h, def_col, font_st in ELEMENT_PRESETS:
            btn = ctk.CTkButton(
                left_box, text=f"+ {name}", anchor="w",
                fg_color="#030712", hover_color="#1f2937", text_color="#c9d1d9",
                border_width=1, border_color="#1f2937",
                command=lambda n=name, t=etype, c=content, w=def_w, h=def_h, col=def_col, f=font_st: self.add_sub_element(n, t, c, w, h, col, f)
            )
            btn.pack(fill="x", padx=8, pady=2)

        center_box = ctk.CTkFrame(grid_frame, fg_color="#000000", border_width=1, border_color="#1f2937", corner_radius=10)
        center_box.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            center_box, width=int(CANVAS_WIDTH * SCALE), height=int(CANVAS_HEIGHT * SCALE),
            bg="#000000", highlightthickness=2, highlightbackground="#1f2937"
        )
        self.canvas.pack(padx=10, pady=10)

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        right_box = ctk.CTkFrame(grid_frame, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10, width=250)
        right_box.pack(side="right", fill="y", padx=(8, 0))

        p_lbl = ctk.CTkLabel(right_box, text="⚙️ Sub-Element Inspector", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
        p_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.sel_name_lbl = ctk.CTkLabel(right_box, text="Click object to edit", text_color="#64748b", font=ctk.CTkFont(weight="bold"))
        self.sel_name_lbl.pack(anchor="w", padx=12, pady=(0, 5))

        c_lbl = ctk.CTkLabel(right_box, text="Text Content:", font=ctk.CTkFont(size=11, weight="bold"))
        c_lbl.pack(anchor="w", padx=12, pady=(2, 1))

        self.entry_content = ctk.CTkEntry(right_box, width=220)
        self.entry_content.pack(padx=10, pady=2)

        apply_content_btn = ctk.CTkButton(right_box, text="Update Text", width=220, command=self.apply_text_content)
        apply_content_btn.pack(padx=10, pady=3)

        geom_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        geom_frame.pack(fill="x", padx=10, pady=2)

        ctk.CTkLabel(geom_frame, text="X:").grid(row=0, column=0, padx=2, pady=1)
        self.entry_x = ctk.CTkEntry(geom_frame, width=55); self.entry_x.grid(row=0, column=1, padx=2, pady=1)
        ctk.CTkLabel(geom_frame, text="Y:").grid(row=0, column=2, padx=2, pady=1)
        self.entry_y = ctk.CTkEntry(geom_frame, width=55); self.entry_y.grid(row=0, column=3, padx=2, pady=1)
        ctk.CTkLabel(geom_frame, text="W:").grid(row=1, column=0, padx=2, pady=1)
        self.entry_w = ctk.CTkEntry(geom_frame, width=55); self.entry_w.grid(row=1, column=1, padx=2, pady=1)
        ctk.CTkLabel(geom_frame, text="H:").grid(row=1, column=2, padx=2, pady=1)
        self.entry_h = ctk.CTkEntry(geom_frame, width=55); self.entry_h.grid(row=1, column=3, padx=2, pady=1)

        apply_geom_btn = ctk.CTkButton(right_box, text="Apply Geometry", width=220, command=self.apply_manual_geometry)
        apply_geom_btn.pack(padx=10, pady=3)

        f_lbl = ctk.CTkLabel(right_box, text="Font Style:", font=ctk.CTkFont(size=11, weight="bold"))
        f_lbl.pack(anchor="w", padx=12, pady=(3, 1))

        self.font_combo = ctk.CTkOptionMenu(
            right_box, values=["Dot Matrix LED", "7-Segment Digital", "Monospace Code", "Default Sans"],
            command=self.on_font_change, width=220
        )
        self.font_combo.set("Dot Matrix LED"); self.font_combo.pack(padx=10, pady=2)

        self.color_btn = ctk.CTkButton(right_box, text="Element Color", width=220, fg_color="#1f2937", command=self.pick_color)
        self.color_btn.pack(padx=10, pady=4)

        self.del_btn = ctk.CTkButton(
            right_box, text="Delete Sub-Element", width=220, fg_color="#da3633", hover_color="#f85149",
            command=self.delete_selected_element
        )
        self.del_btn.pack(side="bottom", padx=10, pady=12)

    # ── TAB 3: SYSTEM SETTINGS ────────────────────────────────────────
    def build_tab_settings(self):
        container = ctk.CTkFrame(self.view_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        s_frame = ctk.CTkFrame(container, fg_color="#111827", border_width=1, border_color="#1f2937", corner_radius=10)
        s_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(s_frame, text="⚙️ App & Connection Settings", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=12, pady=(10, 5))

        ip_inner = ctk.CTkFrame(s_frame, fg_color="transparent")
        ip_inner.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(ip_inner, text="CYD WiFi IP Address:").pack(side="left", padx=(0, 10))
        self.ip_entry = ctk.CTkEntry(ip_inner, width=180)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left")

        self.autostart_var = ctk.BooleanVar(value=True)
        autostart_chk = ctk.CTkCheckBox(s_frame, text="Run Smart Desk Studio Pro on Windows Startup", variable=self.autostart_var)
        autostart_chk.pack(anchor="w", padx=12, pady=8)

    # ── CANVAS DRAWING METHODS ────────────────────────────────────────
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
                    dx = cur_x + col * pitch; dy = start_y + row * pitch
                    col_fill = on_color if is_on else off_color
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=col_fill, outline="", tags=("element", elem_id))
            cur_x += 6 * pitch

    def draw_7segment_text(self, text, start_x, start_y, seg_w, seg_h, color, elem_id=""):
        cur_x = start_x
        for ch in text:
            if ch == ':':
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.3), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.3) + 4, fill=color, outline="", tags=("element", elem_id))
                self.canvas.create_rectangle(cur_x + int(seg_w/2) - 2, start_y + int(seg_h*0.7), cur_x + int(seg_w/2) + 2, start_y + int(seg_h*0.7) + 4, fill=color, outline="", tags=("element", elem_id))
                cur_x += int(seg_w * 0.5); continue

            mask = SEGMENT7_MASKS.get(ch, 0x00); off_col = "#151820"; t = 3
            self.canvas.create_rectangle(cur_x + t, start_y, cur_x + seg_w - t, start_y + t, fill=color if (mask & 0x01) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + t, cur_x + seg_w, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x02) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), cur_x + seg_w, start_y + seg_h - t, fill=color if (mask & 0x04) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + t, start_y + seg_h - t, cur_x + seg_w - t, start_y + seg_h, fill=color if (mask & 0x08) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x, start_y + int(seg_h/2) + int(t/2), cur_x + t, start_y + seg_h - t, fill=color if (mask & 0x10) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x, start_y + t, cur_x + t, start_y + int(seg_h/2) - int(t/2), fill=color if (mask & 0x20) else off_col, outline="", tags=("element", elem_id))
            self.canvas.create_rectangle(cur_x + t, start_y + int(seg_h/2) - int(t/2), cur_x + seg_w - t, start_y + int(seg_h/2) + int(t/2), fill=color if (mask & 0x40) else off_col, outline="", tags=("element", elem_id))
            cur_x += seg_w + 5

    def draw_pixel_sun(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b1111111, 0b1111111, 0b0111110, 0b0011100]
        for r in range(7):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch; dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def draw_pixel_sunrise(self, start_x, start_y, dot_size, pitch, color, elem_id=""):
        sun_map = [0b0011100, 0b0111110, 0b1111111, 0b0000000, 0b1111111]
        for r in range(5):
            bits = sun_map[r]
            for c in range(7):
                if (bits >> (6 - c)) & 1:
                    dx = start_x + c * pitch; dy = start_y + r * pitch
                    self.canvas.create_oval(dx, dy, dx + dot_size, dy + dot_size, fill=color, outline="", tags=("element", elem_id))

    def draw_floating_toolbar(self, elem):
        ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
        tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
        tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

        self.canvas.create_rectangle(tb_x, tb_y, tb_x + 180, tb_y + 24, fill="#111827", outline="#38bdf8", width=1, tags="floating_tb")
        colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
        for idx, col in enumerate(colors):
            cx = tb_x + 12 + idx * 22; cy = tb_y + 12
            self.canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, fill=col, outline="#000000", tags=("floating_tb", f"col_{col}"))
        self.canvas.create_text(tb_x + 150, tb_y + 12, text="🗑️", fill="#f85149", font=("Segoe UI", 9), tags=("floating_tb", "quick_del"))

    def redraw_canvas(self):
        self.canvas.delete("all")
        bg_col = self.skin_data.get("canvas", {}).get("bg_color", "#000000")
        self.canvas.configure(bg=bg_col)

        for x in range(0, int(CANVAS_WIDTH * SCALE), int(20 * SCALE)):
            self.canvas.create_line(x, 0, x, int(CANVAS_HEIGHT * SCALE), fill="#141418", dash=(2, 4))
        for y in range(0, int(CANVAS_HEIGHT * SCALE), int(20 * SCALE)):
            self.canvas.create_line(0, y, int(CANVAS_WIDTH * SCALE), y, fill="#141418", dash=(2, 4))

        elements = self.get_current_elements()

        if not elements:
            self.canvas.create_text(
                int(CANVAS_WIDTH * SCALE / 2), int(CANVAS_HEIGHT * SCALE / 2),
                text=f"[{PAGE_NAMES[self.current_page_idx]}]\nTrang chưa có Sub-Element. Nhấp +Add Sub-Elements bên trái.",
                fill="#484f58", font=("Segoe UI", 12), justify="center"
            )

        for elem in elements:
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            eid = elem["id"]

            is_selected = (eid == self.selected_elem_id)
            color = elem.get("color", "#FFFFFF")
            font_style = elem.get("font_style", "default")
            etype = elem.get("type", "text")
            content = elem.get("content", "")

            if etype == "wifi_signal":
                for b in range(4):
                    bx = ex + b * 4; bh = 3 + b * 2; by = ey + 10 - bh
                    self.canvas.create_oval(bx, by, bx + 3, by + 3, fill=color, outline="", tags=("element", eid))
                self.canvas.create_text(ex + 20, ey + int(eh/2), text="-54dBm", fill=color, font=("Consolas", int(3.5 * SCALE)), anchor="w", tags=("element", eid))
            elif etype == "status_time":
                self.canvas.create_text(ex, ey + int(eh/2), text="14:35", fill=color, font=("Consolas", int(4 * SCALE), "bold"), anchor="w", tags=("element", eid))
            elif etype == "pixel_sun":
                self.draw_pixel_sun(ex, ey, dot_size=4, pitch=6, color=color, elem_id=eid)
            elif etype == "pixel_sunrise":
                self.draw_pixel_sunrise(ex, ey, dot_size=4, pitch=6, color=color, elem_id=eid)
            elif etype == "dot_matrix_divider":
                line_y = ey + int(eh / 2)
                for dx in range(ex, ex + ew, 7):
                    self.canvas.create_oval(dx, line_y, dx + 4, line_y + 4, fill=color, outline="", tags=("element", eid))
            elif font_style == "dot_matrix" or etype == "matrix_text":
                self.draw_dot_matrix_text(content, ex, ey, dot_size=4, pitch=6, on_color=color, off_color="#121212", elem_id=eid)
            elif font_style == "segment7":
                self.draw_7segment_text(content, ex, ey, seg_w=15, seg_h=30, color=color, elem_id=eid)
            elif font_style == "mono":
                self.canvas.create_text(ex, ey + int(eh/2), text=content, fill=color, font=("Consolas", int(4 * SCALE), "bold"), anchor="w", tags=("element", eid))
            else:
                self.canvas.create_text(ex, ey + int(eh/2), text=content, fill=color, font=("Segoe UI", int(5 * SCALE), "bold"), anchor="w", tags=("element", eid))

            if is_selected:
                self.canvas.create_rectangle(ex - 3, ey - 3, ex + ew + 3, ey + eh + 3, outline="#38bdf8", width=2, dash=(3, 3), tags=("selected", eid))
                self.canvas.create_rectangle(ex + ew - 4, ey + eh - 4, ex + ew + 5, ey + eh + 5, fill="#38bdf8", outline="#ffffff", tags=("handle", eid))
                self.draw_floating_toolbar(elem)

        self.update_inspector()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        elements = self.get_current_elements()

        if self.selected_elem_id:
            elem = self.get_selected_element()
            if elem:
                ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
                tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
                tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

                if (tb_x + 140 <= x <= tb_x + 175) and (tb_y <= y <= tb_y + 24):
                    self.delete_selected_element(); return

                colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
                for idx, col in enumerate(colors):
                    cx = tb_x + 12 + idx * 22; cy = tb_y + 12
                    if (cx - 9 <= x <= cx + 9) and (cy - 9 <= y <= cy + 9):
                        elem["color"] = col; self.redraw_canvas(); return

        for elem in elements:
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            if (ex + ew - 5 <= x <= ex + ew + 7) and (ey + eh - 5 <= y <= ey + eh + 7):
                self.selected_elem_id = elem["id"]; self.drag_data["handle"] = "resize"
                self.drag_data["elem"] = elem; self.drag_data["x"] = x; self.drag_data["y"] = y
                self.redraw_canvas(); return

        for elem in reversed(elements):
            ex = int(elem["x"] * SCALE); ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE); eh = int(elem["h"] * SCALE)
            if (ex - 4 <= x <= ex + ew + 4) and (ey - 4 <= y <= ey + eh + 4):
                self.selected_elem_id = elem["id"]; self.drag_data["handle"] = "move"
                self.drag_data["elem"] = elem; self.drag_data["x"] = x - ex; self.drag_data["y"] = y - ey
                self.redraw_canvas(); return

        self.selected_elem_id = None; self.redraw_canvas()

    def on_canvas_drag(self, event):
        elem = self.drag_data.get("elem")
        if not elem: return

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
        self.drag_data["elem"] = None; self.drag_data["handle"] = None

    def nudge_selected_element(self, dx, dy):
        elem = self.get_selected_element()
        if elem:
            elem["x"] = max(0, min(CANVAS_WIDTH - elem["w"], elem["x"] + dx))
            elem["y"] = max(0, min(CANVAS_HEIGHT - elem["h"], elem["y"] + dy))
            self.redraw_canvas()

    def update_inspector(self):
        elem = self.get_selected_element()
        if elem:
            self.sel_name_lbl.configure(text=f"Selected: {elem['name']}", text_color="#38bdf8")
            self.entry_content.delete(0, tk.END); self.entry_content.insert(0, elem.get("content", ""))
            self.entry_x.delete(0, tk.END); self.entry_x.insert(0, str(elem["x"]))
            self.entry_y.delete(0, tk.END); self.entry_y.insert(0, str(elem["y"]))
            self.entry_w.delete(0, tk.END); self.entry_w.insert(0, str(elem["w"]))
            self.entry_h.delete(0, tk.END); self.entry_h.insert(0, str(elem["h"]))

            font_val_map = {
                "dot_matrix": "Dot Matrix LED", "segment7": "7-Segment Digital",
                "mono": "Monospace Code", "default": "Default Sans"
            }
            self.font_combo.set(font_val_map.get(elem.get("font_style", "default"), "Dot Matrix LED"))
            self.color_btn.configure(fg_color=elem.get("color", "#FFFFFF"))
        else:
            self.sel_name_lbl.configure(text="Click object to edit", text_color="#64748b")
            self.entry_content.delete(0, tk.END)
            self.entry_x.delete(0, tk.END); self.entry_y.delete(0, tk.END)
            self.entry_w.delete(0, tk.END); self.entry_h.delete(0, tk.END)

    def apply_text_content(self):
        elem = self.get_selected_element()
        if elem: elem["content"] = self.entry_content.get(); self.redraw_canvas()

    def on_font_change(self, val):
        elem = self.get_selected_element()
        if elem:
            font_key_map = {"Dot Matrix LED": "dot_matrix", "7-Segment Digital": "segment7", "Monospace Code": "mono", "Default Sans": "default"}
            elem["font_style"] = font_key_map.get(val, "default"); self.redraw_canvas()

    def apply_manual_geometry(self):
        elem = self.get_selected_element()
        if elem:
            try:
                elem["x"] = int(self.entry_x.get()); elem["y"] = int(self.entry_y.get())
                elem["w"] = int(self.entry_w.get()); elem["h"] = int(self.entry_h.get())
                self.redraw_canvas()
            except Exception: pass

    def pick_color(self):
        elem = self.get_selected_element()
        if elem:
            color = colorchooser.askcolor(title="Choose Color", color=elem.get("color", "#FFFFFF"))[1]
            if color: elem["color"] = color; self.redraw_canvas()

    def add_sub_element(self, name, etype, content, def_w, def_h, def_col, font_st):
        elements = self.get_current_elements()
        new_id = f"elem_{len(elements) + 1}"
        new_elem = {"id": new_id, "name": name, "type": etype, "content": content, "font_style": font_st, "x": 10, "y": 10, "w": def_w, "h": def_h, "color": def_col}
        elements.append(new_elem); self.selected_elem_id = new_id; self.redraw_canvas()

    def delete_selected_element(self):
        if self.selected_elem_id:
            elements = self.get_current_elements()
            self.skin_data["pages"][str(self.current_page_idx)]["elements"] = [el for el in elements if el["id"] != self.selected_elem_id]
            self.selected_elem_id = None; self.redraw_canvas()

    def get_selected_element(self):
        for elem in self.get_current_elements():
            if elem["id"] == self.selected_elem_id: return elem
        return None

    def apply_palette(self, pal_name):
        pal = COLOR_PALETTES.get(pal_name)
        if not pal: return
        self.skin_data["canvas"]["bg_color"] = pal["bg"]
        elements = self.get_current_elements()
        for idx, el in enumerate(elements):
            if idx % 3 == 0: el["color"] = pal["accent"]
            elif idx % 3 == 1: el["color"] = pal["sec"]
            else: el["color"] = pal["line"]
        self.redraw_canvas()

    def sync_to_cyd_desk(self):
        payload_str = json.dumps(self.skin_data)
        success = False

        if active_serial_conn and active_serial_conn.is_open:
            with serial_lock:
                try:
                    active_serial_conn.write(f"SKIN_JSON:{payload_str}\n".encode('utf-8'))
                    success = True
                    tk.messagebox.showinfo("⚡ Live Sync Success", "Skin successfully synced to ESP32 CYD via USB Serial!")
                except Exception: pass

        if not success and self.cached_ip:
            try:
                resp = requests.post(f"http://{self.cached_ip}/api/skin/update", json=self.skin_data, timeout=1.0)
                if resp.ok:
                    success = True
                    tk.messagebox.showinfo("⚡ Live Sync Success", f"Skin successfully synced to ESP32 CYD via WiFi ({self.cached_ip})!")
            except Exception: pass

        if not success:
            tk.messagebox.showwarning("Sync Notice", "Could not reach CYD hardware over USB or WiFi.\nSkin saved locally.")

    # ── CONTROL FUNCTIONS ─────────────────────────────────────────────
    def force_reconnect(self):
        self.last_port_scan = 0
        self.status_lbl.configure(text="● Scanning USB/WiFi ports...", text_color="#EAB308")

    def apply_theme(self, theme_key):
        self.pending_control["preset"] = theme_key
        self.status_lbl.configure(text=f"✅ Theme set: {theme_key}", text_color="#39FF14")

    def switch_page(self, page_id):
        self.active_cyd_page = page_id
        self.pending_control["page"] = page_id
        self._highlight_page_button(page_id)
        self.draw_sim_canvas_preview()
        self.status_lbl.configure(text=f"✅ Switched to Page {page_id}", text_color="#39FF14")

    def _highlight_page_button(self, page_id):
        for pid, btn_box in enumerate(self.page_btns):
            p_code, p_title, p_sub, p_col = PAGE_ITEMS[pid]
            if pid == page_id:
                btn_box.configure(fg_color="#1f2937", border_color=p_col, border_width=2)
            else:
                btn_box.configure(fg_color="#030712", border_color="#1f2937", border_width=1)

    def _sync_state_from_cyd(self, sdata):
        page_id = sdata.get("page", 0)
        if page_id != self.active_cyd_page:
            self.active_cyd_page = page_id
            self._highlight_page_button(page_id)
            self.draw_sim_canvas_preview()

        cyd_city = sdata.get("city", "")
        if cyd_city and hasattr(self, 'city_combo'):
            for eng, vn in VN_CITIES:
                if eng.lower() == cyd_city.lower():
                    self.city_combo.set(vn); break

        cur1 = sdata.get("cur1", "")
        if cur1 and hasattr(self, 'cur1_combo'):
            self.cur1_combo.set(cur1)

        cur2 = sdata.get("cur2", "")
        if cur2 and hasattr(self, 'cur2_combo'):
            self.cur2_combo.set(cur2)

    def apply_city(self):
        sel = self.city_combo.get(); eng_city = "Hanoi"
        for eng, vn in VN_CITIES:
            if vn == sel: eng_city = eng; break
        self.pending_control["city"] = eng_city
        self.status_lbl.configure(text=f"✅ Weather City set: {sel}", text_color="#39FF14")

    def apply_currencies(self):
        c1 = self.cur1_combo.get(); c2 = self.cur2_combo.get()
        self.pending_control["cur1"] = c1
        self.pending_control["cur2"] = c2
        self.status_lbl.configure(text=f"✅ FX Currencies set: {c1}/{c2}", text_color="#39FF14")

    def _update_telemetry_ui(self, c, r, d, u):
        if hasattr(self, 'lbl_cpu'):
            self.lbl_cpu.configure(text=f"{c}%")
            self.bar_cpu.set(c / 100.0)
            self.lbl_ram.configure(text=f"{r}%")
            self.bar_ram.set(r / 100.0)
            self.lbl_net_down.configure(text=f"{d} KB/s" if d < 1024 else f"{d/1024:.1f} MB/s")
            self.bar_net_down.set(min(1.0, d / 2048.0))
            self.lbl_net_up.configure(text=f"{u} KB/s" if u < 1024 else f"{u/1024:.1f} MB/s")
            self.bar_net_up.set(min(1.0, u / 1024.0))

    # ── HARDWARE METRICS STREAM LOOP (< 50ms Connection) ──────────────
    def stream_loop(self):
        global active_serial_conn
        ser = None
        while True:
            if not self.is_streaming:
                time.sleep(1); break

            now_time = time.time()

            # 1. Collect Hardware Metrics (CPU, RAM, Net, Disks)
            try:
                curr_net = psutil.net_io_counters()
                dt = now_time - self.last_time
                if dt > 0 and self.last_net is not None:
                    down_speed = int((curr_net.bytes_recv - self.last_net.bytes_recv) / dt / 1024)
                    up_speed = int((curr_net.bytes_sent - self.last_net.bytes_sent) / dt / 1024)
                else:
                    down_speed = up_speed = 0
                self.last_net = curr_net; self.last_time = now_time

                cpu_pct = int(psutil.cpu_percent(interval=None))
                ram_pct = int(psutil.virtual_memory().percent)

                # Collect Fixed Disk Drives (C:, D:, E:...)
                disks_info = []
                try:
                    for part in psutil.disk_partitions(all=False):
                        if 'fixed' in part.opts or ('cdrom' not in part.opts and part.fstype):
                            try:
                                usage = psutil.disk_usage(part.mountpoint)
                                dname = part.device.replace(":\\", "").replace(":", "").upper()
                                disks_info.append({"name": dname, "used": int(usage.percent)})
                            except Exception: pass
                except Exception: pass

                payload = {
                    "cpu": cpu_pct,
                    "ram": ram_pct,
                    "net_down": down_speed,
                    "net_up": up_speed,
                    "disks": disks_info[:4]
                }

                # MERGE PENDING USER CONTROL COMMANDS INTO TELEMETRY JSON PACKET
                if self.pending_control:
                    payload.update(self.pending_control)
                    self.pending_control = {}

                self.after(0, lambda c=cpu_pct, r=ram_pct, d=down_speed, u=up_speed:
                           self._update_telemetry_ui(c, r, d, u))
            except Exception:
                time.sleep(0.5); continue

            # 2. USB Serial Connection
            connected_usb = False
            connected_wifi = False
            ser_port = ""

            if (ser is None or not ser.is_open) and (now_time - self.last_port_scan > 1.0):
                self.last_port_scan = now_time
                target_port = self.selected_com_port

                candidate_ports = []
                if target_port != "AUTO":
                    candidate_ports.append(target_port)
                else:
                    if self.cached_com_port:
                        candidate_ports.append(self.cached_com_port)
                    ports = list(serial.tools.list_ports.comports())
                    for p in ports:
                        p_dev = str(p.device).upper()
                        p_desc = str(p.description).upper()
                        p_hwid = str(getattr(p, 'hwid', '')).upper()
                        if "BLUETOOTH" in p_desc or "BTHENUM" in p_hwid: continue
                        if ("COM" in p_dev and p_dev != "COM1") or any(k in p_desc for k in ["CH340", "CP210", "USB", "UART"]):
                            if p.device not in candidate_ports:
                                candidate_ports.append(p.device)

                for p_name in candidate_ports:
                    try:
                        s = serial.Serial()
                        s.port = p_name
                        s.baudrate = 115200
                        s.timeout = 0.05
                        s.dtr = False
                        s.rts = False
                        s.open()
                        ser = s
                        with serial_lock:
                            active_serial_conn = ser
                        self.cached_com_port = p_name
                        break
                    except Exception:
                        ser = None
                        with serial_lock:
                            active_serial_conn = None

            if ser and ser.is_open:
                try:
                    with serial_lock:
                        ser.write((json.dumps(payload) + "\n").encode('utf-8'))
                        ser.flush()

                        # Read response state from CYD if present
                        if ser.in_waiting > 0:
                            raw_lines = ser.read_all().decode('utf-8', errors='ignore').split('\n')
                            for line in raw_lines:
                                line = line.strip()
                                if line.startswith("STATE:"):
                                    try:
                                        sdata = json.loads(line[6:])
                                        self.after(0, lambda sd=sdata: self._sync_state_from_cyd(sd))
                                    except Exception: pass

                    connected_usb = True
                    ser_port = ser.port
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None
                    with serial_lock:
                        active_serial_conn = None
                    connected_usb = False

            # Fallback to WiFi HTTP if USB not connected
            if not connected_usb and self.esp32_ip:
                try:
                    resp = requests.post(f"http://{self.esp32_ip}/api/pc", json=payload, timeout=0.4)
                    if resp.ok:
                        connected_wifi = True
                except Exception: pass

            # Update status banner accurately
            if connected_usb:
                self.after(0, lambda dev=ser_port: self.status_lbl.configure(
                    text=f"🟢 Connected via USB ({dev})", text_color="#39FF14"
                ))
            elif connected_wifi:
                self.after(0, lambda ip=self.esp32_ip: self.status_lbl.configure(
                    text=f"🌐 Connected via WiFi ({ip})", text_color="#00E676"
                ))
            else:
                self.after(0, lambda: self.status_lbl.configure(
                    text="🟡 Standby Mode (Select COM Port / Check Cable)", text_color="#EAB308"
                ))

            time.sleep(1)

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Skin Layout", "*.json")])
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.skin_data, f, indent=2, ensure_ascii=False)
                tk.messagebox.showinfo("Export Success", f"Skin Layout JSON saved to:\n{path}")
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
                self.selected_elem_id = None; self.redraw_canvas()
                tk.messagebox.showinfo("Import Success", "Skin Layout JSON successfully loaded!")
            except Exception as e:
                tk.messagebox.showerror("Import Error", f"Failed to load JSON file: {e}")

def _send_control_cmd(cmd_dict, status_lbl, success_msg, err_msg):
    if app_instance:
        app_instance.pending_control.update(cmd_dict)
        if status_lbl:
            status_lbl.configure(text=success_msg, text_color="#39FF14")

if __name__ == "__main__":
    app = SmartDeskStudioProApp()
    app.mainloop()
