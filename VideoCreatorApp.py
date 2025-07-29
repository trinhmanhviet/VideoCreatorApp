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

# Kiểm tra và yêu cầu cài đặt các thư viện cần thiết
try:
    import pygame
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
        
        # --- Biến chung ---
        self.active_thread = None
        self.image_thumbnails = [] # Giữ tham chiếu đến ảnh thumbnail để không bị xóa
        self.seek_offset = 0.0 # Lưu vị trí tua nhạc
        self.check_ffmpeg_tools()

        # --- Tạo giao diện chính ---
        self.create_main_layout()

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
        file_menu.add_command(label="Mở file âm thanh...", command=self.browse_main_audio_file)
        file_menu.add_command(label="Xuất Audio...", command=self.export_audio)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.destroy)

        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())

    # ======================================================================
    # --- TAB 1: SỬA NHẠC (GIAO DIỆN AUDACITY) ---
    # ======================================================================
    def create_audio_editor_tab(self, parent_tab):
        self.audio_edit_path = tk.StringVar()
        self.preview_file_path = None
        self.undo_stack = []
        self.redo_stack = []
        self.is_preview_dirty = True
        self.is_paused = False
        self.playback_update_id = None
        self.is_seeking = False # Cờ để kiểm tra người dùng có đang kéo thanh trượt không
        
        top_frame = ttk.Frame(parent_tab)
        top_frame.pack(side="top", fill="x")

        toolbar_frame = ttk.Frame(top_frame, style="TFrame", relief="groove", borderwidth=1)
        toolbar_frame.pack(side="top", fill="x", padx=5, pady=5)
        self.create_audio_toolbar(toolbar_frame)

        player_frame = ttk.Frame(top_frame)
        player_frame.pack(fill="x", padx=10, pady=5)
        self.current_time_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.current_time_label.pack(side="left")
        self.seek_bar = ttk.Scale(player_frame, from_=0, to=100, orient="horizontal")
        self.seek_bar.bind("<ButtonPress-1>", self.on_seek_press)
        self.seek_bar.bind("<ButtonRelease-1>", self.on_seek_release)
        self.seek_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.total_duration_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.total_duration_label.pack(side="left")
        
        track_area = ttk.Frame(parent_tab)
        track_area.pack(expand=True, fill="both", padx=5)
        self.create_track_view(track_area)
        
        bottom_frame = ttk.Frame(parent_tab, style="TFrame")
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        self.create_audio_status_bar(bottom_frame)

        self.save_state()

    def create_audio_toolbar(self, parent):
        self.play_pause_btn = ttk.Button(parent, text="▶ Play", width=8, command=self.toggle_play_pause)
        self.play_pause_btn.pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="■ Stop", width=8, command=self.stop_audio).pack(side="left", padx=2, pady=5)
        ttk.Separator(parent, orient='vertical').pack(side='left', fill='y', padx=10, pady=5)
        ttk.Button(parent, text="↩ Undo", command=self.undo).pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="↪ Redo", command=self.redo).pack(side="left", padx=2, pady=5)

    def create_track_view(self, parent):
        track_frame = ttk.LabelFrame(parent, text="Chưa có file âm thanh nào")
        track_frame.pack(expand=True, fill="both", pady=5)
        self.track_frame_label = track_frame
        
        left_panel = ttk.Frame(track_frame, width=150, style="TFrame", relief="groove", borderwidth=1)
        left_panel.pack(side="left", fill="y", padx=5, pady=5); left_panel.pack_propagate(False)
        ttk.Button(left_panel, text="Mute").pack(fill="x", padx=5, pady=5)
        ttk.Button(left_panel, text="Solo").pack(fill="x", padx=5)
        ttk.Label(left_panel, text="L    —    R").pack(pady=(10, 0))
        ttk.Scale(left_panel, from_=-1, to=1, value=0, orient="horizontal").pack(fill="x", padx=5)

        right_panel = ttk.Frame(track_frame)
        right_panel.pack(side="right", expand=True, fill="both")
        
        self.waveform_canvas = tk.Canvas(right_panel, bg="white", height=150)
        self.waveform_canvas.pack(fill="x", padx=5, pady=5)
        self.waveform_canvas.create_text(10, 10, anchor="nw", text="Kéo và thả file âm thanh vào đây để bắt đầu.", font=("Segoe UI", 10))

        options_frame = ttk.Frame(right_panel)
        options_frame.pack(expand=True, fill="both")
        
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
        
        ttk.Button(right_panel, text="Xuất Audio...", command=self.export_audio).pack(pady=10)

    def create_audio_status_bar(self, parent):
        self.audio_progress_bar = ttk.Progressbar(parent, orient="horizontal", length=100, mode="determinate")
        self.audio_progress_bar.pack(fill="x", pady=5, padx=5)
        status_frame = ttk.Frame(parent); status_frame.pack(fill="x", padx=5)
        self.audio_status_label = ttk.Label(status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w")
        self.audio_status_label.pack(side="left", fill="x", expand=True)
        self.audio_open_button = ttk.Button(status_frame, text="Mở thư mục", style="Open.TButton")

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

        # Cột trái: Điều khiển
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
        
        # Cột phải: Danh sách ảnh với thumbnail
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
        num_var.trace_add("write", self.mark_preview_as_dirty) # Đánh dấu thay đổi
        
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

        if self.is_paused: # Nếu đang tạm dừng -> phát tiếp
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.play_pause_btn.config(text="❚❚ Pause")
            self.update_playback_progress()
        elif pygame.mixer.music.get_busy(): # Nếu đang phát -> tạm dừng
            pygame.mixer.music.pause()
            self.is_paused = True
            self.play_pause_btn.config(text="▶ Play")
            if self.playback_update_id:
                self.after_cancel(self.playback_update_id)
        else: # Nếu chưa phát -> bắt đầu
            self.seek_offset = 0.0 # Bắt đầu lại từ đầu
            if self.is_preview_dirty:
                self.start_preview_generation(callback=self.play_audio)
            else:
                self.play_audio()

    def play_audio(self):
        file_to_play = self.preview_file_path if self.preview_file_path and os.path.exists(self.preview_file_path) else self.audio_edit_path.get()
        if not file_to_play or not os.path.exists(file_to_play): messagebox.showwarning("Chưa có file", "Vui lòng mở một file âm thanh."); return
        
        try:
            sound = pygame.mixer.Sound(file_to_play)
            total_seconds = sound.get_length()
            self.seek_bar.config(to=total_seconds)
            self.total_duration_label.config(text=self.format_time(total_seconds))
            
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
        self.seek_bar.set(0)
        self.current_time_label.config(text="00:00.0")

    def on_seek_press(self, event):
        """Khi người dùng nhấn chuột vào thanh trượt, đặt cờ đang tua."""
        self.is_seeking = True

    def on_seek_release(self, event):
        """Khi người dùng nhả chuột, thực hiện tua nhạc và bỏ cờ."""
        if not self.is_seeking:
            return
            
        self.is_seeking = False
        
        if not self.audio_edit_path.get(): return
        
        self.seek_offset = self.seek_bar.get()
        
        try:
            # Nếu đang phát hoặc đang tạm dừng, phát lại từ vị trí mới
            if pygame.mixer.music.get_busy() or self.is_paused:
                pygame.mixer.music.play(start=self.seek_offset)
                if self.is_paused:
                    pygame.mixer.music.pause()
            # Nếu đã dừng, chỉ cần cập nhật offset, lần play tiếp theo sẽ dùng nó
            
            # Cập nhật ngay lập tức nhãn thời gian
            self.current_time_label.config(text=self.format_time(self.seek_offset))
        except pygame.error as e:
            print(f"Lỗi khi tua nhạc: {e}")

    def update_playback_progress(self):
        """Cập nhật vị trí thanh trượt và thời gian khi nhạc đang phát."""
        if pygame.mixer.music.get_busy() and not self.is_paused:
            if not self.is_seeking:
                elapsed_time = pygame.mixer.music.get_pos() / 1000.0
                current_pos_sec = self.seek_offset + elapsed_time
                
                total_duration = self.seek_bar.cget("to")
                if total_duration > 0 and current_pos_sec > total_duration:
                    self.stop_audio()
                    return

                self.seek_bar.set(current_pos_sec)
                self.current_time_label.config(text=self.format_time(current_pos_sec))
            
            self.playback_update_id = self.after(100, self.update_playback_progress)
        elif not self.is_paused and self.audio_edit_path.get():
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
        self.stop_audio()

    def browse_main_audio_file(self):
        types = [("Audio Files", "*.mp3 *.wav *.aac *.flac *.opus *.ogg *.m4a"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Chọn một file âm thanh", filetypes=types)
        if path: self.load_new_audio_file(path)

    def browse_generic_file(self, path_var, file_type):
        types = {"image": [("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")], "audio": [("Audio Files", "*.mp3 *.wav *.aac *.flac *.opus *.ogg *.m4a"), ("All files", "*.*")]}
        path = filedialog.askopenfilename(title=f"Chọn một file {file_type}", filetypes=types.get(file_type))
        if path: path_var.set(path)

    def load_new_audio_file(self, path):
        self.stop_audio(); self.audio_edit_path.set(path)
        self.track_frame_label.config(text=os.path.basename(path))
        self.waveform_canvas.delete("all"); self.waveform_canvas.create_text(10, 10, anchor="nw", text=f"Đã tải: {os.path.basename(path)}", font=("Segoe UI", 10))
        self.preview_file_path = None; self.undo_stack.clear(); self.redo_stack.clear(); self.save_state()
        self.mark_preview_as_dirty()
        self.total_duration_label.config(text="00:00.0")

    def handle_global_drop(self, event):
        filepaths = self.tk.splitlist(event.data)
        current_tab_index = self.notebook.index(self.notebook.select())
        
        # Xử lý kéo thả thư mục
        if len(filepaths) == 1 and os.path.isdir(filepaths[0]):
            folder_path = filepaths[0]
            if current_tab_index == 1: # Tab Tạo Video
                self.add_images_from_folder(folder_path)
            elif current_tab_index == 2: # Tab Xử lý nhanh
                self.select_quick_folder(folder_path)
            return

        # Xử lý kéo thả file
        for path in filepaths:
            if not os.path.isfile(path): continue
            file_ext = os.path.splitext(path)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                if current_tab_index == 1:
                    self.add_images_to_list([path])
                    self.notebook.select(self.video_creator_tab)
            elif file_ext in ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']:
                if current_tab_index == 0: self.load_new_audio_file(path)
                elif current_tab_index == 1: self.video_audio_path.set(path)
            else:
                messagebox.showwarning("Loại file không được hỗ trợ", f"Không thể xử lý file: {os.path.basename(path)}")


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

    # --- Processing Logic ---
    def build_ffmpeg_command(self, input_path, output_path, state_dict=None):
        state = state_dict if state_dict is not None else self.get_current_state()
        command = ['ffmpeg', '-i', input_path]
        main_audio_chain = []
        
        original_rate = 44100
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
            startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            original_rate = int(result.stdout.strip())
        except Exception as e: print(f"Không lấy được sample rate, sử dụng mặc định 44100. Lỗi: {e}")
            
        pitch_factor = 2**(state['pitch'] / 12.0) if 'pitch' in state else 1.0
        speed_factor = state['speed'] if 'speed' in state else 1.0
        tempo_factor = state['tempo'] if 'tempo' in state else 1.0
        
        if abs(pitch_factor * speed_factor - 1.0) > 1e-6:
            final_rate = original_rate * pitch_factor * speed_factor
            main_audio_chain.append(f"asetrate={final_rate}")

        if main_audio_chain: main_audio_chain.append(f"aresample={original_rate}")
        if abs(tempo_factor - 1.0) > 1e-6:
            temp_tempo = tempo_factor
            while temp_tempo < 0.5: main_audio_chain.append("atempo=0.5"); temp_tempo /= 0.5
            main_audio_chain.append(f"atempo={temp_tempo}")

        if state.get('normalize'): main_audio_chain.append("dynaudnorm")
        if state.get('noise_reduce'): main_audio_chain.append("anlmdn")

        if state.get('noise_type') != "Không" and state.get('noise_type') is not None:
            noise_color = {"Nhiễu trắng": "white", "Nhiễu hồng": "pink", "Nhiễu nâu": "brown"}[state['noise_type']]
            main_chain_str = ",".join(main_audio_chain) if main_audio_chain else "anull"
            duration = self.get_file_duration(input_path) or 60
            filter_complex = f"[0:a:0]{main_chain_str}[main];anoisesrc=c={noise_color}:a={state['noise_amp']}:d={duration}[noise];[main][noise]amix=inputs=2:duration=first[out]"
            command.extend(['-filter_complex', filter_complex, '-map', '[out]'])
        elif main_audio_chain:
            command.extend(['-af', ",".join(main_audio_chain)])
        else:
            output_ext = os.path.splitext(output_path)[1].lower()
            if output_ext == '.wav': command.extend(['-c:a', 'pcm_s16le'])
        
        command.extend(['-y', output_path])
        return command

    def start_preview_generation(self, callback=None):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        audio_file = self.audio_edit_path.get()
        if not (audio_file and os.path.exists(audio_file)): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh."); return
        
        self.save_state()
        self.preview_file_path = os.path.join(TEMP_DIR, f"preview_{os.path.basename(audio_file)}.wav")
        command = self.build_ffmpeg_command(audio_file, self.preview_file_path)
        
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, audio_file, self.preview_file_path, True, self.audio_progress_bar, self.audio_status_label, self.audio_open_button, callback))
        self.active_thread.daemon = True; self.active_thread.start()

    def export_audio(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        audio_file = self.audio_edit_path.get()
        if not (audio_file and os.path.exists(audio_file)): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh."); return

        file_types = [("MPEG Audio Layer III", "*.mp3"), ("Waveform Audio File", "*.wav"), ("Free Lossless Audio Codec", "*.flac"), ("Opus Audio", "*.opus"), ("Advanced Audio Coding", "*.m4a"), ("All files", "*.*")]
        output_path = filedialog.asksaveasfilename(initialfile=os.path.splitext(os.path.basename(audio_file))[0] + "_edited", title="Xuất file âm thanh", filetypes=file_types, defaultextension=".mp3")
        if not output_path: return
        
        command = self.build_ffmpeg_command(audio_file, output_path)
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, audio_file, output_path, False, self.audio_progress_bar, self.audio_status_label, self.audio_open_button))
        self.active_thread.daemon = True; self.active_thread.start()

    def start_video_creation_thread(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        img_f, aud_f = self.video_image_path.get(), self.video_audio_path.get()
        if not all([img_f, aud_f, os.path.exists(img_f), os.path.exists(aud_f)]): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn file ảnh và âm thanh hợp lệ."); return
        
        output_path = filedialog.asksaveasfilename(initialfile=os.path.splitext(os.path.basename(aud_f))[0], title="Lưu video", defaultextension=self.video_format_combo.get())
        if not output_path: return
        
        command = ['ffmpeg', '-loop', '1', '-i', img_f, '-i', aud_f, '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', '-y', output_path]
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, aud_f, output_path, False, self.video_progress_bar, self.video_status_label, self.video_open_button))
        self.active_thread.daemon = True; self.active_thread.start()

    def run_generic_process(self, command, input_file, output_path, is_preview, progress_bar, status_label, open_button, callback=None):
        progress_bar['value'] = 0; open_button.pack_forget()
        status_label.config(text="Đang lấy thông tin file...")
        self.update_idletasks()

        total_duration = self.get_file_duration(input_file)
        if total_duration is None: status_label.config(text="Lỗi: Không thể đọc thời lượng file."); return

        status_label.config(text="Bắt đầu xử lý...")
        
        startupinfo = None
        if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', startupinfo=startupinfo)
        
        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        
        state = self.get_current_state()
        tempo_factor = state['tempo']; speed_factor = state['speed']
        output_duration = total_duration / speed_factor / tempo_factor if (speed_factor * tempo_factor) != 0 else total_duration

        for line in process.stdout:
            match = time_pattern.search(line)
            if match and output_duration > 0:
                h, m, s, ms = map(int, match.groups())
                current_time = h * 3600 + m * 60 + s + ms / 100
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
                if callback:
                    self.after(0, callback)
            else:
                open_button.config(command=lambda: self.open_folder_and_select_file(output_path))
                open_button.pack(side="right", padx=(5, 0))
                # Tự động import vào tab tạo video
                if output_path.endswith(('.mp3', '.wav', '.flac', '.opus', '.m4a')):
                    self.video_audio_path.set(output_path)
                    self.notebook.select(self.video_creator_tab)
        else:
            status_label.config(text="Xử lý thất bại! Kiểm tra console.")
            print(f"Lỗi FFMPEG: Lệnh '{' '.join(command)}' thất bại.")

    # --- Quick Process Logic ---
    def select_quick_folder(self, folder_path=None):
        if not folder_path:
            folder_path = filedialog.askdirectory(title="Chọn thư mục chứa file âm thanh")
        if not folder_path: return

        self.quick_input_folder.set(folder_path)
        self.quick_listbox.delete(0, tk.END)
        
        audio_files = []
        supported_exts = ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                audio_files.append(entry.path)
        
        for f in sorted(audio_files):
            self.quick_listbox.insert(tk.END, os.path.basename(f))
        
        self.quick_file_count_label.config(text=f" ({len(audio_files)} files)")

    def select_quick_output_folder(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục để lưu file đã xử lý")
        if folder_path:
            self.quick_output_folder.set(folder_path)

    def start_quick_process(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang được thực hiện."); return
        
        input_folder = self.quick_input_folder.get()
        output_folder = self.quick_output_folder.get()
        files_to_process = self.quick_listbox.get(0, tk.END)

        if not files_to_process: messagebox.showerror("Lỗi", "Không có file nào trong danh sách để xử lý."); return
        if not output_folder: messagebox.showerror("Lỗi", "Vui lòng chọn thư mục đầu ra."); return
        if output_folder == input_folder: messagebox.showerror("Lỗi", "Thư mục đầu ra không được trùng với thư mục nguồn."); return

        self.active_thread = threading.Thread(target=self.run_quick_process, args=(input_folder, output_folder, files_to_process))
        self.active_thread.daemon = True
        self.active_thread.start()

    def run_quick_process(self, input_folder, output_folder, filenames):
        self.quick_progress_bar['maximum'] = len(filenames)
        self.quick_progress_bar['value'] = 0
        
        # Lấy tùy chọn
        preset = self.quick_preset_var.get()
        add_noise = self.quick_noise_var.get()
        normalize = self.quick_normalize_var.get()

        state = {'speed': 1.0, 'tempo': 1.0, 'pitch': 0.0, 'normalize': normalize, 'noise_reduce': False, 'noise_type': 'Không', 'noise_amp': 0.0}
        if preset == "speed_up":
            state['speed'] = 1.005
        elif preset == "speed_down":
            state['speed'] = 0.990
        
        if add_noise:
            state['noise_type'] = "Nhiễu trắng"
            state['noise_amp'] = 0.0005

        for i, filename in enumerate(filenames):
            self.quick_status_label.config(text=f"Đang xử lý {i+1}/{len(filenames)}: {filename}")
            self.quick_progress_bar['value'] = i
            self.update_idletasks()

            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            command = self.build_ffmpeg_command(input_path, output_path, state)
            
            try:
                startupinfo = None
                if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(command, check=True, capture_output=True, startupinfo=startupinfo)
            except subprocess.CalledProcessError as e:
                print(f"Lỗi khi xử lý file {filename}:\n{e.stderr.decode('utf-8', errors='ignore')}")
                self.quick_status_label.config(text=f"Lỗi xử lý file: {filename}. Bỏ qua.")
                continue # Bỏ qua file lỗi và tiếp tục

        self.quick_progress_bar['value'] = len(filenames)
        self.quick_status_label.config(text=f"Hoàn thành! Đã xử lý {len(filenames)} files.")
        messagebox.showinfo("Hoàn thành", f"Đã xử lý thành công {len(filenames)} files.\nLưu tại: {output_folder}")

    # --- Video Creator Image List Logic ---
    def browse_images_for_list(self):
        paths = filedialog.askopenfilenames(
            title="Chọn một hoặc nhiều file ảnh",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")]
        )
        if paths:
            self.add_images_to_list(paths)

    def browse_image_folder_for_list(self):
        folder_path = filedialog.askdirectory(title="Chọn một thư mục ảnh")
        if folder_path:
            self.add_images_from_folder(folder_path)

    def add_images_from_folder(self, folder_path):
        image_paths = []
        supported_exts = ['.jpg', '.jpeg', '.png', '.bmp']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts:
                image_paths.append(entry.path)
        if image_paths:
            self.add_images_to_list(image_paths)
        else:
            messagebox.showinfo("Thông báo", "Không tìm thấy file ảnh nào trong thư mục đã chọn.", parent=self)

    def add_images_to_list(self, paths):
        for path in paths:
            if path not in self.image_list_data:
                self.image_list_data.append(path)
        self.update_image_list_display()
    
    def clear_image_list(self):
        self.image_list_data.clear()
        self.video_image_path.set("")
        self.selected_image_index = -1
        self.update_image_list_display()

    def on_image_canvas_click(self, event):
        canvas_y = self.image_canvas.canvasy(event.y)
        item_height = 64 + 4 # Thumbnail height + padding
        clicked_index = int(canvas_y // item_height)

        if 0 <= clicked_index < len(self.image_list_data):
            # Tối ưu hóa: chỉ thay đổi màu nền, không vẽ lại toàn bộ
            if self.selected_image_index != -1:
                self.update_image_selection_bg(self.selected_image_index, "white")
            
            self.selected_image_index = clicked_index
            self.video_image_path.set(self.image_list_data[self.selected_image_index])
            self.update_image_selection_bg(self.selected_image_index, "#E0E8F0")

    def update_image_selection_bg(self, index, color):
        """Chỉ cập nhật màu nền cho một mục trong danh sách ảnh."""
        item_height = 64 + 4
        y0 = 2 + (index * item_height)
        # Tìm item hình chữ nhật theo tọa độ y
        rect_id = self.image_canvas.find_closest(2, y0 + 2)[0]
        self.image_canvas.itemconfig(rect_id, fill=color)

    def update_image_list_display(self):
        self.image_canvas.delete("all")
        self.image_thumbnails.clear() # Xóa các tham chiếu cũ
        
        y_pos = 2
        thumb_size = (64, 64)
        item_height = thumb_size[1] + 4
        
        for i, path in enumerate(self.image_list_data):
            try:
                img = Image.open(path)
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                photo_img = ImageTk.PhotoImage(img)
                self.image_thumbnails.append(photo_img) # Giữ tham chiếu

                # Vẽ background cho mục
                bg_color = "#E0E8F0" if i == self.selected_image_index else "white"
                self.image_canvas.create_rectangle(0, y_pos - 2, self.image_canvas.winfo_width(), y_pos + item_height - 2, fill=bg_color, outline="", tags=f"bg_{i}")

                # Vẽ ảnh và tên file
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