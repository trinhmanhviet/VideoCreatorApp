import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import subprocess
import threading
import os
import sys
import re

# --- Lớp ứng dụng chính ---
class FfmpegGuiApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bộ công cụ FFMPEG")
        self.geometry("650x680") # Tăng chiều cao cửa sổ
        self.resizable(False, False)

        # --- Cấu hình style ---
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", padding=5, font=("Helvetica", 10))
        style.configure("TButton", padding=5, font=("Helvetica", 10, "bold"))
        style.configure("TEntry", padding=5, font=("Helvetica", 10))
        style.configure("TCombobox", padding=5, font=("Helvetica", 10))
        style.configure("Status.TLabel", font=("Helvetica", 9, "italic"))
        style.configure("Open.TButton", font=("Helvetica", 8))
        style.configure("TLabelframe.Label", font=("Helvetica", 11, "bold"))

        # --- Biến chung ---
        self.active_thread = None
        self.check_ffmpeg_tools()

        # --- Tạo giao diện chính ---
        self.create_widgets()

    def check_ffmpeg_tools(self):
        """Kiểm tra sự tồn tại của FFMPEG và FFPROBE khi khởi động."""
        if not self.is_tool_installed("ffmpeg"):
            messagebox.showerror("Lỗi FFMPEG", "Không tìm thấy FFMPEG. Vui lòng cài đặt và thêm vào PATH.")
            self.destroy(); return
        if not self.is_tool_installed("ffprobe"):
            messagebox.showerror("Lỗi FFPROBE", "Không tìm thấy FFPROBE. Vui lòng kiểm tra lại cài đặt FFMPEG.")
            self.destroy(); return

    def is_tool_installed(self, tool_name):
        """Kiểm tra một công cụ có tồn tại trong PATH không."""
        command = "where" if sys.platform == "win32" else "which"
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run([command, tool_name], check=True, capture_output=True, startupinfo=startupinfo)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def create_widgets(self):
        """Tạo các thành phần giao diện chính, bao gồm cả các tab."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_global_drop)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(expand=True, fill="both")

        self.video_tab = ttk.Frame(self.notebook, padding="10")
        self.audio_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.video_tab, text='  Tạo Video  ')
        self.notebook.add(self.audio_tab, text='  Sửa Nhạc  ')

        self.create_video_creator_tab(self.video_tab)
        self.create_music_edit_tab(self.audio_tab)

    # ======================================================================
    # --- TAB 1: TẠO VIDEO ---
    # ======================================================================
    def create_video_creator_tab(self, parent_tab):
        self.video_image_path = tk.StringVar()
        self.video_audio_path = tk.StringVar()

        image_frame = ttk.LabelFrame(parent_tab, text="1. Chọn file ảnh", padding="10")
        image_frame.pack(fill="x", pady=5, padx=5)
        self.video_image_entry = ttk.Entry(image_frame, textvariable=self.video_image_path)
        self.video_image_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(image_frame, text="Duyệt...", command=lambda: self.browse_file(self.video_image_path, "image")).pack(side="left")

        audio_frame = ttk.LabelFrame(parent_tab, text="2. Chọn file âm thanh", padding="10")
        audio_frame.pack(fill="x", pady=5, padx=5)
        self.video_audio_entry = ttk.Entry(audio_frame, textvariable=self.video_audio_path)
        self.video_audio_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(audio_frame, text="Duyệt...", command=lambda: self.browse_file(self.video_audio_path, "audio")).pack(side="left")

        action_frame = ttk.Frame(parent_tab, padding="10")
        action_frame.pack(fill="x", pady=10, padx=5)
        ttk.Label(action_frame, text="Định dạng video:").pack(side="left", padx=(0, 10))
        self.video_format_combo = ttk.Combobox(action_frame, values=[".mp4", ".mkv", ".avi", ".mov"], state="readonly", width=10)
        self.video_format_combo.set(".mp4")
        self.video_format_combo.pack(side="left", padx=(0, 20))
        self.video_create_btn = ttk.Button(action_frame, text="Tạo Video", command=self.start_video_creation_thread)
        self.video_create_btn.pack(side="right")

        self.video_progress_bar = ttk.Progressbar(parent_tab, orient="horizontal", length=100, mode="determinate")
        self.video_progress_bar.pack(fill="x", pady=5, padx=5)

        status_frame = ttk.Frame(parent_tab)
        status_frame.pack(fill="x", pady=(5, 0), padx=5)
        self.video_status_label = ttk.Label(status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w")
        self.video_status_label.pack(side="left", fill="x", expand=True)
        self.video_open_button = ttk.Button(status_frame, text="Mở thư mục", style="Open.TButton")
        
        ttk.Label(parent_tab, text="💡 Mẹo: Kéo và thả file ảnh/nhạc vào bất cứ đâu trong cửa sổ này.", style="Status.TLabel", anchor="center").pack(fill="x", pady=10)

    # ======================================================================
    # --- TAB 2: SỬA NHẠC ---
    # ======================================================================
    def create_music_edit_tab(self, parent_tab):
        self.audio_edit_path = tk.StringVar()
        self.audio_normalize = tk.BooleanVar()
        self.audio_noise_reduce = tk.BooleanVar()

        input_frame = ttk.LabelFrame(parent_tab, text="1. Chọn file âm thanh", padding="10")
        input_frame.pack(fill="x", pady=5, padx=5)
        self.audio_edit_entry = ttk.Entry(input_frame, textvariable=self.audio_edit_path)
        self.audio_edit_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Duyệt...", command=lambda: self.browse_file(self.audio_edit_path, "audio")).pack(side="left")

        options_frame = ttk.LabelFrame(parent_tab, text="2. Tùy chọn chỉnh sửa", padding="10")
        options_frame.pack(fill="x", pady=10, padx=5)

        speed_frame = ttk.Frame(options_frame)
        speed_frame.pack(fill="x", pady=5)
        ttk.Label(speed_frame, text="Tốc độ:", width=15).pack(side="left")
        self.speed_scale = ttk.Scale(speed_frame, from_=0.5, to=2.0, orient="horizontal", command=lambda v: self.speed_label.config(text=f"{float(v):.2f}x"))
        self.speed_scale.set(1.0)
        self.speed_scale.pack(side="left", fill="x", expand=True)
        self.speed_label = ttk.Label(speed_frame, text="1.00x", width=7)
        self.speed_label.pack(side="left", padx=(10, 0))

        pitch_frame = ttk.Frame(options_frame)
        pitch_frame.pack(fill="x", pady=5)
        ttk.Label(pitch_frame, text="Cao độ (Pitch):", width=15).pack(side="left")
        self.pitch_scale = ttk.Scale(pitch_frame, from_=-12, to=12, orient="horizontal", command=lambda v: self.pitch_label.config(text=f"{int(float(v))} nửa cung"))
        self.pitch_scale.set(0)
        self.pitch_scale.pack(side="left", fill="x", expand=True)
        self.pitch_label = ttk.Label(pitch_frame, text="0 nửa cung", width=12)
        self.pitch_label.pack(side="left", padx=(10, 0))

        misc_frame = ttk.Frame(options_frame)
        misc_frame.pack(fill="x", pady=8)
        ttk.Checkbutton(misc_frame, text="Chuẩn hóa âm lượng (Normalize)", variable=self.audio_normalize).pack(anchor="w")
        ttk.Checkbutton(misc_frame, text="Giảm tiếng ồn (Noise Reduction)", variable=self.audio_noise_reduce).pack(anchor="w", pady=(5,0))
        
        # --- TÙY CHỌN THÊM NHIỄU MỚI ---
        noise_frame = ttk.LabelFrame(options_frame, text="Thêm nhiễu (Generate Noise)", padding="10")
        noise_frame.pack(fill="x", pady=(10, 5))

        noise_type_frame = ttk.Frame(noise_frame)
        noise_type_frame.pack(fill="x", pady=2)
        ttk.Label(noise_type_frame, text="Loại nhiễu:", width=15).pack(side="left")
        self.noise_type_combo = ttk.Combobox(noise_type_frame, values=["Không", "Nhiễu trắng", "Nhiễu hồng", "Nhiễu nâu"], state="readonly")
        self.noise_type_combo.set("Không")
        self.noise_type_combo.pack(side="left", fill="x", expand=True)

        noise_amp_frame = ttk.Frame(noise_frame)
        noise_amp_frame.pack(fill="x", pady=2)
        ttk.Label(noise_amp_frame, text="Cường độ:", width=15).pack(side="left")
        self.noise_amp_scale = ttk.Scale(noise_amp_frame, from_=0.0, to=1.0, orient="horizontal", command=lambda v: self.noise_amp_label.config(text=f"{float(v):.2f}"))
        self.noise_amp_scale.set(0.1)
        self.noise_amp_scale.pack(side="left", fill="x", expand=True)
        self.noise_amp_label = ttk.Label(noise_amp_frame, text="0.10", width=7)
        self.noise_amp_label.pack(side="left", padx=(10, 0))
        # --- KẾT THÚC TÙY CHỌN MỚI ---

        self.audio_process_btn = ttk.Button(parent_tab, text="Xử lý & Lưu", command=self.start_audio_processing_thread)
        self.audio_process_btn.pack(pady=10)

        self.audio_progress_bar = ttk.Progressbar(parent_tab, orient="horizontal", length=100, mode="determinate")
        self.audio_progress_bar.pack(fill="x", pady=5, padx=5)
        
        audio_status_frame = ttk.Frame(parent_tab)
        audio_status_frame.pack(fill="x", pady=(5, 0), padx=5)
        self.audio_status_label = ttk.Label(audio_status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w")
        self.audio_status_label.pack(side="left", fill="x", expand=True)
        self.audio_open_button = ttk.Button(audio_status_frame, text="Mở thư mục", style="Open.TButton")

    # ======================================================================
    # --- HÀM CHUNG & XỬ LÝ SỰ KIỆN ---
    # ======================================================================
    def browse_file(self, path_var, file_type):
        types = {"image": [("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")], "audio": [("Audio Files", "*.mp3 *.wav *.aac *.flac"), ("All files", "*.*")]}
        path = filedialog.askopenfilename(title=f"Chọn một file {file_type}", filetypes=types.get(file_type))
        if path: path_var.set(path)

    def handle_global_drop(self, event):
        filepath = self.tk.splitlist(event.data)[0]
        if not os.path.isfile(filepath): return
        file_ext = os.path.splitext(filepath)[1].lower()
        current_tab = self.notebook.index(self.notebook.select())
        if file_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
            self.video_image_path.set(filepath)
            self.video_status_label.config(text=f"Đã nhận file ảnh: {os.path.basename(filepath)}")
            self.notebook.select(self.video_tab)
        elif file_ext in ['.mp3', '.wav', '.aac', '.flac']:
            if current_tab == 0:
                self.video_audio_path.set(filepath)
                self.video_status_label.config(text=f"Đã nhận file âm thanh: {os.path.basename(filepath)}")
            else:
                self.audio_edit_path.set(filepath)
                self.audio_status_label.config(text=f"Đã nhận file âm thanh: {os.path.basename(filepath)}")
        else:
            messagebox.showwarning("Loại file không được hỗ trợ", f"Không thể xử lý file có định dạng '{file_ext}'.")

    def get_file_duration(self, file_path):
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        try:
            startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(command, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            return float(result.stdout.strip())
        except Exception: return None

    def open_folder_and_select_file(self, path):
        if not os.path.exists(path): messagebox.showerror("Lỗi", "File không tồn tại."); return
        try:
            if sys.platform == "win32": subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif sys.platform == "darwin": subprocess.run(['open', '-R', path])
            else: subprocess.run(['xdg-open', os.path.dirname(path)])
        except Exception as e: messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")

    # ======================================================================
    # --- LOGIC XỬ LÝ CỦA TAB TẠO VIDEO ---
    # ======================================================================
    def start_video_creation_thread(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng đợi."); return
        image_file, audio_file = self.video_image_path.get(), self.video_audio_path.get()
        if not all([image_file, audio_file, os.path.exists(image_file), os.path.exists(audio_file)]): messagebox.showerror("Thiếu thông tin hoặc file không tồn tại", "Vui lòng chọn file ảnh và âm thanh hợp lệ."); return
        default_filename = os.path.splitext(os.path.basename(audio_file))[0]
        output_format = self.video_format_combo.get()
        output_path = filedialog.asksaveasfilename(initialfile=default_filename, title="Lưu video", defaultextension=output_format, filetypes=[(f"{output_format.upper()} files", f"*{output_format}"), ("All files", "*.*")])
        if not output_path: self.video_status_label.config(text="Đã hủy tạo video."); return
        self.active_thread = threading.Thread(target=self.create_video_process, args=(image_file, audio_file, output_path)); self.active_thread.daemon = True; self.active_thread.start()

    def create_video_process(self, image_file, audio_file, output_path):
        self.video_create_btn.config(state="disabled")
        self.video_open_button.pack_forget()
        self.video_progress_bar['value'] = 0
        self.video_status_label.config(text="Đang lấy thông tin file...")
        self.update_idletasks()
        total_duration = self.get_file_duration(audio_file)
        if total_duration is None: self.video_status_label.config(text="Lỗi: Không thể đọc thời lượng file."); self.video_create_btn.config(state="normal"); return
        self.video_status_label.config(text="Bắt đầu tạo video...")
        command = ['ffmpeg', '-loop', '1', '-i', image_file, '-i', audio_file, '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', '-y', output_path]
        try:
            self.run_ffmpeg_process(command, total_duration, self.video_progress_bar, self.video_status_label, output_path, self.video_open_button)
        except Exception as e:
            error_output = e.stdout if hasattr(e, 'stdout') else str(e)
            print(f"FFMPEG Error:\n{error_output}")
            self.video_status_label.config(text="Tạo video thất bại! Kiểm tra console.")
            messagebox.showerror("Lỗi FFMPEG", f"Quá trình tạo video thất bại. Chi tiết:\n{error_output[:500]}...")
        finally: self.video_create_btn.config(state="normal")

    # ======================================================================
    # --- LOGIC XỬ LÝ CỦA TAB SỬA NHẠC ---
    # ======================================================================
    def start_audio_processing_thread(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện. Vui lòng đợi."); return
        audio_file = self.audio_edit_path.get()
        if not (audio_file and os.path.exists(audio_file)): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh hợp lệ."); return
        
        speed, pitch, normalize, noise_reduce = self.speed_scale.get(), self.pitch_scale.get(), self.audio_normalize.get(), self.audio_noise_reduce.get()
        noise_type, noise_amp = self.noise_type_combo.get(), self.noise_amp_scale.get()

        if speed == 1.0 and pitch == 0 and not normalize and not noise_reduce and noise_type == "Không":
            messagebox.showinfo("Thông tin", "Bạn chưa chọn tùy chọn chỉnh sửa nào."); return
            
        default_filename = os.path.splitext(os.path.basename(audio_file))[0] + "_edited"
        file_extension = os.path.splitext(audio_file)[1]
        output_path = filedialog.asksaveasfilename(initialfile=default_filename, title="Lưu file âm thanh đã sửa", defaultextension=file_extension, filetypes=[("Audio Files", f"*{file_extension}"), ("All files", "*.*")])
        if not output_path: self.audio_status_label.config(text="Đã hủy xử lý."); return
        
        self.active_thread = threading.Thread(target=self.process_audio_file, args=(audio_file, output_path, speed, pitch, normalize, noise_reduce, noise_type, noise_amp))
        self.active_thread.daemon = True; self.active_thread.start()

    def process_audio_file(self, input_path, output_path, speed, pitch, normalize, noise_reduce, noise_type, noise_amp):
        self.audio_process_btn.config(state="disabled")
        self.audio_open_button.pack_forget()
        self.audio_progress_bar['value'] = 0
        self.audio_status_label.config(text="Đang lấy thông tin file...")
        self.update_idletasks()

        total_duration = self.get_file_duration(input_path)
        if total_duration is None: self.audio_status_label.config(text="Lỗi: Không thể đọc thời lượng file."); self.audio_process_btn.config(state="normal"); return

        self.audio_status_label.config(text="Bắt đầu xử lý âm thanh...")
        
        command = ['ffmpeg', '-i', input_path]
        main_audio_chain = []
        
        if speed != 1.0:
            temp_speed = speed
            # The atempo filter only accepts values between 0.5 and 100.0.
            # To achieve speeds slower than 0.5, we apply the filter multiple times.
            while temp_speed < 0.5:
                main_audio_chain.append("atempo=0.5")
                temp_speed /= 0.5
            main_audio_chain.append(f"atempo={temp_speed}")

        if pitch != 0:
            pitch_factor = 2**(pitch / 12.0)
            main_audio_chain.append(f"asetrate=44100*{pitch_factor},aresample=44100")
        
        if normalize:
            main_audio_chain.append("dynaudnorm")
        
        if noise_reduce:
            main_audio_chain.append("anlmdn")

        if noise_type != "Không":
            noise_color_map = {"Nhiễu trắng": "white", "Nhiễu hồng": "pink", "Nhiễu nâu": "brown"}
            noise_color = noise_color_map[noise_type]
            
            main_chain_str = ",".join(main_audio_chain) if main_audio_chain else "anull"
            
            filter_complex_graph = (
                f"[0:a]{main_chain_str}[main_audio];"
                f"anoisesrc=color={noise_color}:a={noise_amp}:d={total_duration}[noise_audio];"
                f"[main_audio][noise_audio]amix=inputs=2:duration=first[out]"
            )
            command.extend(['-filter_complex', filter_complex_graph, '-map', '[out]'])
        else:
            if main_audio_chain: command.extend(['-af', ",".join(main_audio_chain)])
        
        command.extend(['-y', output_path])

        try:
            output_duration = total_duration / speed if speed != 0 else total_duration
            self.run_ffmpeg_process(command, output_duration, self.audio_progress_bar, self.audio_status_label, output_path, self.audio_open_button)
        except Exception as e:
            error_output = e.stdout if hasattr(e, 'stdout') else str(e)
            print(f"FFMPEG Error:\n{error_output}")
            self.audio_status_label.config(text="Xử lý thất bại! Kiểm tra console.")
            messagebox.showerror("Lỗi FFMPEG", f"Quá trình xử lý thất bại. Chi tiết:\n{error_output[:500]}...")
        finally: self.audio_process_btn.config(state="normal")

    # ======================================================================
    # --- TIẾN TRÌNH FFMPEG CHUNG ---
    # ======================================================================
    def run_ffmpeg_process(self, command, total_duration, progress_bar, status_label, output_path, open_button):
        startupinfo = None
        if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', startupinfo=startupinfo)
        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        for line in process.stdout:
            match = time_pattern.search(line)
            if match and total_duration > 0:
                h, m, s, ms = map(int, match.groups())
                current_time = h * 3600 + m * 60 + s + ms / 100
                progress = (current_time / total_duration) * 100
                progress_bar['value'] = min(progress, 100)
                status_label.config(text=f"Đang xử lý... {int(progress_bar['value'])}%")
                self.update_idletasks()
        process.wait()
        if process.returncode == 0:
            progress_bar['value'] = 100
            status_label.config(text="Hoàn thành!")
            open_button.config(command=lambda: self.open_folder_and_select_file(output_path))
            open_button.pack(side="right", padx=(5, 0))
        else:
            raise subprocess.CalledProcessError(process.returncode, command, output=process.stdout)

# --- Chạy ứng dụng ---
if __name__ == "__main__":
    try: import tkinterdnd2
    except ImportError: print("="*50 + "\nVui lòng chạy 'pip install tkinterdnd2' để cài đặt thư viện kéo-thả.\n" + "="*50); sys.exit(1)
    app = FfmpegGuiApp()
    app.mainloop()
