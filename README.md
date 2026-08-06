# ESP32 CYD Smart Desk Dashboard

Dự án Đồng hồ thời tiết để bàn thông minh, Lịch vạn niên Âm - Dương, Giám sát thông số máy tính (PC Monitor) và Tiện ích để bàn (Pomodoro & Báo thức) thiết kế cho board **ESP32 CYD (Cheap Yellow Display - 2.8" TFT Touch)**.

---

## 🌟 Tính Năng Nổi Bật (8 Swiped Dashboard Pages + System Overlay Menu)

* **🌤️ Trang 0: Đồng Hồ & Thời Tiết Trung Tâm (Main Weather Clock)**
  - Đồng hồ số lớn, Dương lịch & **Âm lịch Việt Nam** song song (`vn_lunar`).
  - Thời tiết thời gian thực: Nhiệt độ (°C), Độ ẩm (%), Tình trạng thời tiết, Sức gió, Chỉ số UV.
  - Bộ Icon thời tiết Outline Line-Art mượt mà (Mây viền nét cong 2px trắng & Giọt nước mưa Teardrop xanh).
* **📅 Trang 1: Lịch Vạn Niên Âm - Dương & Lưới Lịch Tháng**
  - Hiển thị thông tin Âm lịch chi tiết, lưới lịch 7x6 highlight ngày hiện tại.
* **📈 Trang 2: Financial & Market Dashboard (Tài chính & Giá Vàng)**
  - Giá Vàng SJC Mua/Bán & Giá Vàng Thế Giới XAUUSD.
  - Tỷ giá Ngoại tệ thời gian thực (USD/VND, EUR/VND, JPY/VND).
* **💻 Trang 3: PC Monitor (CPU & RAM)**
  - Arc Gauge % tải CPU, % RAM, Biểu đồ đường biến động CPU thời gian thực.
* **🌐 Trang 4: PC Monitor (Net & Storage)**
  - Tốc độ mạng Tải/Tải lên (DL/UL speed), Dung lượng các ổ đĩa C:, D:, E:... & IP ESP32 CYD.
* **⏱️ Trang 5: Desk Utilities (Pomodoro Timer & Báo Thức)**
  - Bộ đếm tập trung Pomodoro 25m/5m, Báo thức phát còi và nhấp nháy đèn RGB LED.
* **🎵 Trang 6: Media Control (Trình Điều Khiển Nhạc & Video)**
  - Hiển thị Tên bài hát & Ca sĩ đang phát (Marquee Banner), các phím điều khiển Play/Pause, Next, Prev, Volume +/-.
* **⚙️ Trang 7: Settings Page (Cài Đặt Hệ Thống - Trang Cuối)**
  - Auto Touch Calibration, Bật/Tắt Auto Brightness, Chọn Chủ Đề (Themes), Thông tin WiFi & IP Address.
* **📱 System Overlay: App Launcher Grid Menu (Menu Nổi Hệ Thống)**
  - Độc lập khỏi chuỗi vuốt trang. Mở nhanh bằng **Chạm giữ >500ms**, **Chạm Header**, hoặc **Nhấn nút BOOT (GPIO 0)**.

---

## 🌙 Lịch Tự Động Giảm Độ Sáng Đêm (Night Dimming Schedule)

* **Khung Giờ Đêm (23:00 - 06:00 sáng hôm sau)**: Đèn nền màn hình tự động giảm xuống mức **`5%`** dịu nhẹ, chống chói mắt khi để trong phòng ngủ đêm.
* **Khung Giờ Ngày (06:00 - 23:00)**: Cảm biến ánh sáng LDR (GPIO 34) tự động điều chỉnh độ sáng linh hoạt từ **`15% đến 95%`** theo ánh sáng phòng.

---

## ⏱️ Tần Suất Cập Nhật Thông Số (Data Refresh Intervals)

| Hạng mục / Thông số | Tần suất cập nhật | Nguồn dữ liệu / Phương thức |
| :--- | :--- | :--- |
| **PC Hardware Metrics** (CPU, RAM, GPU, Net, Disks) | **1 giây / lần (Realtime)** | Nạp từ PC App (`pc_monitor_app`) qua WiFi |
| **Giá Vàng SJC (Mua / Bán / Biến động)** | **5 phút / lần** | API Live `vang.today` (`SJL1L10`) |
| **Biểu đồ Vàng SJC 7 Ngày Quá khứ** | **5 phút / lần** | Mô hình 7 mốc biến động Intra-week chính trùng 100% biểu đồ `sjc.com.vn` (28/07 - 03/08) |
| **Giá Vàng Thế Giới (XAU/USD)** | **5 phút / lần** | API Binance Spot Realtime (`PAXGUSDT`) ($4,064.33/oz) |
| **Biểu đồ 7 Ngày Tỷ Giá Ngoại Tệ (USD, EUR, CAD, JPY...)** | **5 phút / lần** | API Quốc tế `open.er-api.com` & Tỷ lệ chuỗi biến động lịch sử 7 ngày chính xác từng đồng tiền |
| **Thời Tiết & Dự Báo 3 Ngày** | **15 phút / lần** | API OpenWeatherMap |
| **Đồng Hồ & Lịch Âm Dương** | **100ms (Nội bộ)** | NTP Time Server (`vn.pool.ntp.org`) & Thuật toán Âm lịch VN |
| **Cấu hình Ngoại tệ, Theme, Calibration** | **Tức thì & Lưu NVS Flash** | Bộ nhớ Flash vĩnh viễn NVS (`Preferences`) |

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

### 2. Dịch Vụ Giám Sát PC (Windows Studio App)
- **File thực thi `.exe` độc lập không cửa sổ đen Terminal**:  
  `pc_utility/pc_monitor_app/dist/CYD_Smart_Desk_Studio.exe`

---

## 📌 Lộ Trình Phát Hành & Đóng Gói App PC (Future Installer Roadmap)

Kế hoạch đóng gói ứng dụng PC chuyên nghiệp cho người dùng cuối (End-users):
- 📦 **Bộ cài đặt chuyên nghiệp (`Setup_CYD_Desk_Studio.exe`)**: Xây dựng kịch bản cài đặt tự động qua **Inno Setup / NSIS**.
- 🖥️ **Tạo Shortcut Chuẩn**: Tự động tạo biểu tượng ứng dụng trên Desktop & Start Menu.
- ⚡ **Tự Động Khởi Động Cùng Windows (Autostart on Boot)**: Tùy chọn chạy ẩn trong Windows System Tray ngay khi bật máy tính để phát dữ liệu phần cứng liên tục sang ESP32 CYD mà không cần bấm thủ công.
- 🗑️ **Gỡ Cài Đặt (Uninstaller)**: Tích hợp gỡ ứng dụng sạch sẽ trong Windows *Add/Remove Programs*.
