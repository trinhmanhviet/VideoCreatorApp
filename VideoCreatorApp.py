import tkinter as tk
from tkinter import ttk, filedialog, messagebox, TclError
from tkinterdnd2 import DND_FILES, TkinterDnD
import subprocess
import threading
import os
import sys
import re
import atexit
import shutil
import time
from collections import deque

# Kiểm tra và yêu cầu cài đặt các thư viện cần thiết
try:
    import pygame
    import pygame.sndarray
except ImportError:
    print("="*50)
    print("Thư viện 'pygame' chưa được cài đặt.")
    print("Vui lòng chạy lệnh sau trong terminal để cài đặt:")
    print("pip install pygame")
    print("="*50)
    sys.exit(1)

try:
    from PIL import Image, ImageTk
except ImportError:
    print("="*50)
    print("Thư viện 'Pillow' chưa được cài đặt.")
    print("Vui lòng chạy lệnh sau trong terminal để cài đặt:")
    print("pip install Pillow")
    print("="*50)
    sys.exit(1)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("="*50)
    print("CẢNH BÁO: Thư viện 'numpy' chưa được cài đặt.")
    print("Vui lòng chạy 'pip install numpy' để có thể hiển thị dạng sóng.")
    print("Chức năng vẽ dạng sóng sẽ bị tắt.")
    print("="*50)


# --- Thư mục tạm để lưu file preview ---
TEMP_DIR = "_audiotoolkit_temp"

def cleanup_temp_dir():
    """Xóa thư mục tạm khi thoát ứng dụng."""
    try:
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
    except PermissionError:
        print(f"Không thể xóa thư mục tạm {TEMP_DIR} vì đang được sử dụng.")
    except Exception as e:
        print(f"Lỗi trong quá trình dọn dẹp: {e}")


atexit.register(cleanup_temp_dir)

# --- Lớp ứng dụng chính ---
class FfmpegGuiApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bộ công cụ Media")
        self.geometry("950x800")
        self.configure(bg="#ECECEC")

        # Khởi tạo Pygame Mixer
        pygame.init()
        pygame.mixer.init()

        # Tạo thư mục tạm
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)

        # --- Cấu hình style ---
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", padding=5, font=("Segoe UI", 9), background="#ECECEC")
        style.configure("TButton", padding=5, font=("Segoe UI", 9))
        style.configure("TEntry", padding=5, font=("Segoe UI", 9))
        style.configure("TCombobox", padding=5, font=("Segoe UI", 9))
        style.configure("Status.TLabel", font=("Segoe UI", 9, "italic"), background="#ECECEC")
        style.configure("Open.TButton", font=("Segoe UI", 8))
        style.configure("TLabelframe", background="#ECECEC")
        style.configure("TLabelframe.Label", font=("Segoe UI", 10, "bold"), background="#ECECEC", foreground="#333")
        style.configure("TCheckbutton", background="#ECECEC")
        style.configure("TScale", background="#ECECEC")
        style.configure("Treeview", rowheight=25)
        style.map("Treeview", background=[('selected', '#E0E8F0')], foreground=[('selected', 'black')])
        
        # --- Biến chung ---
        self.active_thread = None
        self.image_thumbnails = [] 
        self.seek_offset = 0.0
        self.waveform_data = None
        self.check_ffmpeg_tools()

        # --- Tạo giao diện chính ---
        self.create_main_layout()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.stop_audio()
        self.destroy()

    def check_ffmpeg_tools(self):
        if not self.is_tool_installed("ffmpeg") or not self.is_tool_installed("ffprobe"):
            messagebox.showerror("Lỗi", "Không tìm thấy FFMPEG/FFPROBE. Vui lòng cài đặt và thêm vào PATH hệ thống.")
            self.after(100, self.destroy)

    def is_tool_installed(self, tool_name):
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

    def create_main_layout(self):
        self.create_menu()
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_global_drop)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)
        self.audio_editor_tab = ttk.Frame(self.notebook, padding="10")
        self.video_creator_tab = ttk.Frame(self.notebook, padding="10")
        self.quick_process_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.audio_editor_tab, text='  Sửa Nhạc  ')
        self.notebook.add(self.video_creator_tab, text='  Tạo Video  ')
        self.notebook.add(self.quick_process_tab, text='  Xử lý nhanh  ')
        self.create_audio_editor_tab(self.audio_editor_tab)
        self.create_video_creator_tab(self.video_creator_tab)
        self.create_quick_process_tab(self.quick_process_tab)

    def create_menu(self):
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Thêm file âm thanh...", command=self.browse_main_audio_file)
        file_menu.add_command(label="Thêm thư mục âm thanh...", command=self.browse_main_audio_folder)
        file_menu.add_command(label="Xuất Audio đã chọn...", command=self.export_audio)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.on_closing)
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())

    # ======================================================================
    # --- TAB 1: SỬA NHẠC (với CANVAS) ---
    # ======================================================================
    def create_audio_editor_tab(self, parent_tab):
        self.preview_file_path = None
        self.undo_stack = []
        self.redo_stack = []
        self.is_preview_dirty = True
        self.is_paused = False
        self.playback_update_id = None
        self.is_seeking = False
        self.audio_file_paths = {}

        paned_window = ttk.PanedWindow(parent_tab, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both")

        # Cột trái: Danh sách file
        left_pane = ttk.Frame(paned_window, width=300)
        paned_window.add(left_pane, weight=1)
        
        list_lf = ttk.LabelFrame(left_pane, text="Danh sách file", padding=5)
        list_lf.pack(expand=True, fill="both")
        
        self.audio_tree = ttk.Treeview(list_lf, columns=("filename",), show="headings")
        self.audio_tree.heading("filename", text="Tên file")
        self.audio_tree.column("filename", anchor="w")
        self.audio_tree.tag_configure('checked', image=self.get_check_image(True))
        self.audio_tree.tag_configure('unchecked', image=self.get_check_image(False))
        self.audio_tree.bind("<Button-1>", self.on_audio_tree_click)
        self.audio_tree.bind("<<TreeviewSelect>>", self.on_audio_tree_select)
        
        scrollbar = ttk.Scrollbar(list_lf, orient=tk.VERTICAL, command=self.audio_tree.yview)
        self.audio_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.audio_tree.pack(expand=True, fill="both")
        
        list_buttons_frame = ttk.Frame(left_pane)
        list_buttons_frame.pack(fill="x", pady=5)
        ttk.Button(list_buttons_frame, text="Chọn tất cả", command=lambda: self.toggle_all_audio_checks(True)).pack(side="left", expand=True, fill="x")
        ttk.Button(list_buttons_frame, text="Bỏ chọn", command=lambda: self.toggle_all_audio_checks(False)).pack(side="left", expand=True, fill="x")
        ttk.Button(list_buttons_frame, text="Đảo ngược", command=self.invert_audio_checks).pack(side="left", expand=True, fill="x")

        # Cột phải: Điều khiển
        right_pane = ttk.Frame(paned_window)
        paned_window.add(right_pane, weight=3)

        top_frame = ttk.Frame(right_pane)
        top_frame.pack(side="top", fill="x")

        toolbar_frame = ttk.Frame(top_frame, style="TFrame", relief="groove", borderwidth=1)
        toolbar_frame.pack(side="top", fill="x", padx=5, pady=5)
        self.create_audio_toolbar(toolbar_frame)
        
        # --- WAVEFORM CANVAS ---
        waveform_lf = ttk.LabelFrame(top_frame, text="Dạng sóng", padding=5)
        waveform_lf.pack(fill="x", expand=True, padx=5, pady=5)
        
        self.waveform_canvas = tk.Canvas(waveform_lf, bg="#2c3e50", height=120, highlightthickness=0)
        self.waveform_canvas.pack(fill="x", expand=True)
        self.waveform_canvas.bind("<Configure>", self.on_canvas_resize)
        self.waveform_canvas.bind("<Button-1>", self.on_waveform_click)
        self.playhead = self.waveform_canvas.create_line(0, 0, 0, 120, fill="#3498db", width=2, state=tk.HIDDEN)


        player_frame = ttk.Frame(top_frame)
        player_frame.pack(fill="x", padx=10, pady=(0, 5))
        self.current_time_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.current_time_label.pack(side="left")
        
        # Thanh trượt bây giờ là phụ, chỉ để hiển thị
        self.seek_var = tk.DoubleVar()
        self.seek_bar = ttk.Scale(player_frame, from_=0, to=100, orient="horizontal", variable=self.seek_var)
        self.seek_bar.pack(side="left", fill="x", expand=True, padx=5)

        self.total_duration_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.total_duration_label.pack(side="left")
        
        # --- KHU VỰC HIỆU ỨNG ---
        options_frame = ttk.LabelFrame(right_pane, text="Hiệu ứng âm thanh", padding=10)
        options_frame.pack(expand=True, fill="both", padx=5)
        
        self.speed_var = self._create_slider_entry_pair(options_frame, "Tốc độ (Speed):", 0.25, 4.0, 1.0, "x", precision=5)
        self.tempo_var = self._create_slider_entry_pair(options_frame, "Nhịp độ (Tempo):", 0.5, 2.0, 1.0, "x", precision=5)
        self.pitch_var = self._create_slider_entry_pair(options_frame, "Cao độ (Pitch):", -12.0, 12.0, 0.0, "nửa cung", precision=5)
        
        misc_frame = ttk.Frame(options_frame); misc_frame.pack(fill="x", pady=8, padx=5)
        self.audio_normalize = tk.BooleanVar(); self.audio_noise_reduce = tk.BooleanVar()
        self.audio_normalize.trace_add("write", self.mark_preview_as_dirty)
        self.audio_noise_reduce.trace_add("write", self.mark_preview_as_dirty)
        ttk.Checkbutton(misc_frame, text="Chuẩn hóa âm lượng (Normalize)", variable=self.audio_normalize).pack(anchor="w")
        ttk.Checkbutton(misc_frame, text="Giảm tiếng ồn (Noise Reduction)", variable=self.audio_noise_reduce).pack(anchor="w", pady=(5,0))
        
        noise_frame = ttk.LabelFrame(options_frame, text="Thêm nhiễu", padding="10")
        noise_frame.pack(fill="x", pady=(10, 5), padx=5)
        noise_type_frame = ttk.Frame(noise_frame); noise_type_frame.pack(fill="x", pady=2)
        ttk.Label(noise_type_frame, text="Loại nhiễu:", width=15).pack(side="left")
        self.noise_type_combo = ttk.Combobox(noise_type_frame, values=["Không", "Nhiễu trắng", "Nhiễu hồng", "Nhiễu nâu"], state="readonly")
        self.noise_type_combo.set("Không"); self.noise_type_combo.pack(side="left", fill="x", expand=True)
        self.noise_type_combo.bind("<<ComboboxSelected>>", self.mark_preview_as_dirty)
        self.noise_amp_var = self._create_slider_entry_pair(noise_frame, "Cường độ:", 0.0, 1.0, 0.1, precision=5)
        
        ttk.Button(right_pane, text="Xuất Audio đã chọn...", command=self.export_audio).pack(pady=10)

        bottom_frame = ttk.Frame(right_pane, style="TFrame")
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        self.create_audio_status_bar(bottom_frame)

        self.save_state()

    def get_check_image(self, checked):
        if not hasattr(self, "_check_images"):
            self._check_images = {}
        if checked not in self._check_images:
            im = Image.new("RGBA", (16, 16), (0,0,0,0))
            for i in range(2, 14):
                im.putpixel((i, 2), (0,0,0,255)); im.putpixel((i, 13), (0,0,0,255))
                im.putpixel((2, i), (0,0,0,255)); im.putpixel((13, i), (0,0,0,255))
            if checked:
                for i in range(3):
                    im.putpixel((5+i, 8+i), (0,0,0,255)); im.putpixel((6+i, 8+i), (0,0,0,255))
                for i in range(4):
                    im.putpixel((7+i, 10-i), (0,0,0,255)); im.putpixel((8+i, 10-i), (0,0,0,255))
            self._check_images[checked] = ImageTk.PhotoImage(im)
        return self._check_images[checked]

    def create_audio_toolbar(self, parent):
        self.play_pause_btn = ttk.Button(parent, text="▶ Play", width=8, command=self.toggle_play_pause)
        self.play_pause_btn.pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="■ Stop", width=8, command=self.stop_audio).pack(side="left", padx=2, pady=5)
        ttk.Separator(parent, orient='vertical').pack(side='left', fill='y', padx=10, pady=5)
        ttk.Button(parent, text="↩ Undo", command=self.undo).pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="↪ Redo", command=self.redo).pack(side="left", padx=2, pady=5)

    def create_audio_status_bar(self, parent):
        self.audio_progress_bar = ttk.Progressbar(parent, orient="horizontal", length=100, mode="determinate")
        self.audio_progress_bar.pack(fill="x", pady=5, padx=5)
        status_frame = ttk.Frame(parent); status_frame.pack(fill="x", padx=5)
        self.audio_status_label = ttk.Label(status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w")
        self.audio_status_label.pack(side="left", fill="x", expand=True)
        self.audio_open_button = ttk.Button(status_frame, text="Mở thư mục", style="Open.TButton")
        
    def on_audio_tree_click(self, event):
        region = self.audio_tree.identify_region(event.x, event.y)
        if region == "cell":
            item_id = self.audio_tree.identify_row(event.y)
            if not item_id: return
            tags = list(self.audio_tree.item(item_id, "tags"))
            if 'checked' in tags:
                tags.remove('checked'); tags.append('unchecked')
            elif 'unchecked' in tags:
                tags.remove('unchecked'); tags.append('checked')
            self.audio_tree.item(item_id, tags=tuple(tags))
            return "break"

    def on_audio_tree_select(self, event):
        self.mark_preview_as_dirty()
        self.seek_offset = 0.0
        self.seek_var.set(0)
        self.current_time_label.config(text="00:00.0")
        self.waveform_canvas.itemconfig(self.playhead, state=tk.HIDDEN) # Ẩn playhead
        
        selected_path = self.get_selected_audio_path()
        if selected_path:
            duration = self.get_file_duration(selected_path)
            if duration is not None:
                self.seek_bar.config(to=duration)
                self.total_duration_label.config(text=self.format_time(duration))
                # Vẽ waveform cho file mới
                self.draw_waveform_from_file(selected_path)
            else:
                self.total_duration_label.config(text="--:--.-")
                self.waveform_canvas.delete("waveform")
        else:
             self.total_duration_label.config(text="00:00.0")
             self.waveform_canvas.delete("waveform")

    def get_selected_audio_path(self):
        selection = self.audio_tree.selection()
        if selection:
            item_id = selection[0]
            return self.audio_file_paths.get(item_id)
        return None

    def add_audio_files_to_list(self, file_paths):
        new_file_added = False
        for path in file_paths:
            if path not in self.audio_file_paths.values():
                filename = os.path.basename(path)
                item_id = self.audio_tree.insert("", "end", values=(filename,), tags=('unchecked',))
                self.audio_file_paths[item_id] = path
                new_file_added = True
        
        if new_file_added and len(self.audio_file_paths) == len(file_paths):
             first_item = self.audio_tree.get_children()[0]
             self.audio_tree.selection_set(first_item)
             self.audio_tree.focus(first_item)

    def add_audio_files_from_folder(self, folder_path):
        audio_files = []
        supported_exts = ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                audio_files.append(entry.path)
        
        if audio_files:
            self.add_audio_files_to_list(sorted(audio_files))
        else:
            messagebox.showinfo("Thông báo", "Không tìm thấy file audio nào trong thư mục đã chọn.", parent=self)

    def toggle_all_audio_checks(self, check_state):
        new_tag = 'checked' if check_state else 'unchecked'
        for item_id in self.audio_tree.get_children():
            self.audio_tree.item(item_id, tags=(new_tag,))

    def invert_audio_checks(self):
        for item_id in self.audio_tree.get_children():
            tags = list(self.audio_tree.item(item_id, "tags"))
            if 'checked' in tags:
                tags.remove('checked'); tags.append('unchecked')
            elif 'unchecked' in tags:
                tags.remove('unchecked'); tags.append('checked')
            self.audio_tree.item(item_id, tags=tuple(tags))
            
    def get_checked_audio_files(self):
        checked_files = []
        for item_id in self.audio_tree.get_children():
            if 'checked' in self.audio_tree.item(item_id, "tags"):
                checked_files.append(self.audio_file_paths[item_id])
        return checked_files

    def run_batch_export(self, files_to_process, output_folder):
        self.audio_progress_bar['maximum'] = len(files_to_process)
        self.audio_progress_bar['value'] = 0
        state = self.get_current_state()

        for i, input_path in enumerate(files_to_process):
            filename = os.path.basename(input_path)
            self.audio_status_label.config(text=f"Đang xử lý {i+1}/{len(files_to_process)}: {filename}")
            self.audio_progress_bar['value'] = i
            self.update_idletasks()

            output_path = os.path.join(output_folder, filename)
            command = self.build_ffmpeg_command(input_path, output_path, state)
            
            try:
                startupinfo = None
                if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                process = subprocess.run(command, check=True, capture_output=True, startupinfo=startupinfo, text=True, encoding='utf-8')
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi xử lý file {filename}:\n{e.stderr}")
                self.audio_status_label.config(text=f"Lỗi xử lý file: {filename}. Bỏ qua.")
                continue

        self.audio_progress_bar['value'] = len(files_to_process)
        self.audio_status_label.config(text=f"Hoàn thành! Đã xuất {len(files_to_process)} files.")
        messagebox.showinfo("Hoàn thành", f"Đã xuất thành công {len(files_to_process)} files.\nLưu tại: {output_folder}")
        
    # --- WAVEFORM CANVAS LOGIC ---
    def on_canvas_resize(self, event):
        """Vẽ lại waveform khi kích thước canvas thay đổi."""
        selected_path = self.get_selected_audio_path()
        if selected_path:
            self.draw_waveform_from_file(selected_path, force_redraw=True)

    def on_waveform_click(self, event):
        """Tua nhạc khi click vào canvas."""
        selected_path = self.get_selected_audio_path()
        if not selected_path: return
        
        canvas_width = self.waveform_canvas.winfo_width()
        duration = self.seek_bar.cget("to")
        
        if duration > 0:
            seek_pos = (event.x / canvas_width) * duration
            self.seek_offset = seek_pos
            self.seek_var.set(seek_pos)
            
            try:
                if pygame.mixer.music.get_busy() or self.is_paused:
                    pygame.mixer.music.play(start=self.seek_offset)
                    if self.is_paused:
                        pygame.mixer.music.pause()
                
                self.update_playhead()
                self.current_time_label.config(text=self.format_time(self.seek_offset))
            except pygame.error as e:
                print(f"Lỗi khi tua nhạc từ canvas: {e}")

    def update_playhead(self):
        """Cập nhật vị trí của playhead trên canvas."""
        duration = self.seek_bar.cget("to")
        current_pos = self.seek_var.get()
        
        if duration > 0:
            canvas_width = self.waveform_canvas.winfo_width()
            canvas_height = self.waveform_canvas.winfo_height()
            x_pos = (current_pos / duration) * canvas_width
            self.waveform_canvas.coords(self.playhead, x_pos, 0, x_pos, canvas_height)
            self.waveform_canvas.itemconfig(self.playhead, state=tk.NORMAL)
        else:
            self.waveform_canvas.itemconfig(self.playhead, state=tk.HIDDEN)

    def draw_waveform_from_file(self, audio_path, force_redraw=False):
        """Lấy dữ liệu và vẽ waveform. Sử dụng cache để tránh xử lý lại."""
        if not NUMPY_AVAILABLE:
            self.waveform_canvas.delete("all") # Xóa mọi thứ nếu không có numpy
            self.playhead = self.waveform_canvas.create_line(0, 0, 0, 120, fill="#3498db", width=2, state=tk.HIDDEN)
            self.waveform_canvas.create_text(
                self.waveform_canvas.winfo_width()/2, self.waveform_canvas.winfo_height()/2,
                text="Cài đặt 'numpy' để xem dạng sóng", fill="white", font=("Segoe UI", 10)
            )
            return

        if not force_redraw and self.waveform_data is not None:
             self.plot_waveform(self.waveform_data)
             return

        # Sử dụng thread để không làm treo giao diện khi xử lý file lớn
        thread = threading.Thread(target=self._load_and_draw_waveform, args=(audio_path,), daemon=True)
        thread.start()

    def _load_and_draw_waveform(self, audio_path):
        try:
            # Load âm thanh bằng pygame
            sound = pygame.mixer.Sound(audio_path)
            # Lấy mẫu dưới dạng mảng numpy
            samples = pygame.sndarray.samples(sound)
            if samples.ndim > 1:
                samples = samples.mean(axis=1) # Chuyển sang mono nếu là stereo
            
            # Giảm số lượng mẫu để vẽ nhanh hơn
            canvas_width = self.waveform_canvas.winfo_width()
            if canvas_width <= 0: canvas_width = 800 # Giá trị mặc định
            
            num_samples = len(samples)
            step = max(1, num_samples // (canvas_width * 2))
            
            # Lấy giá trị đỉnh (max và min) cho mỗi block
            waveform_peaks = []
            for i in range(0, num_samples, step):
                chunk = samples[i:i+step]
                if len(chunk) > 0:
                     waveform_peaks.append((np.min(chunk), np.max(chunk)))

            # Chuẩn hóa giá trị đỉnh về khoảng [-1, 1]
            max_abs_val = max(abs(p[0]) for p in waveform_peaks) + max(abs(p[1]) for p in waveform_peaks)
            if max_abs_val == 0: max_abs_val = 1
            
            self.waveform_data = [(p[0]/max_abs_val, p[1]/max_abs_val) for p in waveform_peaks]

            # Lên lịch vẽ trên main thread
            self.after(0, self.plot_waveform, self.waveform_data)

        except Exception as e:
            print(f"Lỗi khi xử lý waveform: {e}")

    def plot_waveform(self, waveform_data):
        """Vẽ dữ liệu waveform đã xử lý lên canvas."""
        self.waveform_canvas.delete("all")
        # Tạo lại playhead vì `delete("all")` đã xóa nó
        self.playhead = self.waveform_canvas.create_line(0, 0, 0, 120, fill="#3498db", width=2, state=tk.HIDDEN)

        if not waveform_data: return

        canvas_width = self.waveform_canvas.winfo_width()
        canvas_height = self.waveform_canvas.winfo_height()
        center_y = canvas_height / 2
        
        line_width = canvas_width / len(waveform_data)
        
        for i, (min_peak, max_peak) in enumerate(waveform_data):
            x = i * line_width
            y1 = center_y - (max_peak * center_y * 0.9)
            y2 = center_y - (min_peak * center_y * 0.9)
            self.waveform_canvas.create_line(x, y1, x, y2, fill="#7f8c8d", tags="waveform")
            self.waveform_canvas.create_line(x, y1, x, y2+1, fill="#95a5a6", tags="waveform") # Highlight
            
        self.update_playhead() # Cập nhật lại vị trí playhead
        
    # ======================================================================
    # --- TAB 2: TẠO VIDEO ---
    # ======================================================================
    def create_video_creator_tab(self, parent_tab):
        self.video_image_path = tk.StringVar()
        self.video_audio_path = tk.StringVar()
        self.image_list_data = [] # List of full paths
        self.selected_image_index = -1

        paned_window = ttk.PanedWindow(parent_tab, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both")

        left_pane = ttk.Frame(paned_window, width=450)
        paned_window.add(left_pane, weight=2)
        
        image_frame = ttk.LabelFrame(left_pane, text="1. Chọn file ảnh (từ danh sách bên phải)", padding="10")
        image_frame.pack(fill="x", pady=10, padx=5)
        ttk.Entry(image_frame, textvariable=self.video_image_path, state="readonly").pack(side="left", fill="x", expand=True)

        audio_frame = ttk.LabelFrame(left_pane, text="2. Chọn file âm thanh", padding="10")
        audio_frame.pack(fill="x", pady=10, padx=5)
        ttk.Entry(audio_frame, textvariable=self.video_audio_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(audio_frame, text="Duyệt...", command=lambda: self.browse_generic_file(self.video_audio_path, "audio")).pack(side="left")

        action_frame = ttk.Frame(left_pane, padding="10")
        action_frame.pack(fill="x", pady=20, padx=5)
        ttk.Label(action_frame, text="Định dạng video:").pack(side="left", padx=(0, 10))
        self.video_format_combo = ttk.Combobox(action_frame, values=[".mp4", ".mkv", ".avi", ".mov"], state="readonly", width=10)
        self.video_format_combo.set(".mp4")
        self.video_format_combo.pack(side="left", padx=(0, 20))
        
        ttk.Button(action_frame, text="Tạo Video", command=self.start_video_creation_thread).pack(side="right")

        self.video_progress_bar = ttk.Progressbar(left_pane, orient="horizontal", length=100, mode="determinate")
        self.video_progress_bar.pack(fill="x", pady=10, padx=5)

        status_frame = ttk.Frame(left_pane)
        status_frame.pack(fill="x", pady=(5, 0), padx=5)
        self.video_status_label = ttk.Label(status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w")
        self.video_status_label.pack(side="left", fill="x", expand=True)
        self.video_open_button = ttk.Button(status_frame, text="Mở thư mục", style="Open.TButton")
        
        right_pane = ttk.Frame(paned_window)
        paned_window.add(right_pane, weight=1)

        image_list_lf = ttk.LabelFrame(right_pane, text="Danh sách ảnh", padding=10)
        image_list_lf.pack(expand=True, fill="both", padx=5)
        
        canvas_frame = ttk.Frame(image_list_lf)
        canvas_frame.pack(expand=True, fill="both")
        self.image_canvas = tk.Canvas(canvas_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.image_canvas.yview)
        self.image_canvas.config(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.image_canvas.pack(side="left", expand=True, fill="both")
        self.image_canvas.bind("<Configure>", lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all")))
        self.image_canvas.bind("<Button-1>", self.on_image_canvas_click)
        self.image_canvas.bind_all("<MouseWheel>", lambda e: self.image_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        image_buttons_frame = ttk.Frame(image_list_lf)
        image_buttons_frame.pack(fill="x", pady=(5,0))
        ttk.Button(image_buttons_frame, text="Thêm Ảnh...", command=self.browse_images_for_list).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(image_buttons_frame, text="Thêm Thư mục...", command=self.browse_image_folder_for_list).pack(side="left", expand=True, fill="x", padx=(2, 2))
        ttk.Button(image_buttons_frame, text="Xóa hết", command=self.clear_image_list).pack(side="right", padx=(2, 0))

    # ======================================================================
    # --- TAB 3: XỬ LÝ NHANH (QUICK PROCESS) ---
    # ======================================================================
    def create_quick_process_tab(self, parent_tab):
        self.quick_input_folder = tk.StringVar()
        self.quick_output_folder = tk.StringVar()
        paned_window = ttk.PanedWindow(parent_tab, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both")
        left_frame = ttk.Frame(paned_window, width=250)
        paned_window.add(left_frame, weight=1)
        top_left_frame = ttk.Frame(left_frame)
        top_left_frame.pack(fill="x", pady=(0, 5))
        ttk.Button(top_left_frame, text="Chọn thư mục nguồn...", command=self.select_quick_folder).pack(side="left", expand=True, fill="x")
        self.quick_file_count_label = ttk.Label(top_left_frame, text=" (0 files)")
        self.quick_file_count_label.pack(side="left", padx=5)
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(expand=True, fill="both")
        self.quick_listbox = tk.Listbox(list_frame, font=("Segoe UI", 9))
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.quick_listbox.yview)
        self.quick_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.quick_listbox.pack(side="left", expand=True, fill="both")
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)
        options_lf = ttk.LabelFrame(right_frame, text="Tùy chọn xử lý hàng loạt", padding=10)
        options_lf.pack(fill="x", padx=5, pady=5)
        self.quick_preset_var = tk.StringVar(value="none")
        ttk.Radiobutton(options_lf, text="Không thay đổi tốc độ", variable=self.quick_preset_var, value="none").pack(anchor="w")
        ttk.Radiobutton(options_lf, text="Tăng tốc nhẹ (1.005x)", variable=self.quick_preset_var, value="speed_up").pack(anchor="w")
        ttk.Radiobutton(options_lf, text="Giảm tốc nhẹ (0.990x)", variable=self.quick_preset_var, value="speed_down").pack(anchor="w")
        ttk.Separator(options_lf, orient='horizontal').pack(fill='x', pady=10)
        self.quick_noise_var = tk.BooleanVar()
        ttk.Checkbutton(options_lf, text="Thêm nhiễu trắng cực nhẹ (amplitude 0.0005)", variable=self.quick_noise_var).pack(anchor="w")
        self.quick_normalize_var = tk.BooleanVar()
        ttk.Checkbutton(options_lf, text="Chuẩn hóa âm lượng", variable=self.quick_normalize_var).pack(anchor="w", pady=5)
        output_lf = ttk.LabelFrame(right_frame, text="Thư mục lưu file", padding=10)
        output_lf.pack(fill="x", padx=5, pady=10)
        ttk.Entry(output_lf, textvariable=self.quick_output_folder).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(output_lf, text="Duyệt...", command=self.select_quick_output_folder).pack(side="left")
        ttk.Button(right_frame, text="Bắt đầu xử lý hàng loạt", command=self.start_quick_process).pack(pady=20)
        self.quick_progress_bar = ttk.Progressbar(right_frame, orient="horizontal", length=100, mode="determinate")
        self.quick_progress_bar.pack(fill="x", pady=5, padx=5)
        self.quick_status_label = ttk.Label(right_frame, text="Sẵn sàng", style="Status.TLabel")
        self.quick_status_label.pack(fill="x", padx=5)

    # ======================================================================
    # --- HÀM CHUNG & XỬ LÝ SỰ KIỆN ---
    # ======================================================================
    def _create_slider_entry_pair(self, parent, label_text, from_val, to_val, initial_val, unit_text="", is_int=False, precision=2):
        frame = ttk.Frame(parent); frame.pack(fill="x", pady=5, padx=5)
        ttk.Label(frame, text=label_text, width=15).pack(side="left")
        num_var = tk.DoubleVar(value=initial_val)
        num_var.trace_add("write", self.mark_preview_as_dirty)
        def format_val(v): return f"{int(v)}" if is_int else f"{v:.{precision}f}"
        scale = ttk.Scale(frame, from_=from_val, to=to_val, orient="horizontal", variable=num_var)
        scale.pack(side="left", fill="x", expand=True, padx=(0, 10))
        entry = ttk.Entry(frame, width=10, justify='center')
        entry.pack(side="left")
        def update_from_scale(*args):
            val = num_var.get()
            entry.delete(0, tk.END); entry.insert(0, format_val(val))
        def update_from_entry(event=None):
            try:
                val = float(entry.get()); val = max(from_val, min(to_val, val))
                num_var.set(val)
            except (ValueError, TclError): update_from_scale()
            entry.delete(0, tk.END); entry.insert(0, format_val(num_var.get())); frame.focus()
        num_var.trace_add("write", update_from_scale)
        entry.bind("<Return>", update_from_entry); entry.bind("<FocusOut>", update_from_entry)
        entry.insert(0, format_val(initial_val))
        if unit_text: ttk.Label(frame, text=unit_text, width=10).pack(side="left", padx=(5, 0))
        return num_var

    def toggle_play_pause(self):
        if self.active_thread and self.active_thread.is_alive(): return

        if self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.play_pause_btn.config(text="❚❚ Pause")
            self.update_playback_progress()
        elif pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_pause_btn.config(text="▶ Play")
            if self.playback_update_id:
                self.after_cancel(self.playback_update_id)
        else:
            self.seek_offset = 0.0
            if self.is_preview_dirty:
                self.start_preview_generation(callback=self.play_audio)
            else:
                self.play_audio()

    def play_audio(self):
        file_to_play = self.preview_file_path if self.preview_file_path and os.path.exists(self.preview_file_path) else self.get_selected_audio_path()
        if not file_to_play or not os.path.exists(file_to_play): messagebox.showwarning("Chưa có file", "Vui lòng chọn một file âm thanh từ danh sách để phát."); return
        
        try:
            pygame.mixer.music.load(file_to_play)
            pygame.mixer.music.play(start=self.seek_offset)
            self.play_pause_btn.config(text="❚❚ Pause")
            self.is_paused = False
            self.update_playback_progress()
        except pygame.error as e: messagebox.showerror("Lỗi phát nhạc", f"Không thể phát file: {e}")

    def stop_audio(self):
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self.play_pause_btn.config(text="▶ Play")
        self.is_paused = False
        if self.playback_update_id:
            self.after_cancel(self.playback_update_id)
        self.seek_var.set(0)
        self.current_time_label.config(text="00:00.0")
        self.waveform_canvas.itemconfig(self.playhead, state=tk.HIDDEN)

    def on_seek_press(self, event):
        self.is_seeking = True

    def on_seek_release(self, event):
        if not self.is_seeking: return
        self.is_seeking = False
        if not self.get_selected_audio_path(): return
        self.seek_offset = self.seek_var.get()
        try:
            if pygame.mixer.music.get_busy() or self.is_paused:
                pygame.mixer.music.play(start=self.seek_offset)
                if self.is_paused:
                    pygame.mixer.music.pause()
            self.current_time_label.config(text=self.format_time(self.seek_offset))
            self.update_playhead()
        except pygame.error as e:
            print(f"Lỗi khi tua nhạc: {e}")

    def update_playback_progress(self):
        if pygame.mixer.music.get_busy() and not self.is_paused:
            if not self.is_seeking:
                elapsed_time = pygame.mixer.music.get_pos() / 1000.0
                current_pos_sec = self.seek_offset + elapsed_time
                
                total_duration = self.seek_bar.cget("to")
                if total_duration > 0 and current_pos_sec > total_duration:
                    self.stop_audio()
                    return

                self.seek_var.set(current_pos_sec)
                self.current_time_label.config(text=self.format_time(current_pos_sec))
                self.update_playhead()
            
            self.playback_update_id = self.after(100, self.update_playback_progress)
        elif not self.is_paused and self.get_selected_audio_path():
            self.stop_audio()

    def format_time(self, seconds):
        if seconds < 0: seconds = 0
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:04.1f}"

    def get_current_state(self):
        return {'speed': self.speed_var.get(),'tempo': self.tempo_var.get(),'pitch': self.pitch_var.get(),'normalize': self.audio_normalize.get(),'noise_reduce': self.audio_noise_reduce.get(),'noise_type': self.noise_type_combo.get(),'noise_amp': self.noise_amp_var.get()}

    def apply_state(self, state):
        self.speed_var.set(state['speed']); self.tempo_var.set(state['tempo']); self.pitch_var.set(state['pitch'])
        self.audio_normalize.set(state['normalize']); self.audio_noise_reduce.set(state['noise_reduce'])
        self.noise_type_combo.set(state['noise_type']); self.noise_amp_var.set(state['noise_amp'])
        self.mark_preview_as_dirty()

    def save_state(self):
        current_state = self.get_current_state()
        if not self.undo_stack or self.undo_stack[-1] != current_state:
            self.undo_stack.append(current_state); self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1:
            self.redo_stack.append(self.undo_stack.pop()); state_to_apply = self.undo_stack[-1]
            self.apply_state(state_to_apply); self.audio_status_label.config(text="Đã hoàn tác.")

    def redo(self):
        if self.redo_stack:
            state_to_apply = self.redo_stack.pop(); self.undo_stack.append(state_to_apply)
            self.apply_state(state_to_apply); self.audio_status_label.config(text="Đã làm lại.")

    def mark_preview_as_dirty(self, *args):
        self.is_preview_dirty = True
        self.waveform_data = None # Xóa cache waveform
        self.stop_audio()

    def browse_main_audio_file(self):
        paths = filedialog.askopenfilenames(
            title="Chọn một hoặc nhiều file âm thanh",
            filetypes=[("Audio Files", "*.mp3 *.wav *.aac *.flac *.opus *.ogg *.m4a"), ("All files", "*.*")]
        )
        if paths:
            self.add_audio_files_to_list(paths)

    def browse_main_audio_folder(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục chứa file âm thanh")
        if folder_path:
            self.add_audio_files_from_folder(folder_path)

    def browse_generic_file(self, path_var, file_type):
        types = {"image": [("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")], "audio": [("Audio Files", "*.mp3 *.wav *.aac *.flac *.opus *.ogg *.m4a"), ("All files", "*.*")]}
        path = filedialog.askopenfilename(title=f"Chọn một file {file_type}", filetypes=types.get(file_type))
        if path: path_var.set(path)

    def handle_global_drop(self, event):
        filepaths = self.tk.splitlist(event.data)
        current_tab_index = self.notebook.index(self.notebook.select())
        if len(filepaths) == 1 and os.path.isdir(filepaths[0]):
            folder_path = filepaths[0]
            if current_tab_index == 0: self.add_audio_files_from_folder(folder_path)
            elif current_tab_index == 1: self.add_images_from_folder(folder_path)
            elif current_tab_index == 2: self.select_quick_folder(folder_path)
            return
        audio_files_to_add, image_files_to_add = [], []
        for path in filepaths:
            if not os.path.isfile(path): continue
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp']: image_files_to_add.append(path)
            elif file_ext in ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']: audio_files_to_add.append(path)
            else: messagebox.showwarning("Loại file không được hỗ trợ", f"Không thể xử lý file: {os.path.basename(path)}")
        if current_tab_index == 0 and audio_files_to_add: self.add_audio_files_to_list(audio_files_to_add)
        elif current_tab_index == 1:
            if image_files_to_add: self.add_images_to_list(image_files_to_add)
            if audio_files_to_add: self.video_audio_path.set(audio_files_to_add[0])

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

    def build_ffmpeg_command(self, input_path, output_path, state_dict=None):
        state = state_dict if state_dict is not None else self.get_current_state()
        command, main_audio_chain = ['ffmpeg', '-i', input_path], []
        original_rate = 44100
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
            startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            original_rate = int(result.stdout.strip())
        except Exception as e: print(f"Không lấy được sample rate, sử dụng mặc định 44100. Lỗi: {e}")
        pitch_factor = 2**(state['pitch']/12.0); speed_factor = state['speed']; tempo_factor = state['tempo']
        if abs(pitch_factor * speed_factor - 1.0) > 1e-6:
            main_audio_chain.append(f"asetrate={original_rate*pitch_factor*speed_factor}")
        if main_audio_chain: main_audio_chain.append(f"aresample={original_rate}")
        if abs(tempo_factor - 1.0) > 1e-6:
            temp_tempo = tempo_factor
            while temp_tempo < 0.5: main_audio_chain.append("atempo=0.5"); temp_tempo /= 0.5
            main_audio_chain.append(f"atempo={temp_tempo}")
        if state.get('normalize'): main_audio_chain.append("dynaudnorm")
        if state.get('noise_reduce'): main_audio_chain.append("anlmdn")
        if state.get('noise_type') != "Không":
            noise_color = {"Nhiễu trắng": "white", "Nhiễu hồng": "pink", "Nhiễu nâu": "brown"}[state['noise_type']]
            main_chain_str = ",".join(main_audio_chain) if main_audio_chain else "anull"
            duration = self.get_file_duration(input_path) or 60
            filter_complex = f"[0:a:0]{main_chain_str}[main];anoisesrc=c={noise_color}:a={state['noise_amp']}:d={duration}[noise];[main][noise]amix=inputs=2:duration=first[out]"
            command.extend(['-filter_complex', filter_complex, '-map', '[out]'])
        elif main_audio_chain:
            command.extend(['-af', ",".join(main_audio_chain)])
        elif os.path.splitext(output_path)[1].lower() == '.wav': command.extend(['-c:a', 'pcm_s16le'])
        command.extend(['-y', output_path])
        return command

    def start_preview_generation(self, callback=None):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        audio_file = self.get_selected_audio_path()
        if not (audio_file and os.path.exists(audio_file)): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh từ danh sách."); return
        self.save_state()
        self.preview_file_path = os.path.join(TEMP_DIR, f"preview_{os.path.basename(audio_file)}.wav")
        command = self.build_ffmpeg_command(audio_file, self.preview_file_path)
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, audio_file, self.preview_file_path, True, self.audio_progress_bar, self.audio_status_label, self.audio_open_button, callback), daemon=True)
        self.active_thread.start()

    def export_audio(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        checked_files = self.get_checked_audio_files()
        if not checked_files: messagebox.showerror("Lỗi", "Vui lòng tích chọn ít nhất một file để xuất."); return
        output_folder = filedialog.askdirectory(title="Chọn thư mục để lưu các file đã xử lý")
        if not output_folder: return
        self.active_thread = threading.Thread(target=self.run_batch_export, args=(checked_files, output_folder), daemon=True)
        self.active_thread.start()

    def start_video_creation_thread(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        img_f, aud_f = self.video_image_path.get(), self.video_audio_path.get()
        if not all([img_f, aud_f, os.path.exists(img_f), os.path.exists(aud_f)]): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn file ảnh và âm thanh hợp lệ."); return
        output_path = filedialog.asksaveasfilename(initialfile=os.path.splitext(os.path.basename(aud_f))[0], title="Lưu video", defaultextension=self.video_format_combo.get())
        if not output_path: return
        
        command = ['ffmpeg', '-loop', '1', '-i', img_f, '-i', aud_f, 
                   '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', # Tự động sửa kích thước ảnh
                   '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', 
                   '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', '-y', output_path]

        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, aud_f, output_path, False, self.video_progress_bar, self.video_status_label, self.video_open_button), daemon=True)
        self.active_thread.start()

    def run_generic_process(self, command, input_file, output_path, is_preview, progress_bar, status_label, open_button, callback=None):
        progress_bar['value'] = 0; open_button.pack_forget()
        status_label.config(text="Đang lấy thông tin file...")
        self.update_idletasks()
        total_duration = self.get_file_duration(input_file)
        if total_duration is None: status_label.config(text="Lỗi: Không thể đọc thời lượng file."); return
        status_label.config(text="Bắt đầu xử lý...")
        
        startupinfo = None
        if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # --- SỬA LỖI TREO TẠI ĐÂY ---
        # Gộp stdout và stderr để đọc tiến trình từ một luồng duy nhất, tránh bị treo.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        state = self.get_current_state()
        tempo, speed = (state['tempo'], state['speed']) if is_preview else (1.0, 1.0)
        output_duration = total_duration / speed / tempo if (speed * tempo) != 0 else total_duration
        
        # Lưu lại một vài dòng output cuối để báo lỗi nếu cần
        output_buffer = deque(maxlen=20)

        for line in iter(process.stdout.readline, ''):
            output_buffer.append(line)
            match = time_pattern.search(line)
            if match and output_duration > 0:
                h, m, s, ms = map(int, match.groups())
                current_time = h*3600 + m*60 + s + ms/100
                progress = (current_time / output_duration) * 100
                progress_bar['value'] = min(progress, 100)
                status_label.config(text=f"Đang xử lý... {int(progress_bar['value'])}%")
                self.update_idletasks()

        process.wait()

        if process.returncode == 0:
            progress_bar['value'] = 100
            status_label.config(text="Hoàn thành!")
            if is_preview:
                self.is_preview_dirty = False
                if callback: self.after(0, callback)
            else:
                open_button.config(command=lambda: self.open_folder_and_select_file(output_path))
                open_button.pack(side="right", padx=(5, 0))
                if output_path.lower().endswith(('.mp3', '.wav', '.flac', '.opus', '.m4a')):
                    self.video_audio_path.set(output_path); self.notebook.select(self.video_creator_tab)
        else:
            # Nếu có lỗi, in ra thông báo chi tiết từ buffer
            status_label.config(text="Xử lý thất bại! Kiểm tra console.")
            print("="*60)
            print("LỖI FFMPEG: Lệnh sau đã thất bại:")
            print(f"  {' '.join(command)}")
            print("\nThông báo lỗi chi tiết từ FFMPEG (các dòng cuối):")
            for out_line in output_buffer:
                print(out_line, end='')
            print("\n" + "="*60)

    def select_quick_folder(self, folder_path=None):
        if not folder_path: folder_path = filedialog.askdirectory(title="Chọn thư mục chứa file âm thanh")
        if not folder_path: return
        self.quick_input_folder.set(folder_path)
        self.quick_listbox.delete(0, tk.END)
        audio_files = []
        supported_exts = ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                audio_files.append(entry.path)
        for f in sorted(audio_files): self.quick_listbox.insert(tk.END, os.path.basename(f))
        self.quick_file_count_label.config(text=f" ({len(audio_files)} files)")

    def select_quick_output_folder(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục để lưu file đã xử lý")
        if folder_path: self.quick_output_folder.set(folder_path)

    def start_quick_process(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        input_folder, output_folder = self.quick_input_folder.get(), self.quick_output_folder.get()
        files_to_process = self.quick_listbox.get(0, tk.END)
        if not files_to_process: messagebox.showerror("Lỗi", "Không có file nào trong danh sách để xử lý."); return
        if not output_folder: messagebox.showerror("Lỗi", "Vui lòng chọn thư mục đầu ra."); return
        if output_folder == input_folder: messagebox.showerror("Lỗi", "Thư mục đầu ra không được trùng với thư mục nguồn."); return
        self.active_thread = threading.Thread(target=self.run_quick_process, args=(input_folder, output_folder, files_to_process), daemon=True)
        self.active_thread.start()

    def run_quick_process(self, input_folder, output_folder, filenames):
        self.quick_progress_bar['maximum'] = len(filenames)
        self.quick_progress_bar['value'] = 0
        preset = self.quick_preset_var.get(); add_noise = self.quick_noise_var.get(); normalize = self.quick_normalize_var.get()
        state = {'speed': 1.0, 'tempo': 1.0, 'pitch': 0.0, 'normalize': normalize, 'noise_reduce': False, 'noise_type': 'Không', 'noise_amp': 0.0}
        if preset == "speed_up": state['speed'] = 1.005
        elif preset == "speed_down": state['speed'] = 0.990
        if add_noise: state['noise_type'] = "Nhiễu trắng"; state['noise_amp'] = 0.0005
        for i, filename in enumerate(filenames):
            self.quick_status_label.config(text=f"Đang xử lý {i+1}/{len(filenames)}: {filename}")
            self.quick_progress_bar['value'] = i; self.update_idletasks()
            input_path = os.path.join(input_folder, filename); output_path = os.path.join(output_folder, filename)
            command = self.build_ffmpeg_command(input_path, output_path, state)
            try:
                startupinfo = None
                if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(command, check=True, capture_output=True, startupinfo=startupinfo, text=True, encoding='utf-8')
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi xử lý file {filename}:\n{e.stderr}")
                self.quick_status_label.config(text=f"Lỗi xử lý file: {filename}. Bỏ qua."); continue
        self.quick_progress_bar['value'] = len(filenames)
        self.quick_status_label.config(text=f"Hoàn thành! Đã xử lý {len(filenames)} files.")
        messagebox.showinfo("Hoàn thành", f"Đã xử lý thành công {len(filenames)} files.\nLưu tại: {output_folder}")

    def browse_images_for_list(self):
        paths = filedialog.askopenfilenames(
            title="Chọn một hoặc nhiều file ảnh",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")])
        if paths: self.add_images_to_list(paths)

    def browse_image_folder_for_list(self):
        folder_path = filedialog.askdirectory(title="Chọn một thư mục ảnh")
        if folder_path: self.add_images_from_folder(folder_path)

    def add_images_from_folder(self, folder_path):
        image_paths, supported_exts = [], ['.jpg', '.jpeg', '.png', '.bmp']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                image_paths.append(entry.path)
        if image_paths: self.add_images_to_list(image_paths)
        else: messagebox.showinfo("Thông báo", "Không tìm thấy file ảnh nào trong thư mục đã chọn.", parent=self)

    def add_images_to_list(self, paths):
        for path in paths:
            if path not in self.image_list_data: self.image_list_data.append(path)
        self.update_image_list_display()
    
    def clear_image_list(self):
        self.image_list_data.clear(); self.video_image_path.set(""); self.selected_image_index = -1
        self.update_image_list_display()

    def on_image_canvas_click(self, event):
        canvas_y = self.image_canvas.canvasy(event.y)
        item_height = 64 + 4
        clicked_index = int(canvas_y // item_height)
        if 0 <= clicked_index < len(self.image_list_data):
            if self.selected_image_index != -1:
                self.update_image_selection_bg(self.selected_image_index, "white")
            self.selected_image_index = clicked_index
            self.video_image_path.set(self.image_list_data[self.selected_image_index])
            self.update_image_selection_bg(self.selected_image_index, "#E0E8F0")

    def update_image_selection_bg(self, index, color):
        item_height = 64 + 4; y0 = 2 + (index * item_height)
        rect_id = self.image_canvas.find_closest(2, y0 + 2)[0]
        self.image_canvas.itemconfig(rect_id, fill=color)

    def update_image_list_display(self):
        self.image_canvas.delete("all"); self.image_thumbnails.clear()
        y_pos, thumb_size, item_height = 2, (64, 64), 68
        for i, path in enumerate(self.image_list_data):
            try:
                img = Image.open(path)
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.image_thumbnails.append(photo_img)
                bg_color = "#E0E8F0" if i == self.selected_image_index else "white"
                self.image_canvas.create_rectangle(0, y_pos - 2, self.image_canvas.winfo_width(), y_pos + item_height - 2, fill=bg_color, outline="", tags=f"bg_{i}")
                self.image_canvas.create_image(4, y_pos, anchor="nw", image=photo_img)
                self.image_canvas.create_text(thumb_size[0] + 10, y_pos + (item_height / 2), anchor="w", text=os.path.basename(path), font=("Segoe UI", 9))
                y_pos += item_height
            except Exception as e:
                print(f"Lỗi khi tải thumbnail cho {path}: {e}")
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))

# --- Chạy ứng dụng ---
if __name__ == "__main__":
    app = FfmpegGuiApp()
    app.mainloop()