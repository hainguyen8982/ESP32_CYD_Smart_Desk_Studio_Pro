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
import pystray
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
app_instance = None

CANVAS_WIDTH = 320
CANVAS_HEIGHT = 240
SCALE = 2.2  # 2.2x Display scale for compact studio tab (704x528 canvas)

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

COLOR_PALETTES = {
    "Cyberpunk Neon": {"accent": "#00F5FF", "sec": "#FF00CC", "bg": "#140026", "line": "#39FF14"},
    "Nordic Slate": {"accent": "#38BDF8", "sec": "#94A3B8", "bg": "#0F172A", "line": "#10B981"},
    "Luxury Gold": {"accent": "#FFD700", "sec": "#FFF8DC", "bg": "#0B0B0E", "line": "#FFA500"},
    "Retro CRT": {"accent": "#00FF41", "sec": "#009926", "bg": "#000000", "line": "#00FF41"}
}

VN_CITIES = [
    ("Hanoi", "Hà Nội"), ("Ho Chi Minh", "TP. Hồ Chí Minh"), ("Da Nang", "Đà Nẵng"),
    ("Hai Phong", "Hải Phòng"), ("Can Tho", "Cần Thơ"), ("Nha Trang", "Nha Trang (Khánh Hòa)"),
    ("Da Lat", "Đà Lạt (Lâm Đồng)"), ("Hue", "Thừa Thiên Huế"), ("Vung Tau", "Bà Rịa - Vũng Tàu"),
    ("Quy Nhon", "Quy Nhơn (Bình Định)"), ("Buon Ma Thuot", "Buôn Ma Thuột"), ("Ha Long", "Hạ Long"),
    ("Phan Thiet", "Phan Thiết"), ("Thanh Hoa", "Thanh Hóa"), ("Vinh", "Vinh (Nghệ An)")
]

def start_udp_media_listener():
    def udp_loop():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 8080))
            sock.settimeout(1.0)
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data:
                        msg = data.decode('utf-8', errors='ignore').strip()
                        if "MEDIA_CMD:" in msg:
                            handle_media_action(msg.split("MEDIA_CMD:")[1].strip())
                except socket.timeout:
                    continue
                except Exception:
                    time.sleep(0.1)
        except Exception:
            pass

    t = threading.Thread(target=udp_loop, daemon=True)
    t.start()

def handle_media_action(action):
    if not action: return
    act = str(action).lower().strip()
    vk = None
    if act in ["play_pause", "play", "pause"]: vk = VK_MEDIA_PLAY_PAUSE
    elif act == "next": vk = VK_MEDIA_NEXT_TRACK
    elif act == "prev": vk = VK_MEDIA_PREV_TRACK
    elif act in ["vol_up", "volume_up"]: vk = VK_VOLUME_UP
    elif act in ["vol_down", "volume_down"]: vk = VK_VOLUME_DOWN
    elif act in ["mute"]: vk = VK_VOLUME_MUTE

    if vk and sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
        except Exception:
            pass

start_udp_media_listener()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SmartDeskStudioProApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("👑 Smart Desk Studio Pro — Unified Dashboard & Skin Designer")
        self.geometry("1280x860")
        self.resizable(True, True)

        global app_instance
        app_instance = self

        self.esp32_ip = "192.168.1.13"
        self.cached_ip = "192.168.1.13"
        self.cached_com_port = ""
        self.is_streaming = True
        self.active_cyd_page = 0
        self.last_net = None
        self.last_time = time.time()
        self.last_port_scan = 0

        # Skin Designer Data Structure
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

        # Start Background PC Stats Streamer Thread (< 50ms fast connection)
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

    def bind_keyboard_shortcuts(self):
        self.bind("<Delete>", lambda e: self.delete_selected_element())
        self.bind("<BackSpace>", lambda e: self.delete_selected_element())
        self.bind("<Up>", lambda e: self.nudge_selected_element(0, -1))
        self.bind("<Down>", lambda e: self.nudge_selected_element(0, 1))
        self.bind("<Left>", lambda e: self.nudge_selected_element(-1, 0))
        self.bind("<Right>", lambda e: self.nudge_selected_element(1, 0))

    def create_unified_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Header Status Bar ──────────────────────────────────────────
        hdr = ctk.CTkFrame(main_container, fg_color="#161b22", corner_radius=10, height=50)
        hdr.pack(fill="x", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            hdr, text="👑 Smart Desk Studio Pro", font=ctk.CTkFont(size=18, weight="bold"), text_color="#58a6ff"
        )
        title_lbl.pack(side="left", padx=15, pady=8)

        self.status_lbl = ctk.CTkLabel(
            hdr, text="● Searching Dashboard...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#d29922"
        )
        self.status_lbl.pack(side="right", padx=15, pady=8)

        # ── 3 Main Navigation Tabs ────────────────────────────────────
        self.tabview = ctk.CTkTabview(main_container, corner_radius=10)
        self.tabview.pack(fill="both", expand=True)

        self.tab_live = self.tabview.add("🖥️ Live Control Center")
        self.tab_designer = self.tabview.add("🎨 Skin Designer Studio")
        self.tab_settings = self.tabview.add("⚙️ System Settings")

        self.build_tab_live()
        self.build_tab_designer()
        self.build_tab_settings()

    # ── TAB 1: LIVE CONTROL CENTER (REDESIGNED ULTRA-PREMIUM UI) ──────
    def build_tab_live(self):
        container = ctk.CTkScrollableFrame(self.tab_live, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)

        # 1. Hardware Telemetry Metrics Cards
        tele_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        tele_frame.pack(fill="x", pady=(0, 8))

        t_hdr = ctk.CTkLabel(tele_frame, text="📊 Live PC Hardware Telemetry", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58a6ff")
        t_hdr.pack(anchor="w", padx=15, pady=(10, 6))

        m_grid = ctk.CTkFrame(tele_frame, fg_color="transparent")
        m_grid.pack(fill="x", padx=10, pady=(0, 10))

        # CPU Box
        cpu_box = ctk.CTkFrame(m_grid, fg_color="#0d1117", border_width=1, border_color="#30363d", corner_radius=8, width=150)
        cpu_box.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(cpu_box, text="💻 CPU LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b949e").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_cpu = ctk.CTkLabel(cpu_box, text="0%", font=ctk.CTkFont(size=22, weight="bold"), text_color="#00F5FF")
        self.lbl_cpu.pack(anchor="w", padx=10, pady=2)
        self.bar_cpu = ctk.CTkProgressBar(cpu_box, height=6, progress_color="#00F5FF", fg_color="#21262d")
        self.bar_cpu.set(0.0)
        self.bar_cpu.pack(fill="x", padx=10, pady=(0, 10))

        # RAM Box
        ram_box = ctk.CTkFrame(m_grid, fg_color="#0d1117", border_width=1, border_color="#30363d", corner_radius=8, width=150)
        ram_box.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(ram_box, text="🧠 RAM LOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b949e").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_ram = ctk.CTkLabel(ram_box, text="0%", font=ctk.CTkFont(size=22, weight="bold"), text_color="#AB47BC")
        self.lbl_ram.pack(anchor="w", padx=10, pady=2)
        self.bar_ram = ctk.CTkProgressBar(ram_box, height=6, progress_color="#AB47BC", fg_color="#21262d")
        self.bar_ram.set(0.0)
        self.bar_ram.pack(fill="x", padx=10, pady=(0, 10))

        # Net Down Box
        down_box = ctk.CTkFrame(m_grid, fg_color="#0d1117", border_width=1, border_color="#30363d", corner_radius=8, width=150)
        down_box.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(down_box, text="⬇️ NET DOWNLOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b949e").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_down = ctk.CTkLabel(down_box, text="0 KB/s", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00E676")
        self.lbl_net_down.pack(anchor="w", padx=10, pady=(4, 10))

        # Net Up Box
        up_box = ctk.CTkFrame(m_grid, fg_color="#0d1117", border_width=1, border_color="#30363d", corner_radius=8, width=150)
        up_box.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(up_box, text="⬆️ NET UPLOAD", font=ctk.CTkFont(size=10, weight="bold"), text_color="#8b949e").pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_net_up = ctk.CTkLabel(up_box, text="0 KB/s", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFA726")
        self.lbl_net_up.pack(anchor="w", padx=10, pady=(4, 10))

        for col_i in range(4):
            m_grid.columnconfigure(col_i, weight=1)

        # 2. Descriptive Page Switcher Grid (8 Buttons with Full Titles & Icons)
        p_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        p_frame.pack(fill="x", pady=6)

        p_lbl = ctk.CTkLabel(p_frame, text="🖥️ Switch Dashboard Page (Pages 0..7)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58a6ff")
        p_lbl.pack(anchor="w", padx=15, pady=(10, 6))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 10))

        self.page_btns = []
        page_titles = [
            "Page 0: 🌤️ Weather Clock",
            "Page 1: 📆 Lunar Calendar",
            "Page 2: 📈 Finance & Gold",
            "Page 3: 💻 PC Hardware",
            "Page 4: 🚀 Net & Disks",
            "Page 5: ⏳ Pomodoro Desk",
            "Page 6: 🎵 Media Remote",
            "Page 7: ⚙️ System Settings"
        ]

        for pid in range(8):
            row = pid // 4
            col = pid % 4
            btn = ctk.CTkButton(
                p_grid, text=page_titles[pid], font=ctk.CTkFont(size=12, weight="bold"),
                height=38, fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda p=pid: self.switch_page(p)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")
            self.page_btns.append(btn)

        for col_i in range(4):
            p_grid.columnconfigure(col_i, weight=1)

        # 3. Preset Theme Switcher (6 Theme Buttons with Color Swatches)
        th_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        th_frame.pack(fill="x", pady=6)

        th_lbl = ctk.CTkLabel(th_frame, text="🎨 Preset Firmware Theme Switcher (Chủ Đề Giao Diện)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58a6ff")
        th_lbl.pack(anchor="w", padx=15, pady=(10, 6))

        th_grid = ctk.CTkFrame(th_frame, fg_color="transparent")
        th_grid.pack(fill="x", padx=10, pady=(0, 10))

        preset_themes = [
            ("🌊 Ocean Dark", "ocean_dark", "#0F172A", "#38BDF8"),
            ("🟣 Cyberpunk Neon", "cyberpunk", "#140026", "#FF00CC"),
            ("🌲 Forest Slate", "forest", "#064E3B", "#10B981"),
            ("🌸 Cherry Blossom", "cherry", "#831843", "#F472B6"),
            ("☀️ Light Day", "light_day", "#F8FAFC", "#0284C7"),
            ("🟢 Retro Green", "retro_green", "#000000", "#00FF41")
        ]

        for idx, (tname, tkey, bg_col, acc_col) in enumerate(preset_themes):
            row = idx // 3
            col = idx % 3
            t_btn = ctk.CTkButton(
                th_grid, text=f"✨ {tname}", font=ctk.CTkFont(size=12, weight="bold"),
                height=36, fg_color="#21262d", hover_color="#30363d", text_color=acc_col,
                command=lambda k=tkey: self.apply_theme(k)
            )
            t_btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

        for col_i in range(3):
            th_grid.columnconfigure(col_i, weight=1)

        # 4. Weather Location & Foreign Exchange Settings
        w_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        w_frame.pack(fill="x", pady=6)

        w_lbl = ctk.CTkLabel(w_frame, text="🌤️ Weather Location & 💱 Foreign Exchange Currencies", font=ctk.CTkFont(size=14, weight="bold"), text_color="#58a6ff")
        w_lbl.pack(anchor="w", padx=15, pady=(10, 6))

        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 10))

        city_names = [c[1] for c in VN_CITIES]
        self.city_combo = ctk.CTkOptionMenu(w_inner, values=city_names, width=220)
        self.city_combo.set("Hà Nội")
        self.city_combo.pack(side="left", padx=(0, 10))

        set_city_btn = ctk.CTkButton(w_inner, text="Set City", width=90, command=self.apply_city)
        set_city_btn.pack(side="left", padx=(0, 20))

        currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW"]
        self.cur1_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=100)
        self.cur1_combo.set("USD")
        self.cur1_combo.pack(side="left", padx=(0, 5))

        self.cur2_combo = ctk.CTkOptionMenu(w_inner, values=currencies, width=100)
        self.cur2_combo.set("EUR")
        self.cur2_combo.pack(side="left", padx=(0, 10))

        set_cur_btn = ctk.CTkButton(w_inner, text="Set Currencies", width=110, command=self.apply_currencies)
        set_cur_btn.pack(side="left")

    # ── TAB 2: SKIN DESIGNER STUDIO ───────────────────────────────────
    def build_tab_designer(self):
        body = ctk.CTkFrame(self.tab_designer, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=5, pady=5)

        # Top Palette Swatches & Sync Bar
        pal_bar = ctk.CTkFrame(body, fg_color="#161b22", corner_radius=8, height=45)
        pal_bar.pack(fill="x", pady=(0, 8))

        p_lbl = ctk.CTkLabel(pal_bar, text="🎨 1-Click Theme:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38bdf8")
        p_lbl.pack(side="left", padx=10, pady=6)

        for pal_name in COLOR_PALETTES:
            p_btn = ctk.CTkButton(
                pal_bar, text=f"✨ {pal_name}", width=110, height=24,
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda name=pal_name: self.apply_palette(name)
            )
            p_btn.pack(side="left", padx=3, pady=6)

        sync_btn = ctk.CTkButton(
            pal_bar, text="⚡ 1-Click Sync to Desk", width=160, fg_color="#238636", hover_color="#2ea043",
            font=ctk.CTkFont(weight="bold"), command=self.sync_to_cyd_desk
        )
        sync_btn.pack(side="right", padx=10, pady=6)

        # 3 Grid Columns
        grid_frame = ctk.CTkFrame(body, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)

        # Left Toolbox
        left_box = ctk.CTkFrame(grid_frame, fg_color="#161b22", corner_radius=10, width=220)
        left_box.pack(side="left", fill="y", padx=(0, 8))

        w_lbl = ctk.CTkLabel(left_box, text="➕ Add Sub-Elements", font=ctk.CTkFont(size=12, weight="bold"))
        w_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        for name, etype, content, def_w, def_h, def_col, font_st in ELEMENT_PRESETS:
            btn = ctk.CTkButton(
                left_box, text=f"+ {name}", anchor="w",
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda n=name, t=etype, c=content, w=def_w, h=def_h, col=def_col, f=font_st: self.add_sub_element(n, t, c, w, h, col, f)
            )
            btn.pack(fill="x", padx=8, pady=2)

        # Center Interactive Canvas
        center_box = ctk.CTkFrame(grid_frame, fg_color="#090d16", corner_radius=10)
        center_box.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(
            center_box, width=int(CANVAS_WIDTH * SCALE), height=int(CANVAS_HEIGHT * SCALE),
            bg="#000000", highlightthickness=2, highlightbackground="#30363d"
        )
        self.canvas.pack(padx=10, pady=10)

        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # Right Sub-Element Inspector
        right_box = ctk.CTkFrame(grid_frame, fg_color="#161b22", corner_radius=10, width=250)
        right_box.pack(side="right", fill="y", padx=(8, 0))

        p_lbl = ctk.CTkLabel(right_box, text="⚙️ Sub-Element Inspector", font=ctk.CTkFont(size=13, weight="bold"))
        p_lbl.pack(anchor="w", padx=12, pady=(10, 5))

        self.sel_name_lbl = ctk.CTkLabel(right_box, text="Click object to edit", text_color="#8b949e", font=ctk.CTkFont(weight="bold"))
        self.sel_name_lbl.pack(anchor="w", padx=12, pady=(0, 5))

        c_lbl = ctk.CTkLabel(right_box, text="✏️ Text Content:", font=ctk.CTkFont(size=11, weight="bold"))
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

        f_lbl = ctk.CTkLabel(right_box, text="🔤 Font Style:", font=ctk.CTkFont(size=11, weight="bold"))
        f_lbl.pack(anchor="w", padx=12, pady=(3, 1))

        self.font_combo = ctk.CTkOptionMenu(
            right_box, values=["Dot Matrix LED", "7-Segment Digital", "Monospace Code", "Default Sans"],
            command=self.on_font_change, width=220
        )
        self.font_combo.set("Dot Matrix LED")
        self.font_combo.pack(padx=10, pady=2)

        self.color_btn = ctk.CTkButton(right_box, text="🎨 Element Color", width=220, fg_color="#21262d", command=self.pick_color)
        self.color_btn.pack(padx=10, pady=4)

        self.del_btn = ctk.CTkButton(
            right_box, text="🗑️ Delete Sub-Element", width=220, fg_color="#da3633", hover_color="#f85149",
            command=self.delete_selected_element
        )
        self.del_btn.pack(side="bottom", padx=10, pady=12)

    # ── TAB 3: SYSTEM SETTINGS ────────────────────────────────────────
    def build_tab_settings(self):
        container = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        s_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        s_frame.pack(fill="x", pady=5)

        s_title = ctk.CTkLabel(s_frame, text="⚙️ App & Connection Settings", font=ctk.CTkFont(size=14, weight="bold"))
        s_title.pack(anchor="w", padx=12, pady=(10, 5))

        ip_inner = ctk.CTkFrame(s_frame, fg_color="transparent")
        ip_inner.pack(fill="x", padx=12, pady=5)

        ctk.CTkLabel(ip_inner, text="CYD WiFi IP Address:").pack(side="left", padx=(0, 10))
        self.ip_entry = ctk.CTkEntry(ip_inner, width=180)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left")

        # Auto-Start on Windows Boot Checkbox
        self.autostart_var = ctk.BooleanVar(value=True)
        autostart_chk = ctk.CTkCheckBox(s_frame, text="Run Smart Desk Studio Pro on Windows Startup", variable=self.autostart_var)
        autostart_chk.pack(anchor="w", padx=12, pady=8)

    # ── CANVAS DRAWING & DESIGNER METHODS ─────────────────────────────
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
            t = 3

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

    def draw_floating_toolbar(self, elem):
        ex = int(elem["x"] * SCALE)
        ey = int(elem["y"] * SCALE)
        tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
        tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

        self.canvas.create_rectangle(
            tb_x, tb_y, tb_x + 180, tb_y + 24,
            fill="#161b22", outline="#38bdf8", width=1, tags="floating_tb"
        )
        colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
        for idx, col in enumerate(colors):
            cx = tb_x + 12 + idx * 22
            cy = tb_y + 12
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

            if etype == "wifi_signal":
                for b in range(4):
                    bx = ex + b * 4; bh = 3 + b * 2; by = ey + 10 - bh
                    self.canvas.create_oval(bx, by, bx + 3, by + 3, fill=color, outline="", tags=("element", eid))
                self.canvas.create_text(ex + 20, ey + int(eh/2), text="-54dBm", fill=color, font=("Consolas", int(3.5 * SCALE)), anchor="w", tags=("element", eid))
            elif etype == "status_time":
                self.canvas.create_text(ex, ey + int(eh/2), text="⏰ 14:35", fill=color, font=("Consolas", int(4 * SCALE), "bold"), anchor="w", tags=("element", eid))
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
                self.canvas.create_rectangle(
                    ex - 3, ey - 3, ex + ew + 3, ey + eh + 3,
                    outline="#58a6ff", width=2, dash=(3, 3), tags=("selected", eid)
                )
                self.canvas.create_rectangle(
                    ex + ew - 4, ey + eh - 4, ex + ew + 5, ey + eh + 5,
                    fill="#58a6ff", outline="#ffffff", tags=("handle", eid)
                )
                self.draw_floating_toolbar(elem)

        self.update_inspector()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        elements = self.get_current_elements()

        if self.selected_elem_id:
            elem = self.get_selected_element()
            if elem:
                ex = int(elem["x"] * SCALE)
                ey = int(elem["y"] * SCALE)
                tb_x = min(int(CANVAS_WIDTH * SCALE) - 180, max(10, ex))
                tb_y = max(10, ey - 30) if ey > 32 else ey + int(elem["h"] * SCALE) + 6

                if (tb_x + 140 <= x <= tb_x + 175) and (tb_y <= y <= tb_y + 24):
                    self.delete_selected_element()
                    return

                colors = ["#FFFFFF", "#FF3333", "#00F5FF", "#FFD700", "#00E676"]
                for idx, col in enumerate(colors):
                    cx = tb_x + 12 + idx * 22
                    cy = tb_y + 12
                    if (cx - 9 <= x <= cx + 9) and (cy - 9 <= y <= cy + 9):
                        elem["color"] = col
                        self.redraw_canvas()
                        return

        for elem in elements:
            ex = int(elem["x"] * SCALE)
            ey = int(elem["y"] * SCALE)
            ew = int(elem["w"] * SCALE)
            eh = int(elem["h"] * SCALE)

            if (ex + ew - 5 <= x <= ex + ew + 7) and (ey + eh - 5 <= y <= ey + eh + 7):
                self.selected_elem_id = elem["id"]
                self.drag_data["handle"] = "resize"
                self.drag_data["elem"] = elem
                self.drag_data["x"] = x
                self.drag_data["y"] = y
                self.redraw_canvas()
                return

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
            self.sel_name_lbl.configure(text="Click object to edit", text_color="#8b949e")
            self.entry_content.delete(0, tk.END)
            self.entry_x.delete(0, tk.END); self.entry_y.delete(0, tk.END)
            self.entry_w.delete(0, tk.END); self.entry_h.delete(0, tk.END)

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
            color = colorchooser.askcolor(title="Choose Color", color=elem.get("color", "#FFFFFF"))[1]
            if color:
                elem["color"] = color
                self.redraw_canvas()

    def add_sub_element(self, name, etype, content, def_w, def_h, def_col, font_st):
        elements = self.get_current_elements()
        new_id = f"elem_{len(elements) + 1}"
        new_elem = {
            "id": new_id, "name": name, "type": etype, "content": content,
            "font_style": font_st, "x": 10, "y": 10, "w": def_w, "h": def_h, "color": def_col
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
            try:
                active_serial_conn.write(f"SKIN_JSON:{payload_str}\n".encode('utf-8'))
                success = True
                tk.messagebox.showinfo("⚡ Live Sync Success", "Skin successfully synced to ESP32 CYD via USB Serial!")
            except Exception:
                pass

        if not success and self.cached_ip:
            try:
                resp = requests.post(f"http://{self.cached_ip}/api/skin/update", json=self.skin_data, timeout=1.0)
                if resp.ok:
                    success = True
                    tk.messagebox.showinfo("⚡ Live Sync Success", f"Skin successfully synced to ESP32 CYD via WiFi ({self.cached_ip})!")
            except Exception:
                pass

        if not success:
            tk.messagebox.showwarning("Sync Notice", "Could not reach CYD hardware over USB or WiFi.\nSkin saved locally.")

    # ── CONTROL FUNCTIONS ─────────────────────────────────────────────
    def apply_theme(self, theme_key):
        _send_control_cmd({"preset": theme_key}, self.status_lbl, f"✅ Theme: {theme_key}", "❌ Theme error")

    def switch_page(self, page_id):
        self.active_cyd_page = page_id
        for pid, btn in enumerate(self.page_btns):
            if pid == page_id:
                btn.configure(fg_color="#1f6feb", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="#21262d", text_color="#c9d1d9")
        _send_control_cmd({"page": page_id}, self.status_lbl, f"✅ Switched to Page {page_id}", "❌ Switch error")

    def apply_city(self):
        sel = self.city_combo.get()
        eng_city = "Hanoi"
        for eng, vn in VN_CITIES:
            if vn == sel:
                eng_city = eng; break
        _send_control_cmd({"city": eng_city}, self.status_lbl, f"✅ City: {sel}", "❌ Error setting city")

    def apply_currencies(self):
        c1 = self.cur1_combo.get()
        c2 = self.cur2_combo.get()
        _send_control_cmd({"cur1": c1, "cur2": c2}, self.status_lbl, f"✅ Currencies: {c1}/{c2}", "❌ Currency error")

    def _update_telemetry_ui(self, c, r, d, u):
        if hasattr(self, 'lbl_cpu'):
            self.lbl_cpu.configure(text=f"{c}%")
            self.bar_cpu.set(c / 100.0)
            self.lbl_ram.configure(text=f"{r}%")
            self.bar_ram.set(r / 100.0)
            self.lbl_net_down.configure(text=f"{d} KB/s" if d < 1024 else f"{d/1024:.1f} MB/s")
            self.lbl_net_up.configure(text=f"{u} KB/s" if u < 1024 else f"{u/1024:.1f} MB/s")

    # ── HARDWARE METRICS STREAM LOOP (< 50ms Connection) ──────────────
    def stream_loop(self):
        ser = None
        while True:
            if not self.is_streaming:
                time.sleep(1); continue

            now_time = time.time()

            # 1. Collect Hardware Metrics
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

                payload = {"cpu": cpu_pct, "ram": ram_pct, "net_down": down_speed, "net_up": up_speed}
                self.after(0, lambda c=cpu_pct, r=ram_pct, d=down_speed, u=up_speed:
                           self._update_telemetry_ui(c, r, d, u))
            except Exception:
                time.sleep(0.5); continue

            # 2. USB Serial Connection (Instant Bluetooth Filtering & Cache First)
            if (ser is None or not ser.is_open) and (now_time - self.last_port_scan > 1.5):
                self.last_port_scan = now_time
                try:
                    if self.cached_com_port:
                        try:
                            s = serial.Serial(self.cached_com_port, 115200, timeout=0.05, dtr=False, rts=False)
                            ser = s; global active_serial_conn; active_serial_conn = ser
                        except Exception: self.cached_com_port = ""

                    if ser is None or not ser.is_open:
                        ports = list(serial.tools.list_ports.comports())
                        for p in ports:
                            p_dev = str(p.device).upper()
                            p_desc = str(p.description).upper()
                            p_hwid = str(getattr(p, 'hwid', '')).upper()

                            if "BLUETOOTH" in p_desc or "BTHENUM" in p_hwid: continue

                            if ("COM" in p_dev and p_dev != "COM1") or any(k in p_desc for k in ["CH340", "CP210", "USB", "UART"]):
                                try:
                                    s = serial.Serial(p.device, 115200, timeout=0.05, dtr=False, rts=False)
                                    ser = s; active_serial_conn = ser
                                    self.cached_com_port = p.device
                                    self.after(0, lambda dev=p.device: self.status_lbl.configure(text=f"🟢 Connected USB ({dev})", text_color="#39FF14"))
                                    break
                                except Exception: pass
                except Exception: ser = None

            if ser and ser.is_open:
                try:
                    ser.write((json.dumps(payload) + "\n").encode('utf-8'))
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None

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
                self.selected_elem_id = None
                self.redraw_canvas()
                tk.messagebox.showinfo("Import Success", "Skin Layout JSON successfully loaded!")
            except Exception as e:
                tk.messagebox.showerror("Import Error", f"Failed to load JSON file: {e}")

def _send_control_cmd(cmd_dict, status_lbl, success_msg, err_msg):
    def _thread_task():
        global active_serial_conn
        sent_usb = False
        if active_serial_conn and active_serial_conn.is_open:
            try:
                active_serial_conn.write((json.dumps(cmd_dict) + "\n").encode('utf-8'))
                sent_usb = True
            except Exception: pass
        if sent_usb and status_lbl:
            status_lbl.configure(text=success_msg, text_color="#39FF14")

    threading.Thread(target=_thread_task, daemon=True).start()

if __name__ == "__main__":
    app = SmartDeskStudioProApp()
    app.mainloop()
