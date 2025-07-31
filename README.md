# 🎼 Bộ công cụ Media (VideoCreatorApp)

**VideoCreatorApp** là một ứng dụng desktop đa năng dành cho Windows, giúp bạn dễ dàng chỉnh sửa file âm thanh, tạo video từ ảnh và nhạc, cũng như xử lý hàng loạt file media một cách nhanh chóng. Ứng dụng được xây dựng bằng Python với giao diện đồ họa thân thiện.

---

## ✨ Tính năng chính

Ứng dụng được chia thành **3 tab chức năng chính**:

### 1. 🎹 Sửa Nhạc
- **Hiển thị dạng sóng**: Trực quan hóa file âm thanh trên canvas, giúp điều hướng dễ dàng.
- **Phát nhạc cơ bản**: Hỗ trợ Play, Pause, Stop, và tua nhanh bằng cách nhấp trực tiếp vào waveform.
- **Áp dụng hiệu ứng**:
  - Thay đổi **Tốc độ (Speed)** và **Nhịp độ (Tempo)**.
  - Điều chỉnh **Cao độ (Pitch)** theo từng nửa cung.
  - **Chuẩn hóa âm lượng (Normalize)**.
  - **Giảm tiếng ồn (Noise Reduction)** cơ bản.
  - Thêm nhiễu nền (**Trắng**, **Hồng**, **Nâu**) với cường độ tùy chỉnh.
- **Xuất hàng loạt**: Chọn nhiều file và áp dụng cùng một bộ hiệu ứng để xuất.

### 2. 🎬 Tạo Video
- **Tạo video từ ảnh + nhạc**: Nhanh chóng tạo video từ một ảnh tĩnh và một file âm thanh.
- **Quản lý ảnh trực quan**: Danh sách ảnh dưới dạng thumbnail, chọn ảnh nền cho video.
- **Hỗ trợ định dạng**: Tạo video với các định dạng phổ biến như `.mp4`, `.mkv`, `.mov`...
- **Tối ưu cho ảnh tĩnh**: Sử dụng FFMPEG để giữ chất lượng video cao nhất.

### 3. ⚡ Xử lý nhanh
- **Xử lý hàng loạt** file trong thư mục.
- Các **mẫu thiết lập sẵn**:
  - Tăng/Giảm tốc nhẹ.
  - Thêm nhiễu trắng siêu nhẹ.
  - Chuẩn hóa âm lượng.
- **Tự động hóa toàn bộ quy trình** và lưu kết quả vào thư mục đầu ra riêng biệt.

---

## 🛠️ Yêu cầu

### Dành cho người dùng (chạy `.exe`)
- Windows 7, 10, 11
- Không cần cài thêm nếu sử dụng bản đã đóng gói (`.exe`)

### Dành cho lập trình viên (chạy từ mã nguồn)
- **Python** 3.8+
- **FFmpeg & FFprobe**: Cần được cài đặt và thêm vào `PATH` hệ thống  
  → [Tải FFmpeg tại đây](https://ffmpeg.org/download.html)

### Thư viện Python yêu cầu:
```bash
pip install pygame Pillow numpy tkinterdnd2-universal
