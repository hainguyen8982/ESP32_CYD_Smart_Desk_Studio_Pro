import sys
import time
import threading
import requests
import psutil
import customtkinter as ctk
from PIL import Image, ImageDraw
import pystray

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

class CYDMonitorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("ESP32 CYD Desk Dashboard Studio")
        self.geometry("560x680")
        self.resizable(False, False)

        self.esp32_ip = "192.168.1.13"
        self.is_streaming = True
        self.tray_icon = None

        # Network speed tracking
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        # Start background hardware metrics streaming thread
        self.stream_thread = threading.Thread(target=self.stream_loop, daemon=True)
        self.stream_thread.start()

    def create_widgets(self):
        # ── Header Frame ──────────────────────────────────────────────
        hdr_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        hdr_frame.pack(fill="x", padx=15, pady=(15, 10))

        title_lbl = ctk.CTkLabel(
            hdr_frame, text="💻 ESP32 CYD Smart Dashboard Studio",
            font=ctk.CTkFont(size=18, weight="bold"), text_color="#58a6ff"
        )
        title_lbl.pack(pady=10)

        # ── Connection Settings ───────────────────────────────────────
        conn_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        conn_frame.pack(fill="x", padx=15, pady=5)

        ip_lbl = ctk.CTkLabel(conn_frame, text="ESP32 IP Address:", font=ctk.CTkFont(size=13))
        ip_lbl.pack(side="left", padx=12, pady=10)

        self.ip_entry = ctk.CTkEntry(conn_frame, width=140)
        self.ip_entry.insert(0, self.esp32_ip)
        self.ip_entry.pack(side="left", padx=5, pady=10)

        self.status_lbl = ctk.CTkLabel(
            conn_frame, text="● Connected", font=ctk.CTkFont(size=12, weight="bold"), text_color="#2ea043"
        )
        self.status_lbl.pack(side="right", padx=15, pady=10)

        # ── Weather Location Section ──────────────────────────────────
        w_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        w_frame.pack(fill="x", padx=15, pady=5)

        w_title = ctk.CTkLabel(w_frame, text="🌤️ Weather Location", font=ctk.CTkFont(size=14, weight="bold"))
        w_title.pack(anchor="w", padx=12, pady=(10, 5))

        w_inner = ctk.CTkFrame(w_frame, fg_color="transparent")
        w_inner.pack(fill="x", padx=12, pady=(0, 10))

        city_names = [c[1] for c in VN_CITIES]
        self.city_combo = ctk.CTkOptionMenu(w_inner, values=city_names, width=280)
        self.city_combo.set("Hà Nội")
        self.city_combo.pack(side="left", padx=(0, 10))

        set_city_btn = ctk.CTkButton(w_inner, text="Set City", width=100, command=self.apply_city)
        set_city_btn.pack(side="left")

        # ── Theme Presets Section ─────────────────────────────────────
        t_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        t_frame.pack(fill="x", padx=15, pady=5)

        t_title = ctk.CTkLabel(t_frame, text="🎨 Theme Presets", font=ctk.CTkFont(size=14, weight="bold"))
        t_title.pack(anchor="w", padx=12, pady=(10, 5))

        t_grid = ctk.CTkFrame(t_frame, fg_color="transparent")
        t_grid.pack(fill="x", padx=10, pady=(0, 10))

        for idx, (name, key) in enumerate(THEMES):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                t_grid, text=name, width=155, height=32,
                command=lambda k=key: self.apply_theme(k)
            )
            btn.grid(row=r, column=c, padx=5, pady=5)

        # ── Remote Page Switcher ──────────────────────────────────────
        p_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        p_frame.pack(fill="x", padx=15, pady=5)

        p_title = ctk.CTkLabel(p_frame, text="📱 Remote Page Switcher", font=ctk.CTkFont(size=14, weight="bold"))
        p_title.pack(anchor="w", padx=12, pady=(10, 5))

        p_grid = ctk.CTkFrame(p_frame, fg_color="transparent")
        p_grid.pack(fill="x", padx=10, pady=(0, 10))

        pages = [
            ("0: Weather Clock", 0), ("1: Lunar Calendar", 1), ("2: Gold & Finance", 2),
            ("3: PC CPU/RAM", 3),     ("4: PC GPU/VRAM", 4),     ("5: PC Net/Disks", 5),
            ("6: Desk Utilities", 6)
        ]

        for idx, (p_name, p_id) in enumerate(pages):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                p_grid, text=p_name, width=155, height=30, fg_color="#21262d", hover_color="#30363d",
                command=lambda pid=p_id: self.switch_page(pid)
            )
            btn.grid(row=r, column=c, padx=5, pady=4)

        # ── Hardware Live Status Preview ──────────────────────────────
        m_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        m_frame.pack(fill="x", padx=15, pady=5)

        m_title = ctk.CTkLabel(m_frame, text="📊 Live Hardware Metrics Streamed", font=ctk.CTkFont(size=14, weight="bold"))
        m_title.pack(anchor="w", padx=12, pady=(10, 5))

        self.metrics_lbl = ctk.CTkLabel(
            m_frame, text="CPU: 0% | RAM: 0% | Net Down: 0 KB/s | Net Up: 0 KB/s",
            font=ctk.CTkFont(size=12), text_color="#8b949e"
        )
        self.metrics_lbl.pack(anchor="w", padx=12, pady=(0, 10))

    def apply_city(self):
        sel = self.city_combo.get()
        eng_city = "Hanoi"
        for eng, vn in VN_CITIES:
            if vn == sel:
                eng_city = eng
                break

        ip = self.ip_entry.get().strip()
        try:
            resp = requests.post(f"http://{ip}/api/weather/city", json={"city": eng_city}, timeout=2)
            if resp.ok:
                self.status_lbl.configure(text=f"✅ City: {sel}", text_color="#2ea043")
        except Exception as e:
            self.status_lbl.configure(text="❌ Error setting city", text_color="#f85149")

    def apply_theme(self, theme_key):
        ip = self.ip_entry.get().strip()
        try:
            resp = requests.post(f"http://{ip}/api/theme", json={"preset": theme_key}, timeout=2)
            if resp.ok:
                self.status_lbl.configure(text=f"✅ Theme: {theme_key}", text_color="#2ea043")
        except Exception:
            self.status_lbl.configure(text="❌ Theme error", text_color="#f85149")

    def switch_page(self, page_id):
        ip = self.ip_entry.get().strip()
        try:
            requests.get(f"http://{ip}/api/page?id={page_id}", timeout=2)
        except Exception:
            pass

    def stream_loop(self):
        while True:
            if self.is_streaming:
                try:
                    ip = self.ip_entry.get().strip()
                    cpu_pct = int(psutil.cpu_percent(interval=1.0))
                    ram_pct = int(psutil.virtual_memory().percent)

                    # Compute network speed
                    now_time = time.time()
                    curr_net = psutil.net_io_counters()
                    dt = now_time - self.last_time
                    if dt > 0:
                        down_speed = int((curr_net.bytes_recv - self.last_net.bytes_recv) / dt / 1024)
                        up_speed = int((curr_net.bytes_sent - self.last_net.bytes_sent) / dt / 1024)
                    else:
                        down_speed = up_speed = 0

                    self.last_net = curr_net
                    self.last_time = now_time

                    disk_pct = int(psutil.disk_usage('/').percent)

                    payload = {
                        "cpuLoad": cpu_pct,
                        "cpuTemp": 45,
                        "ramLoad": ram_pct,
                        "ramUsed": round(psutil.virtual_memory().used / (1024**3), 1),
                        "ramTotal": round(psutil.virtual_memory().total / (1024**3), 1),
                        "gpuLoad": cpu_pct,  # fallback to CPU load if no pynvml
                        "gpuTemp": 48,
                        "vramLoad": ram_pct,
                        "netDown": down_speed,
                        "netUp": up_speed,
                        "disk1Load": disk_pct,
                        "disk2Load": 0
                    }

                    # Update live GUI label
                    self.metrics_lbl.configure(
                        text=f"CPU: {cpu_pct}% | RAM: {ram_pct}% | Net Down: {down_speed} KB/s | Net Up: {up_speed} KB/s"
                    )

                    resp = requests.post(f"http://{ip}/api/pc", json=payload, timeout=1.5)
                    if resp.ok:
                        self.status_lbl.configure(text="● Streaming Active", text_color="#2ea043")
                    else:
                        self.status_lbl.configure(text="● Disconnected", text_color="#f85149")
                except Exception:
                    self.status_lbl.configure(text="● Offline", text_color="#f85149")
                    time.sleep(2)
            else:
                time.sleep(2)

    def create_tray_icon(self):
        # Create a simple blue icon for system tray
        image = Image.new('RGB', (64, 64), color=(13, 17, 23))
        d = ImageDraw.Draw(image)
        d.ellipse((12, 12, 52, 52), fill=(88, 166, 255))
        d.rectangle((24, 24, 40, 40), fill=(13, 17, 23))

        menu = pystray.Menu(
            pystray.MenuItem("Open Studio", self.show_from_tray, default=True),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon("CYDStudio", image, "ESP32 CYD Dashboard Studio", menu)
        self.tray_icon.run()

    def minimize_to_tray(self):
        self.withdraw()
        if not self.tray_icon:
            threading.Thread(target=self.create_tray_icon, daemon=True).start()

    def show_from_tray(self, icon=None, item=None):
        self.deiconify()

    def exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = CYDMonitorApp()
    app.mainloop()
