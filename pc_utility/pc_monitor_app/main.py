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
import customtkinter as ctk
from PIL import Image, ImageDraw
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

def start_udp_media_listener():
    def udp_loop():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", 8080))
            sock.settimeout(1.0)
            print("[*] High-Speed UDP Media Listener Started (Port 8080 - 0ms Latency)")
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    if data:
                        msg = data.decode('utf-8', errors='ignore').strip()
                        if "MEDIA_CMD:" in msg:
                            act = msg.split("MEDIA_CMD:")[1].strip()
                            handle_media_action(act)
                except socket.timeout:
                    continue
                except Exception:
                    time.sleep(0.1)
        except Exception as e:
            print(f"[UDP Listener Notice]: {e}")

    t = threading.Thread(target=udp_loop, daemon=True)
    t.start()

def start_fast_serial_listener():
    def serial_loop():
        global active_serial_conn
        print("[*] High-Speed USB Serial Listener Started (0ms Latency)")
        while True:
            try:
                if active_serial_conn and active_serial_conn.is_open and active_serial_conn.in_waiting:
                    line = active_serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if "MEDIA_CMD:" in line:
                        act = line.split("MEDIA_CMD:")[1].strip()
                        handle_media_action(act)
                else:
                    time.sleep(0.005)
            except Exception:
                time.sleep(0.05)

    t = threading.Thread(target=serial_loop, daemon=True)
    t.start()

# Launch high-speed background listeners on module load
start_udp_media_listener()
start_fast_serial_listener()

def background_skip_youtube_ad():
    """Background YouTube Ad Skipper — MULTI-PHASE 100% Skip Sequence!"""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        
        # 1. Global Media Next Track (0xB0)
        user32.keybd_event(0xB0, 0, 0, 0)
        user32.keybd_event(0xB0, 0, 2, 0)
        time.sleep(0.03)

        # 2. Shift + N (YouTube Native Shortcut for Next / Skip Ad)
        user32.keybd_event(0x10, 0, 0, 0) # Shift down
        user32.keybd_event(0x4E, 0, 0, 0) # N down
        user32.keybd_event(0x4E, 0, 2, 0) # N up
        user32.keybd_event(0x10, 0, 2, 0) # Shift up
        time.sleep(0.03)

        # 3. 5x Right Arrow (0x27) (Fast forward 25s for unskippable ads)
        for _ in range(5):
            user32.keybd_event(0x27, 0, 0, 0)
            user32.keybd_event(0x27, 0, 2, 0)
            time.sleep(0.015)
            
        print("[Media Remote]: Executed Multi-phase YouTube Ad Skip Sequence!")
    except Exception as e:
        print(f"[Skip Ad Error]: {e}")

last_media_time = 0.0
# app_instance is declared in the _send_control_cmd section below

def trigger_instant_media_push():
    def _push():
        time.sleep(0.35)
        if app_instance:
            app_instance.send_instant_telemetry()
    threading.Thread(target=_push, daemon=True).start()

def handle_media_action(action):
    global last_media_time
    if not action:
        return
    now = time.time()
    if now - last_media_time < 0.35:
        return  # Ignore duplicate trigger within 350ms!
    
    act = str(action).lower().strip()
    vk = None
    if act in ["play_pause", "play", "pause"]:
        vk = VK_MEDIA_PLAY_PAUSE
    elif act == "next":
        vk = VK_MEDIA_NEXT_TRACK
    elif act == "prev":
        vk = VK_MEDIA_PREV_TRACK
    elif act in ["vol_up", "volume_up"]:
        vk = VK_VOLUME_UP
    elif act in ["vol_down", "volume_down"]:
        vk = VK_VOLUME_DOWN
    elif act in ["mute"]:
        vk = VK_VOLUME_MUTE
    elif act == "skip_ad":
        threading.Thread(target=background_skip_youtube_ad, daemon=True).start()
        last_media_time = now
        trigger_instant_media_push()
        return

    if vk and sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(vk, 0, 0, 0)
            user32.keybd_event(vk, 0, 2, 0)
            print(f"[Media Remote]: Executed VK Action (0x{vk:02X}) for '{act}'")
        except Exception as e:
            print(f"[Media Remote Error]: {e}")
    last_media_time = now
    trigger_instant_media_push()

# Set CustomTkinter theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

VN_CITIES = [
    ("Hanoi", "Hà Nội"),
    ("Ho Chi Minh", "TP. Hồ Chí Minh"),
    ("Da Nang", "Đà Nẵng"),
    ("Hai Phong", "Hải Phòng"),
    ("Can Tho", "Cần Thơ"),
    ("Nha Trang", "Nha Trang (Khánh Hòa)"),
    ("Da Lat", "Đà Lạt (Lâm Đồng)"),
    ("Hue", "Thừa Thiên Huế"),
    ("Vung Tau", "Bà Rịa - Vũng Tàu"),
    ("Quy Nhon", "Quy Nhơn (Bình Định)"),
    ("Buon Ma Thuot", "Buôn Ma Thuột"),
    ("Ha Long", "Hạ Long (Quảng Ninh)"),
    ("Phan Thiet", "Phan Thiết"),
    ("Thanh Hoa", "Thanh Hóa"),
    ("Vinh", "Vinh (Nghệ An)"),
    ("Phu Quoc", "Đảo Phú Quốc"),
    ("Rach Gia", "Rạch Giá (Kiên Giang)"),
    ("Ca Mau", "Cà Mau")
]

THEMES = [
    ("Ocean Dark", "ocean_dark"),
    ("Cyberpunk", "cyberpunk"),
    ("Forest", "forest"),
    ("Cherry", "cherry"),
    ("Light Day", "light_day"),
    ("Retro Green", "retro_green")
]

# Global reusable HTTP Session with connection pooling & fast timeouts
http_stream_session = requests.Session()
app_instance = None

def _send_control_cmd(cmd_json, success_lbl=None, success_msg="", err_msg=""):
    # 1. Send via USB Serial FIRST if connected & open
    global active_serial_conn
    sent_usb = False
    if active_serial_conn and active_serial_conn.is_open:
        try:
            active_serial_conn.write((json.dumps(cmd_json) + "\n").encode('utf-8'))
            sent_usb = True
            if success_lbl and success_msg:
                success_lbl.configure(text=success_msg, text_color="#2ea043")
        except Exception as e:
            sent_usb = False

    # 2. If USB Serial succeeded, return immediately! (Do NOT fire HTTP to avoid false error overwrites)
    if sent_usb:
        return

    # 3. Otherwise, if IP is configured, send via non-blocking standalone HTTP in background thread
    global app_instance
    ip = ""
    if app_instance:
        try:
            ip = app_instance.ip_entry.get().strip()
        except Exception:
            pass
        if not ip:
            ip = app_instance.cached_ip

    if ip:
        def _http_worker():
            try:
                if "page" in cmd_json:
                    resp = requests.get(f"http://{ip}/api/page?id={cmd_json['page']}", timeout=1.5)
                elif "preset" in cmd_json:
                    resp = requests.get(f"http://{ip}/api/theme?preset={cmd_json['preset']}", timeout=1.5)
                elif "city" in cmd_json:
                    resp = requests.post(f"http://{ip}/api/weather/city", json={"city": cmd_json["city"]}, timeout=1.5)
                elif "cur1" in cmd_json or "cur2" in cmd_json:
                    resp = requests.get(f"http://{ip}/api/exchange?cur1={cmd_json.get('cur1','')}&cur2={cmd_json.get('cur2','')}", timeout=1.5)
                else:
                    resp = None

                if resp and resp.ok:
                    if success_lbl and success_msg:
                        success_lbl.configure(text=success_msg, text_color="#2ea043")
                else:
                    if success_lbl and err_msg:
                        success_lbl.configure(text=err_msg, text_color="#f85149")
            except Exception:
                if success_lbl and err_msg:
                    success_lbl.configure(text=err_msg, text_color="#f85149")

        threading.Thread(target=_http_worker, daemon=True).start()
    else:
        if success_lbl and err_msg:
            success_lbl.configure(text="❌ Not connected", text_color="#f85149")

class GPUMonitor:
    """Utility class to read real GPU and VRAM metrics on Windows using NVML or native PDH counters."""
    def __init__(self):
        self.use_nvml = False
        self.q_gpu = None
        self.q_vram = None
        self._init_gpu()

    def _init_gpu(self):
        # 1. Try NVML (Nvidia GPUs)
        try:
            import pynvml
            pynvml.nvmlInit()
            self.pynvml = pynvml
            self.use_nvml = True
            return
        except Exception:
            pass

        # 2. Fallback to Windows PDH (Intel UHD / AMD Radeon / Nvidia / Integrated & Dedicated)
        try:
            import ctypes
            self.ctypes = ctypes
            self.pdh = ctypes.windll.pdh
            
            self.q_gpu = ctypes.c_void_p()
            self.c_gpu = ctypes.c_void_p()
            if self.pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.q_gpu)) == 0:
                self.pdh.PdhAddEnglishCounterW(self.q_gpu, r'\GPU Engine(*engtype_3D)\Utilization Percentage', 0, ctypes.byref(self.c_gpu))
                self.pdh.PdhCollectQueryData(self.q_gpu)
                
            self.q_vram = ctypes.c_void_p()
            self.c_vram = ctypes.c_void_p()
            if self.pdh.PdhOpenQueryW(None, 0, ctypes.byref(self.q_vram)) == 0:
                self.pdh.PdhAddEnglishCounterW(self.q_vram, r'\GPU Process Memory(*)\Local Usage', 0, ctypes.byref(self.c_vram))
                self.pdh.PdhCollectQueryData(self.q_vram)
        except Exception:
            pass

    def get_metrics(self):
        gpu_pct = 0
        vram_pct = 0

        if self.use_nvml:
            try:
                handle = self.pynvml.nvmlDeviceGetHandleByIndex(0)
                util = self.pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_pct = int(util.gpu)
                vram_pct = int((mem.used / mem.total) * 100)
                return gpu_pct, vram_pct
            except Exception:
                pass

        if self.q_gpu and hasattr(self, 'ctypes'):
            try:
                import struct
                # Collect GPU 3D utilization
                self.pdh.PdhCollectQueryData(self.q_gpu)
                buf_size = self.ctypes.c_ulong(0)
                item_cnt = self.ctypes.c_ulong(0)
                self.pdh.PdhGetFormattedCounterArrayW(self.c_gpu, 0x00000200, self.ctypes.byref(buf_size), self.ctypes.byref(item_cnt), None)
                if buf_size.value > 0:
                    buf = self.ctypes.create_string_buffer(buf_size.value)
                    self.pdh.PdhGetFormattedCounterArrayW(self.c_gpu, 0x00000200, self.ctypes.byref(buf_size), self.ctypes.byref(item_cnt), buf)
                    raw_bytes = buf.raw
                    total_val = 0.0
                    for i in range(item_cnt.value):
                        offset = i * 24
                        status = int.from_bytes(raw_bytes[offset+8:offset+12], 'little')
                        if status == 0:
                            val = struct.unpack_from('d', raw_bytes, offset+16)[0]
                            total_val += val
                    gpu_pct = int(round(min(100.0, total_val)))

                # Collect VRAM Memory Usage
                self.pdh.PdhCollectQueryData(self.q_vram)
                buf_size = self.ctypes.c_ulong(0)
                item_cnt = self.ctypes.c_ulong(0)
                self.pdh.PdhGetFormattedCounterArrayW(self.c_vram, 0x00000200, self.ctypes.byref(buf_size), self.ctypes.byref(item_cnt), None)
                if buf_size.value > 0:
                    buf = self.ctypes.create_string_buffer(buf_size.value)
                    self.pdh.PdhGetFormattedCounterArrayW(self.c_vram, 0x00000200, self.ctypes.byref(buf_size), self.ctypes.byref(item_cnt), buf)
                    raw_bytes = buf.raw
                    total_vram_bytes = 0.0
                    for i in range(item_cnt.value):
                        offset = i * 24
                        status = int.from_bytes(raw_bytes[offset+8:offset+12], 'little')
                        if status == 0:
                            val = struct.unpack_from('d', raw_bytes, offset+16)[0]
                            total_vram_bytes += val
                    
                    sys_ram = psutil.virtual_memory().total
                    max_vram = sys_ram * 0.5  # Shared VRAM limit is typically half of total RAM
                    vram_pct = int(round(min(100.0, (total_vram_bytes / max_vram) * 100)))
            except Exception:
                pass

        return gpu_pct, vram_pct


def check_windows_media_playing():
    try:
        import asyncio
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status
        
        async def _get():
            mgr = await Manager.request_async()
            sess = mgr.get_current_session()
            if sess:
                info = sess.get_playback_info()
                is_playing = (info.playback_status == Status.PLAYING)
                props = await sess.try_get_media_properties_async()
                title = remove_vietnamese_accents(props.title) if props else ""
                artist = remove_vietnamese_accents(props.artist) if props else ""
                return is_playing, title, artist
            return False, "", ""
        
        return asyncio.run(_get())
    except Exception:
        return False, "", ""


class CYDMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        global app_instance
        app_instance = self

        self.title("ESP32 CYD Desk Dashboard Studio")
        self.geometry("580x950")
        self.resizable(True, True)

        self.esp32_ip = "192.168.1.13"
        self.cached_ip = self.esp32_ip
        self.is_streaming = True
        self.tray_icon = None
        self.active_cyd_page = 0

        # Network speed & GPU tracking
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()
        self.gpu_mon = GPUMonitor()

        # Main Scrollable Container for 100% Overflow Prevention
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.pack(fill="both", expand=True, padx=5, pady=5)

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Clear debug log on each startup
        try:
            open("debug.log", "w").close()
        except Exception:
            pass

        # Start background hardware metrics streaming thread
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

        # Poll & sync IP from entry box every 2s on main thread
        self._sync_ip_loop()

    def send_instant_telemetry(self):
        try:
            is_playing, media_title, media_artist = check_windows_media_playing()
            cpu_pct = int(psutil.cpu_percent(interval=None))
            ram_pct = int(psutil.virtual_memory().percent)
            gpu_pct, vram_pct = self.gpu_mon.get_metrics()
            
            payload = {
                "cpu": cpu_pct, "ram": ram_pct, "gpu": gpu_pct, "vram": vram_pct,
                "net_down": 0, "net_up": 0,
                "isMediaPlaying": is_playing,
                "mediaTitle": media_title,
                "mediaArtist": media_artist
            }
            # 1. Instant Push over USB Serial if connected
            global active_serial_conn
            if active_serial_conn and active_serial_conn.is_open:
                try:
                    active_serial_conn.write((json.dumps(payload) + "\n").encode('utf-8'))
                except Exception:
                    pass

            # 2. Instant Push over WiFi HTTP
            ip = self.cached_ip
            if ip:
                try:
                    requests.post(f"http://{ip}/api/pc", json=payload, timeout=1.0)
                except Exception:
                    pass
        except Exception:
            pass

    def create_widgets(self):
        container = self.scroll_container

        # ── Header Frame ──────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        hdr_frame.pack(fill="x", padx=10, pady=(10, 5))

        title_lbl = ctk.CTkLabel(
            hdr_frame, text="💻 ESP32 CYD Smart Dashboard Studio",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#58a6ff"
        )
        title_lbl.pack(pady=10)

        # ── Connection Settings ───────────────────────────────────────
        conn_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        conn_frame.pack(fill="x", padx=10, pady=4)

        ip_lbl = ctk.CTkLabel(conn_frame, text="ESP32 IP Address:", font=ctk.CTkFont(size=13))
        ip_lbl.pack(side="left", padx=12, pady=10)

        self.ip_entry = ctk.CTkEntry(conn_frame, width=140)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left", padx=5, pady=10)

        self.status_lbl = ctk.CTkLabel(
            conn_frame, text="● Searching for CYD...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#d29922"
        )
        self.status_lbl.pack(side="right", padx=15, pady=10)

        # ── Weather Location Section ──────────────────────────────────
        w_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        w_frame.pack(fill="x", padx=10, pady=4)

        w_title = ctk.CTkLabel(w_frame, text="🌤️ Weather Location", font=ctk.CTkFont(size=14, weight="bold"))
        w_title.pack(anchor="w", padx=12, pady=(8, 4))

        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 8))

        city_names = [c[1] for c in VN_CITIES]
        self.city_combo = ctk.CTkOptionMenu(w_inner, values=city_names, width=280)
        self.city_combo.set("Hà Nội")
        self.city_combo.pack(side="left", padx=(0, 10))

        set_city_btn = ctk.CTkButton(w_inner, text="Set City", width=100, command=self.apply_city)
        set_city_btn.pack(side="left")

        # ── Foreign Exchange Rates Section ─────────────────────────────
        ex_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        ex_frame.pack(fill="x", padx=10, pady=4)

        ex_title = ctk.CTkLabel(ex_frame, text="💱 Foreign Exchange Rates (Chọn 2 Tỷ Giá)", font=ctk.CTkFont(size=14, weight="bold"))
        ex_title.pack(anchor="w", padx=12, pady=(8, 4))

        ex_inner = ctk.CTkFrame(ex_frame, fg_color="transparent")
        ex_inner.pack(fill="x", padx=12, pady=(0, 8))

        currencies = ["USD", "EUR", "JPY", "GBP", "AUD", "SGD", "CNY", "KRW", "CAD"]

        self.cur1_combo = ctk.CTkOptionMenu(ex_inner, values=currencies, width=130)
        self.cur1_combo.set("USD")
        self.cur1_combo.pack(side="left", padx=(0, 10))

        self.cur2_combo = ctk.CTkOptionMenu(ex_inner, values=currencies, width=130)
        self.cur2_combo.set("EUR")
        self.cur2_combo.pack(side="left", padx=(0, 10))

        set_ex_btn = ctk.CTkButton(ex_inner, text="Set Currencies", width=110, command=self.apply_currencies)
        set_ex_btn.pack(side="left")

        self.page_buttons = {}
        self.theme_buttons = {}
        self.active_page_id = -1
        self.active_theme_key = ""

        # ── Theme Presets Section ─────────────────────────────────────
        t_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        t_frame.pack(fill="x", padx=10, pady=4)

        t_title = ctk.CTkLabel(t_frame, text="🎨 Theme Presets", font=ctk.CTkFont(size=14, weight="bold"))
        t_title.pack(anchor="w", padx=12, pady=(8, 4))

        t_grid = ctk.CTkFrame(t_frame, fg_color="transparent")
        t_grid.pack(fill="x", padx=10, pady=(0, 8))

        for idx, (name, key) in enumerate(THEMES):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                t_grid, text=name, width=155, height=30,
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda k=key: self.apply_theme(k)
            )
            btn.grid(row=r, column=c, padx=5, pady=4)
            self.theme_buttons[key] = btn

        # ── Remote Page Switcher ──────────────────────────────────────
        p_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        p_frame.pack(fill="x", padx=10, pady=4)

        p_title = ctk.CTkLabel(p_frame, text="📱 Remote Page Switcher", font=ctk.CTkFont(size=14, weight="bold"))
        p_title.pack(anchor="w", padx=12, pady=(8, 4))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 8))

        pages = [
            ("0: Weather Clock", 0), ("1: Lunar Calendar", 1), ("2: Gold & Finance", 2),
            ("3: PC Monitor", 3), ("4: PC Net & Storage", 4), ("5: Desk Utilities", 5),
            ("6: Media Control", 6), ("7: Settings", 7)
        ]

        for idx, (p_name, p_id) in enumerate(pages):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                p_grid, text=p_name, width=155, height=30,
                fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9",
                command=lambda pid=p_id: self.switch_page(pid)
            )
            btn.grid(row=r, column=c, padx=5, pady=4)
            self.page_buttons[p_id] = btn

        # ── Media Control Quick Remote Section ────────────────────────
        m_remote_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        m_remote_frame.pack(fill="x", padx=10, pady=4)

        m_remote_title = ctk.CTkLabel(m_remote_frame, text="🎵 Media Control Hotkeys (Bấm nhanh trên PC)", font=ctk.CTkFont(size=14, weight="bold"))
        m_remote_title.pack(anchor="w", padx=12, pady=(8, 4))

        m_remote_grid = ctk.CTkFrame(m_remote_frame, fg_color="transparent")
        m_remote_grid.pack(fill="x", padx=10, pady=(0, 8))

        media_btns = [
            ("⏮ PREV", "prev", "#21262d", "#30363d"),
            ("▶❚❚ PLAY/PAUSE", "play_pause", "#238636", "#2ea043"),
            ("⏭ NEXT", "next", "#21262d", "#30363d"),
            ("🔉 VOL -", "vol_down", "#21262d", "#30363d"),
            ("⏩ SKIP AD", "skip_ad", "#d97706", "#b45309"),
            ("🔊 VOL +", "vol_up", "#21262d", "#30363d")
        ]

        for idx, (b_name, b_act, b_fg, b_hov) in enumerate(media_btns):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                m_remote_grid, text=b_name, width=155, height=30,
                fg_color=b_fg, hover_color=b_hov, text_color="#ffffff",
                command=lambda a=b_act: handle_media_action(a)
            )
            btn.grid(row=r, column=c, padx=5, pady=4)

        # Highlight default active buttons at launch
        self.highlight_active_page(0)
        self.highlight_active_theme("ocean_dark")

        # ── Hardware Live Status Preview ──────────────────────────────
        m_frame = ctk.CTkFrame(container, fg_color="#161b22", corner_radius=10)
        m_frame.pack(fill="x", padx=10, pady=4)

        m_title = ctk.CTkLabel(m_frame, text="📊 Live Hardware Metrics Streamed", font=ctk.CTkFont(size=14, weight="bold"))
        m_title.pack(anchor="w", padx=12, pady=(10, 5))

        self.metrics_lbl = ctk.CTkLabel(
            m_frame, text="CPU: 0% | RAM: 0% | Net Down: 0 KB/s | Net Up: 0 KB/s",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        )
        self.metrics_lbl.pack(anchor="w", padx=12, pady=(0, 10))


    def _sync_ip_loop(self):
        """Runs on main thread every 2s — copies IP entry to cached_ip for background thread."""
        try:
            self.cached_ip = self.ip_entry.get().strip()
        except Exception:
            pass
        self.after(2000, self._sync_ip_loop)

    def _set_metrics_text(self, cpu, ram, down, up):
        self.metrics_lbl.configure(
            text=f"CPU: {cpu}% | RAM: {ram}% | Net\u2193 {down} KB/s | Net\u2191 {up} KB/s"
        )

    def _set_status(self, text, color):
        self.status_lbl.configure(text=text, text_color=color)

    def highlight_active_page(self, page_id):
        self.active_cyd_page = page_id
        if page_id == self.active_page_id:
            return
        self.active_page_id = page_id
        for pid, btn in self.page_buttons.items():
            if pid == page_id:
                btn.configure(fg_color="#1f6feb", hover_color="#388bfd", text_color="#ffffff")
            else:
                btn.configure(fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9")

    def highlight_active_theme(self, theme_key):
        if theme_key == self.active_theme_key:
            return
        self.active_theme_key = theme_key
        for key, btn in self.theme_buttons.items():
            if key == theme_key:
                btn.configure(fg_color="#238636", hover_color="#2ea043", text_color="#ffffff")
            else:
                btn.configure(fg_color="#21262d", hover_color="#30363d", text_color="#c9d1d9")

    def update_settings_gui(self, st_data):
        if not isinstance(st_data, dict):
            return
        if "city" in st_data and st_data["city"]:
            c_val = str(st_data["city"]).strip()
            for eng, vn in VN_CITIES:
                if eng.lower() == c_val.lower():
                    self.city_combo.set(vn)
                    break
        if "cur1" in st_data and st_data["cur1"]:
            self.cur1_combo.set(str(st_data["cur1"]).upper())
        if "cur2" in st_data and st_data["cur2"]:
            self.cur2_combo.set(str(st_data["cur2"]).upper())

    def apply_city(self):
        sel = self.city_combo.get()
        eng_city = "Hanoi"
        for eng, vn in VN_CITIES:
            if vn == sel:
                eng_city = eng
                break
        _send_control_cmd({"city": eng_city}, self.status_lbl, f"✅ City: {sel}", "❌ Error setting city")

    def apply_currencies(self):
        c1 = self.cur1_combo.get()
        c2 = self.cur2_combo.get()
        _send_control_cmd({"cur1": c1, "cur2": c2}, self.status_lbl, f"✅ Currencies: {c1}/{c2}", "❌ Currency error")

    def apply_theme(self, theme_key):
        self.highlight_active_theme(theme_key)
        _send_control_cmd({"preset": theme_key}, self.status_lbl, f"✅ Theme: {theme_key}", "❌ Theme error")

    def switch_page(self, page_id):
        self.highlight_active_page(page_id)
        _send_control_cmd({"page": page_id}, self.status_lbl, f"✅ Page: {page_id}", "❌ Page error")

    def stream_loop(self):
        # Sync current selected currencies to ESP32 on connect
        time.sleep(1)
        try:
            c1 = self.cur1_combo.get()
            c2 = self.cur2_combo.get()
            ip = self.ip_entry.get().strip()
            if ip:
                requests.get(f"http://{ip}/api/exchange?cur1={c1}&cur2={c2}", timeout=1)
        except Exception:
            pass

        ser = None
        ser_port = ""
        connected_usb = False
        connected_wifi = False

        # Blocking first call so next call(interval=1) gives real data right away
        psutil.cpu_percent(interval=1)

        last_port_scan = 0
        while True:
            if not self.is_streaming:
                time.sleep(1)
                continue

            # 1. Page-Aware Smart Hardware Metrics Collection (ultra-low PC CPU/GPU load)
            try:
                now_time = time.time()
                active_p = self.active_cyd_page

                # Always calculate network speeds continuously so delta dt is smooth and instant
                curr_net = psutil.net_io_counters()
                dt = now_time - self.last_time
                if dt > 0 and self.last_net is not None:
                    down_speed = int((curr_net.bytes_recv - self.last_net.bytes_recv) / dt / 1024)
                    up_speed = int((curr_net.bytes_sent - self.last_net.bytes_sent) / dt / 1024)
                else:
                    down_speed = up_speed = 0
                self.last_net = curr_net
                self.last_time = now_time

                # Base lightweight metrics
                cpu_pct = int(psutil.cpu_percent(interval=None))
                ram_pct = int(psutil.virtual_memory().percent)
                gpu_pct = vram_pct = 0
                disks = []
                is_playing = False
                media_title = media_artist = ""

                # Query GPU/VRAM when CYD is on Page 3 (PC Monitor) or Page 4 (Net & Storage)
                if active_p in (3, 4):
                    gpu_pct, vram_pct = self.gpu_mon.get_metrics()

                # Query Disks when on Page 4 or periodically
                for letter in string.ascii_uppercase:
                    drive_path = f"{letter}:\\"
                    if os.path.exists(drive_path):
                        try:
                            usage = psutil.disk_usage(drive_path)
                            if usage.total > 0:
                                disks.append({"name": letter, "used": int(round((usage.used / usage.total) * 100))})
                        except Exception:
                            pass

                # Query Media Track Info continuously or when on Page 6
                is_playing, media_title, media_artist = check_windows_media_playing()

                payload = {
                    "cpu": cpu_pct,
                    "cpuLoad": cpu_pct,
                    "cputemp": 45,
                    "cpuTemp": 45,
                    "ram": ram_pct,
                    "ramLoad": ram_pct,
                    "gpu": gpu_pct,
                    "gpuLoad": gpu_pct,
                    "gputemp": 48,
                    "gpuTemp": 48,
                    "vram": vram_pct,
                    "vramLoad": vram_pct,
                    "net_down": down_speed,
                    "netDown": down_speed,
                    "net_up": up_speed,
                    "netUp": up_speed,
                    "disks": disks,
                    "isMediaPlaying": is_playing,
                    "mediaTitle": media_title,
                    "mediaArtist": media_artist
                }

                # Update live GUI label IMMEDIATELY (thread-safe)
                self.after(0, lambda c=cpu_pct, r=ram_pct, d=down_speed, u=up_speed:
                           self._set_metrics_text(c, r, d, u))
            except Exception:
                with open("debug.log", "a") as _f:
                    _f.write(f"[METRICS ERR] {time.time():.0f}: {traceback.format_exc()}\n")
                time.sleep(0.5)
                continue

            # Reset connection flags each loop iteration
            connected_usb = False
            connected_wifi = False
            active_wifi_ip = ""

            # 2. USB Serial Auto Connection (instant non-resetting connection)
            if (ser is None or not ser.is_open) and (now_time - last_port_scan > 2.0):
                last_port_scan = now_time
                try:
                    ports = list(serial.tools.list_ports.comports())
                    for p in ports:
                        desc = str(p.description).upper()
                        if p.vid is not None and ("CH340" in desc or "CP210" in desc or "USB" in desc or "UART" in desc or "COM4" in str(p.device).upper()):
                            try:
                                s = serial.Serial()
                                s.port = p.device
                                s.baudrate = 115200
                                s.dtr = False
                                s.rts = False
                                s.timeout = 0.1
                                s.open()
                                ser = s
                                global active_serial_conn
                                active_serial_conn = ser
                                ser_port = p.device
                                print(f"[USB Serial]: Connected on {p.device}")
                                break
                            except Exception:
                                pass
                except Exception:
                    ser = None

            if ser and ser.is_open:
                try:
                    json_line = json.dumps(payload) + "\n"
                    ser.write(json_line.encode('utf-8'))
                    connected_usb = True
                    # Read any response for page/theme/media sync (non-blocking)
                    if ser.in_waiting:
                        try:
                            resp_line = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                            for l in resp_line.splitlines():
                                l = l.strip()
                                if "MEDIA_CMD:" in l:
                                    handle_media_action(l.split("MEDIA_CMD:")[1].strip())
                                elif l.startswith("STATE:"):
                                    try:
                                        st_data = json.loads(l[6:])
                                        cyd_page = st_data.get("page", -1)
                                        cyd_theme = st_data.get("theme", "")
                                        if cyd_page >= 0:
                                            self.after(0, lambda p=cyd_page: self.highlight_active_page(p))
                                        if cyd_theme:
                                            self.after(0, lambda t=cyd_theme: self.highlight_active_theme(t))
                                        self.after(0, lambda d=st_data: self.update_settings_gui(d))
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                except Exception:
                    try: ser.close()
                    except Exception: pass
                    ser = None

            # 3. WiFi HTTP Streaming — try IP first, fallback to mDNS cyd-dashboard.local
            ip_list = [self.cached_ip, "cyd-dashboard.local"] if self.cached_ip else ["cyd-dashboard.local"]
            for target_ip in ip_list:
                if not target_ip:
                    continue
                try:
                    resp = http_stream_session.post(f"http://{target_ip}/api/pc", json=payload, timeout=0.4)
                    if resp.ok:
                        connected_wifi = True
                        active_wifi_ip = target_ip
                        if target_ip != self.cached_ip:
                            self.cached_ip = target_ip
                        try:
                            res_data = resp.json()
                            # Sync page/theme/city/currencies from CYD response
                            cyd_page = res_data.get("page", -1)
                            cyd_theme = res_data.get("theme", "")
                            if cyd_page >= 0:
                                self.after(0, lambda p=cyd_page: self.highlight_active_page(p))
                            if cyd_theme:
                                self.after(0, lambda t=cyd_theme: self.highlight_active_theme(t))
                            # Sync settings GUI (city/currencies)
                            self.after(0, lambda d=res_data: self.update_settings_gui(d))
                            # Handle media remote action
                            media_act = res_data.get("mediaAction", "")
                            if media_act:
                                handle_media_action(media_act)
                        except Exception:
                            pass
                        break # Connected successfully!
                except Exception:
                    pass

            # 4. Status Indicator Update (thread-safe via after)
            if connected_usb:
                self.after(0, lambda p=ser_port: self._set_status(f"\u25cf Connected (USB {p})", "#2ea043"))
            elif connected_wifi:
                self.after(0, lambda i=active_wifi_ip: self._set_status(f"\u25cf Connected (WiFi {i})", "#2ea043"))
            else:
                self.after(0, lambda: self._set_status("\u25cf Searching for CYD...", "#d29922"))

            # Dynamic Real-Time Streaming interval: 0.35s (~3 FPS) on PC Monitor pages (3 & 4), 0.5s on others
            if self.active_cyd_page in (3, 4):
                time.sleep(0.35)
            else:
                time.sleep(0.5)

    def create_tray_icon(self):
        """Runs in its own non-daemon thread. Blocking call."""
        # Draw ESP32 chip icon
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(image)
        d.rectangle((8, 8, 56, 56), fill=(13, 17, 23))
        d.ellipse((16, 16, 48, 48), fill=(88, 166, 255))
        d.rectangle((26, 26, 38, 38), fill=(13, 17, 23))

        def on_open(icon, item):
            self.after(0, self.deiconify)

        def on_exit(icon, item):
            icon.stop()
            self.after(0, self._do_exit)

        menu = pystray.Menu(
            pystray.MenuItem("Open Studio", on_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", on_exit)
        )
        self.tray_icon = pystray.Icon("CYDStudio", image, "CYD Dashboard Studio", menu)
        self.tray_icon.run()  # blocks until icon.stop()

    def minimize_to_tray(self):
        self.withdraw()
        if self.tray_icon is None:
            t = threading.Thread(target=self.create_tray_icon, daemon=False)
            t.start()
        # if already running, just stay hidden

    def show_from_tray(self, icon=None, item=None):
        self.deiconify()

    def _do_exit(self):
        self.tray_icon = None
        self.destroy()
        sys.exit(0)

    def exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self._do_exit()

if __name__ == "__main__":
    app = CYDMonitorApp()
    app.mainloop()
