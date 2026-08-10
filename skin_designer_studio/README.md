# 🎨 SMART DESK STUDIO - LAYOUT & SKIN DESIGNER (PROTOTYPE)

Thư mục này chứa ứng dụng thử nghiệm **Desktop Skin Designer Studio** — phần mềm đồ họa kéo thả (Drag-and-Drop) thiết kế bố cục và giao diện Skin độc lập dành cho ESP32 CYD Smart Desk Dashboard.

---

## 🚀 Hướng Dẫn Chạy & Thử Nghiệm

Mở **PowerShell** hoặc **Command Prompt** tại thư mục này và chạy:

```bash
cd skin_designer_studio
python main.py
```

---

## 🌟 Các Tính Năng Đồ Họa Đã Hiện Có Trong Bản Prototype

1. **📺 Canvas Tỉ Lệ Chuẩn 320x240 Pixel-Perfect (Scaled 2.5x - 800x600)**:
   - Mô phỏng chính xác khung màn hình TFT 2.8" của ESP32 CYD với lưới tọa độ pixel (Grid lines).
2. **🖱️ Kéo Thả (Drag & Drop) & Co Giãn Widget (Resize Handles)**:
   - Nhấp giữ chuột trái vào bất kỳ khối ô Widget nào để **di chuyển vị trí (X, Y)**.
   - Nhấp kéo núm vuông xanh ở góc dưới bên phải widget để **thay đổi kích thước độ rộng (W) & độ cao (H)**.
3. **📦 Thư Viện Skin Presets Đa Dạng**:
   - Chọn mẫu Skin có sẵn (`Cyberpunk Neon HUD`, `Nordic Minimalist Studio`, `Luxury Gold & Finance`) để tự động nạp cấu hình và xem thử giao diện ngay lập tức.
4. **⚙️ Bộ Chỉnh Thuộc Tính (Widget Inspector)**:
   - Tùy chỉnh tọa độ X, Y, W, H bằng số.
   - Tùy chọn **Color Picker** đổi màu nền Card Background và màu nhấn Accent Color của từng Widget.
   - Thêm bớt Widget mới (`Clock`, `Weather`, `CPU Gauge`, `RAM Meter`, `Gold Price`, `Line Chart`) hoặc xóa bỏ ô không dùng.
5. **💾 Đóng Gói Export / Import Skin JSON Schema**:
   - Xuất cấu hình Skin thành file `.json` để sẵn sàng gửi xuống mạch ESP32 CYD trong tương lai.

---

> ⚠️ **Ghi chú**: Đây là thư mục dự án độc lập dùng để thử nghiệm ứng dụng thiết kế đồ họa Skin trên PC. **Mã nguồn firmware và ứng dụng chính trên Dashboard của ESP32 CYD hoàn toàn không bị ảnh hưởng hay thay đổi**.
