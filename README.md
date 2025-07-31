# 🎼 Bộ Công Cụ Media (VideoCreatorApp)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg) ![License](https://img.shields.io/badge/License-MIT-green.svg)

**VideoCreatorApp** là một ứng dụng máy tính đa năng, mạnh mẽ dành cho Windows, được thiết kế để trở thành người bạn đồng hành của những người sáng tạo nội dung. Cung cấp một bộ công cụ "tất cả trong một" để chỉnh sửa âm thanh, tạo video nhanh và xử lý hàng loạt tệp media.

![Giao diện ứng dụng](https://i.imgur.com/your-screenshot.gif)
*(Mẹo: Hãy quay một video GIF ngắn giới thiệu ứng dụng và thay thế link trên để README thêm phần sống động!)*

---

## 📋 Mục lục
* [Tính năng nổi bật](#-tính-năng-nổi-bật)
* [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
* [Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)
* [Hướng dẫn sử dụng](#-hướng-dẫn-sử-dụng)
* [Đóng góp](#-đóng-góp)
* [Giấy phép](#-giấy-phép)

---

## ✨ Tính năng nổi bật

### 🎹 **Tab 1: Trình Sửa Âm Thanh**
- **Trực quan hóa Sóng Âm:** Phân tích và hiển thị dạng sóng của tệp audio trên Canvas, cho phép bạn "nhìn" thấy âm nhạc.
- **Điều khiển Trực quan:** Tua nhạc tức thì bằng cách nhấp chuột vào bất kỳ vị trí nào trên dạng sóng.
- **Bộ Hiệu ứng Đa dạng:**
    - 🎚️ **Tốc độ & Nhịp độ:** Tăng hoặc giảm tốc độ phát lại mà không làm thay đổi (hoặc có thay đổi) cao độ.
    - 🎵 **Cao độ (Pitch):** Dịch chuyển tông của bản nhạc lên hoặc xuống.
    - 🔊 **Chuẩn hóa Âm lượng:** Tự động điều chỉnh âm lượng để đạt mức tiêu chuẩn, tránh tình trạng quá to hoặc quá nhỏ.
    - 🤫 **Giảm Tiếng ồn:** Loại bỏ các tạp âm nền không mong muốn.
- **📤 Xuất hàng loạt:** Áp dụng một bộ hiệu ứng cho nhiều tệp và xuất chúng cùng một lúc.

### 🎬 **Tab 2: Trình Tạo Video**
- **Ảnh + Nhạc = Video:** Tạo video một cách siêu tốc chỉ từ một tệp ảnh và một tệp âm thanh.
- **Thư viện Ảnh:** Quản lý danh sách ảnh đầu vào với chế độ xem thumbnail tiện lợi.
- **Linh hoạt Định dạng:** Hỗ trợ xuất ra các định dạng video phổ biến nhất (`.mp4`, `.mkv`, `.avi`, `.mov`).

### ⚡ **Tab 3: Xử Lý Nhanh**
- **Sức mạnh Tự động hóa:** Chọn một thư mục nguồn và một thư mục đích để xử lý hàng trăm tệp audio chỉ bằng một cú nhấp chuột.
- **Các Mẫu Thiết lập Sẵn:** Nhanh chóng áp dụng các cấu hình phổ biến như "Tăng tốc nhẹ" hoặc "Chuẩn hóa âm lượng" cho toàn bộ tệp.

---

## 🛠️ Yêu cầu hệ thống

### **Đối với Người dùng cuối**
- Hệ điều hành Windows 7/10/11.
- Chỉ cần tải file `.exe` và chạy. Không yêu cầu cài đặt thêm.

### **Đối với Lập trình viên**
- **Python 3.8** trở lên.
- **FFmpeg:** Đã được cài đặt và thêm vào biến môi trường `PATH` của hệ thống. (Tải tại [ffmpeg.org](https://ffmpeg.org/download.html))
- Các thư viện Python được liệt kê trong file `requirements.txt`.

---

## 🚀 Hướng dẫn cài đặt

### **Cách 1: Tải bản dựng sẵn (.exe)**
1.  Đi đến mục **[Releases](https://github.com/your-username/your-repo/releases)** của dự án.
2.  Tải về tệp `VideoCreatorApp.exe`.
3.  Nhấp đúp vào tệp để khởi chạy ứng dụng.

### **Cách 2: Chạy từ Mã nguồn**
1.  Clone repository này về máy:
    ```bash
    git clone [https://github.com/your-username/your-repo.git](https://github.com/your-username/your-repo.git)
    cd your-repo
    ```
2.  Tạo một môi trường ảo (khuyến khích):
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
3.  Cài đặt các thư viện cần thiết (đảm bảo bạn đã có file `requirements.txt`):
    ```bash
    pip install -r requirements.txt
    ```
4.  Chạy ứng dụng:
    ```bash
    python VideoCreatorApp.py
    ```

---

## 📖 Hướng dẫn sử dụng

1.  **Sửa Nhạc:**
    - Kéo thả tệp audio vào danh sách hoặc dùng menu `File` -> `Thêm file...`.
    - Nhấp vào một tệp trong danh sách để xem dạng sóng.
    - Điều chỉnh các thanh trượt hiệu ứng bên dưới.
    - Nhấn `▶ Play` để nghe thử bản xem trước.
    - Tích vào các ô checkbox của những tệp bạn muốn xuất, sau đó nhấn nút `Xuất Audio đã chọn...`.

2.  **Tạo Video:**
    - Kéo thả một hoặc nhiều ảnh vào khu vực "Danh sách ảnh".
    - Kéo thả một tệp audio vào ô "Chọn file âm thanh" hoặc dùng nút `Duyệt...`.
    - Nhấp vào một ảnh trong danh sách để chọn làm nền cho video.
    - Chọn định dạng và nhấn `Tạo Video`.

3.  **Xử lý nhanh:**
    - Chọn thư mục nguồn và thư mục đích.
    - Chọn các tùy chọn xử lý hàng loạt.
    - Nhấn `Bắt đầu xử lý hàng loạt`.

---

## 📦 Đóng gói ứng dụng (.exe)

Để tự đóng gói ứng dụng, bạn cần `pyinstaller`.

1.  Cài đặt: `pip install pyinstaller`
2.  Tạo thư mục `binaries` và đặt `ffmpeg.exe`, `ffprobe.exe` vào trong đó.
3.  Chạy lệnh sau từ thư mục gốc dự án:
    ```bash
    pyinstaller --name "VideoCreatorApp" --onefile --windowed --icon="path/to/your/icon.ico" --add-binary "binaries/ffmpeg.exe;." --add-binary "binaries/ffprobe.exe;." VideoCreatorApp.py
    ```
4.  Ứng dụng hoàn chỉnh của bạn sẽ nằm trong thư mục `dist`.

---

## 🤝 Đóng góp

Mọi ý kiến đóng góp đều được hoan nghênh! Vui lòng tạo một [Pull Request](https://github.com/your-username/your-repo/pulls) hoặc mở một [Issue](https://github.com/your-username/your-repo/issues) để thảo luận về những thay đổi bạn muốn thực hiện.

---

## 📝 Giấy phép

Dự án này được cấp phép theo **Giấy phép MIT**. Xem file `LICENSE` để biết thêm chi tiết.