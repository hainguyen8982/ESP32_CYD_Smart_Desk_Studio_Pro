# ESP32 CYD Smart Desk Dashboard

Dự án Đồng hồ thời tiết để bàn thông minh, Lịch vạn niên Âm - Dương, Giám sát thông số máy tính (PC Monitor) và Tiện ích để bàn (Pomodoro & Báo thức) thiết kế cho board **ESP32 CYD (Cheap Yellow Display - 2.8" TFT Touch)**.

---

## 🌟 Tính Năng Nổi Bật (7 Dashboard Pages)

* **🌤️ Trang 0: Đồng Hồ & Thời Tiết Trung Tâm (Main Weather Clock)**
  - Đồng hồ số lớn, Dương lịch & **Âm lịch Việt Nam** song song (`vn_lunar`).
  - Thời tiết thời gian thực: Nhiệt độ (°C), Độ ẩm (%), Tình trạng thời tiết, Sức gió, Chỉ số UV.
* **📅 Trang 1: Lịch Vạn Niên Âm - Dương & Lưới Lịch Tháng**
  - Hiển thị thông tin Âm lịch chi tiết, lưới lịch 7x6 highlight ngày hiện tại.
* **📈 Trang 2: Financial & Market Dashboard (Tài chính & Giá Vàng)**
  - Giá Vàng SJC Mua/Bán & Giá Vàng Thế Giới XAUUSD.
  - Tỷ giá Ngoại tệ thời gian thực (USD/VND, EUR/VND, JPY/VND).
* **💻 Trang 3: PC Monitor (CPU & RAM)**
  - Arc Gauge % tải CPU, % RAM, Biểu đồ đường biến động CPU thời gian thực.
* **🎮 Trang 4: PC Monitor (GPU & VRAM)**
  - Arc Gauge % tải GPU, % VRAM, Biểu đồ GPU.
* **🌐 Trang 5: PC Monitor (Network & Disks)**
  - Tốc độ mạng Tải/Tải lên (DL/UL speed), Dung lượng các ổ đĩa C:, D:, E:... & IP ESP32 CYD.
* **⏱️ Trang 6: Desk Utilities (Pomodoro Timer & Báo Thức)**
  - Bộ đếm tập trung Pomodoro 25m/5m, Báo thức phát còi và nhấp nháy đèn RGB LED.

---

## 🛠️ Cấu Hình Phần Cứng Chuẩn (ESP32 CYD 2.8")

- **TFT Display Driver:** `ILI9341_2_DRIVER` (SPI HSPI: CS=15, DC=2, BL=21 PWM)
- **Universal Touch Auto-Detect Driver:** Tự động phát hiện Cảm ứng Điện dung (GT911/CST816 I2C) hoặc Cảm ứng Điện trở (XPT2046 SPI CS=33, IRQ=36).
- **LDR Light Sensor:** GPIO 34 (Tự động chỉnh độ sáng đèn nền màn hình).
- **Onboard Speaker:** GPIO 26 (Còi báo & âm thanh chạm).
- **RGB LED:** Red=GPIO 4, Green=GPIO 16, Blue=GPIO 17.

---

## 🚀 Hướng Dẫn Biên Dịch & Sử Dụng

### 1. Nạp Firmware Lên ESP32 CYD
```bash
cd ESP32_CYD_Smart_Desk_Dashboard
pio run -t upload -e esp32_display
```

### 2. Dịch Vụ Giám Sát PC (Windows)
```bash
cd pc_utility
pip install psutil pyserial wmi pyinstaller
python pc_monitor.py
```
*(Để chạy ẩn cùng Windows: `pyinstaller --onefile --noconsole pc_monitor.py` và copy file `.exe` vào `shell:startup`)*
