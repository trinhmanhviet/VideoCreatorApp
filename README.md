🎼 Bộ công cụ Media (VideoCreatorApp)
Một ứng dụng desktop đa năng dành cho Windows, giúp bạn dễ dàng chỉnh sửa file âm thanh, tạo video từ ảnh và nhạc, cũng như xử lý hàng loạt file media một cách nhanh chóng. Ứng dụng được xây dựng bằng Python với giao diện đồ họa thân thiện.

(Mẹo: Bạn nên chụp một bức ảnh màn hình của ứng dụng và thay thế dòng dưới đây để README trông hấp dẫn hơn!)

✨ Tính năng chính
Ứng dụng được chia thành 3 tab chức năng chính:

1. 🎹 Sửa Nhạc
Hiển thị dạng sóng: Trực quan hóa file âm thanh trên một canvas để dễ dàng điều hướng.

Phát nhạc cơ bản: Hỗ trợ Play, Pause, Stop và tua nhạc bằng cách nhấp chuột trực tiếp lên dạng sóng.

Áp dụng hiệu ứng:

Thay đổi Tốc độ (Speed) và Nhịp độ (Tempo).

Điều chỉnh Cao độ (Pitch) theo từng nửa cung.

Chuẩn hóa âm lượng (Normalize) để âm thanh đồng đều.

Giảm tiếng ồn (Noise Reduction) cơ bản.

Thêm các loại nhiễu nền (Trắng, Hồng, Nâu) với cường độ tùy chỉnh.

Xuất hàng loạt: Chọn nhiều file và xuất tất cả chúng với cùng một bộ hiệu ứng.

2. 🎬 Tạo Video
Đơn giản và hiệu quả: Tạo video nhanh chóng từ một file ảnh và một file âm thanh.

Danh sách ảnh trực quan: Thêm nhiều ảnh vào danh sách, xem dưới dạng thumbnail và chọn ảnh nền cho video.

Hỗ trợ nhiều định dạng: Dễ dàng tạo video với các định dạng phổ biến như .mp4, .mkv, .mov...

Tối ưu cho ảnh tĩnh: Sử dụng các tùy chọn FFMPEG để đảm bảo chất lượng video tốt nhất cho nội dung là ảnh tĩnh.

3. ⚡ Xử lý nhanh
Xử lý cả thư mục: Chọn một thư mục nguồn chứa hàng loạt file âm thanh để áp dụng hiệu ứng.

Các mẫu thiết lập sẵn:

Tăng/giảm tốc độ nhẹ.

Thêm nhiễu trắng siêu nhẹ.

Chuẩn hóa âm lượng.

Tự động hóa: Tự động xử lý tất cả các file và lưu vào một thư mục đầu ra riêng biệt, giúp tiết kiệm tối đa thời gian.

🛠️ Yêu cầu
Dành cho người dùng (Chạy file .exe)
Hệ điều hành Windows 7, 10, 11.

Không cần cài đặt gì thêm nếu bạn tải bản đã được đóng gói.

Dành cho lập trình viên (Chạy từ mã nguồn)
Python 3.8+

FFmpeg & FFprobe: Cần được cài đặt và thêm vào biến môi trường PATH của hệ thống. Bạn có thể tải về từ trang web chính thức của FFmpeg.

Các thư viện Python:

pygame
Pillow
numpy
tkinterdnd2-universal
pyinstaller (để đóng gói)
Bạn có thể cài đặt tất cả bằng lệnh: pip install pygame Pillow numpy tkinterdnd2-universal

🚀 Cài đặt và Sử dụng
Cách 1: Sử dụng file .exe (Khuyến khích)
Truy cập mục Releases trên trang GitHub của dự án.

Tải về file VideoCreatorApp.exe mới nhất.

Chạy file vừa tải về để bắt đầu sử dụng.

Cách 2: Chạy từ mã nguồn
Clone repository này về máy của bạn:

Bash

git clone https://github.com/your-username/VideoCreatorApp.git
Đảm bảo bạn đã cài đặt FFmpeg và các thư viện Python được liệt kê ở trên.

Di chuyển vào thư mục dự án:

Bash

cd VideoCreatorApp
Chạy ứng dụng:

Bash

python VideoCreatorApp.py
📦 Đóng gói thành file .exe
Nếu bạn muốn tự đóng gói ứng dụng từ mã nguồn, hãy làm theo các bước sau:

Cài đặt PyInstaller: pip install pyinstaller

Tạo một thư mục con tên là binaries và sao chép ffmpeg.exe và ffprobe.exe vào đó.

Chạy lệnh sau từ thư mục gốc của dự án:

Bash

pyinstaller --name "VideoCreatorApp" --onefile --windowed --icon="path/to/your/icon.ico" --add-binary "binaries/ffmpeg.exe;." --add-binary "binaries/ffprobe.exe;." VideoCreatorApp.py
File .exe hoàn chỉnh sẽ nằm trong thư mục dist.

✍️ Tác giả
(Điền tên của bạn vào đây)

Cảm ơn bạn đã sử dụng ứng dụng! Nếu có bất kỳ câu hỏi hoặc góp ý nào, vui lòng tạo một "Issue" trên GitHub.