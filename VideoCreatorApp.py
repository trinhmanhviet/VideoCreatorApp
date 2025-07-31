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

# --- KIỂM TRA THƯ VIỆN (Đã bỏ numpy) ---
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
# --- Lớp ứng dụng chính ---
class FfmpegGuiApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bộ công cụ Media")
        self.geometry("950x800")
        self.configure(bg="#ECECEC")

        pygame.init()
        pygame.mixer.init()

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
        self.duration_cache = {} # Cache chỉ để lưu thời lượng, giúp chọn file nhanh
        self.check_ffmpeg_tools()
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
                startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
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
        file_menu.add_command(label="Xuất Audio...", command=self.export_audio)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.on_closing)
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self.undo)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self.redo)
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())

    # --- TAB 1: SỬA NHẠC (Đã bỏ dạng sóng) ---
    def create_audio_editor_tab(self, parent_tab):
        self.preview_file_path = None
        self.undo_stack = []; self.redo_stack = []
        self.is_preview_dirty = True; self.is_paused = False
        self.playback_update_id = None; self.is_seeking = False
        self.audio_file_paths = {}

        paned_window = ttk.PanedWindow(parent_tab, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both")

        left_pane = ttk.Frame(paned_window, width=300)
        paned_window.add(left_pane, weight=1)
        
        # MỚI: Khung chứa chế độ một file
        self.single_audio_frame = ttk.LabelFrame(left_pane, text="Chọn 1 file audio", padding=5)
        self.single_audio_path = tk.StringVar()
        self.single_audio_path.trace_add("write", self.on_single_audio_select)
        ttk.Entry(self.single_audio_frame, textvariable=self.single_audio_path, state="readonly").pack(side="left", fill="x", expand=True, padx=(0,5))
        ttk.Button(self.single_audio_frame, text="Duyệt...", command=lambda: self.browse_generic_file(self.single_audio_path, "audio")).pack(side="right")

        # SỬA: Khung chứa chế độ nhiều file (batch)
        self.list_lf = ttk.LabelFrame(left_pane, text="Danh sách file (chế độ hàng loạt)", padding=5)
        
        self.audio_tree = ttk.Treeview(self.list_lf, columns=("filename",), show="headings", selectmode="extended")
        self.audio_tree.heading("filename", text="Tên file")
        self.audio_tree.column("filename", anchor="w")
        self.audio_tree.tag_configure('checked', image=self.get_check_image(True))
        self.audio_tree.tag_configure('unchecked', image=self.get_check_image(False))
        self.audio_tree.bind("<Button-1>", self.on_audio_tree_click)
        self.audio_tree.bind("<<TreeviewSelect>>", self.on_audio_tree_select)
        
        scrollbar = ttk.Scrollbar(self.list_lf, orient=tk.VERTICAL, command=self.audio_tree.yview)
        self.audio_tree.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.audio_tree.pack(expand=True, fill="both")
        
        list_buttons_frame = ttk.Frame(self.list_lf)
        list_buttons_frame.pack(fill="x", pady=5)
        ttk.Button(list_buttons_frame, text="Check tất cả", command=lambda: self.toggle_all_audio_checks(True)).pack(side="left", expand=True, fill="x")
        ttk.Button(list_buttons_frame, text="Bỏ Check", command=lambda: self.toggle_all_audio_checks(False)).pack(side="left", expand=True, fill="x")
        ttk.Button(list_buttons_frame, text="Đảo ngược", command=self.invert_audio_checks).pack(side="left", expand=True, fill="x")

        right_pane = ttk.Frame(paned_window)
        paned_window.add(right_pane, weight=3)

        top_frame = ttk.Frame(right_pane)
        top_frame.pack(side="top", fill="x")

        # MỚI: Checkbox chuyển đổi chế độ
        mode_frame = ttk.Frame(top_frame)
        mode_frame.pack(fill="x", padx=5, pady=5)
        self.audio_batch_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(mode_frame, text="Chế độ hàng loạt (Batch)", variable=self.audio_batch_mode, command=self.toggle_audio_batch_mode).pack(anchor="w")

        toolbar_frame = ttk.Frame(top_frame, style="TFrame", relief="groove", borderwidth=1)
        toolbar_frame.pack(side="top", fill="x", padx=5, pady=5)
        self.create_audio_toolbar(toolbar_frame)
        
        player_frame = ttk.Frame(top_frame)
        player_frame.pack(fill="x", padx=10, pady=10)
        self.current_time_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.current_time_label.pack(side="left")
        
        self.seek_var = tk.DoubleVar()
        self.seek_bar = ttk.Scale(player_frame, from_=0, to=100, orient="horizontal", variable=self.seek_var)
        self.seek_bar.bind("<ButtonPress-1>", self.on_seek_press)
        self.seek_bar.bind("<ButtonRelease-1>", self.on_seek_release)
        self.seek_bar.pack(side="left", fill="x", expand=True, padx=5)

        self.total_duration_label = ttk.Label(player_frame, text="00:00.0", font=("Consolas", 9))
        self.total_duration_label.pack(side="left")
        
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
        
        ttk.Button(right_pane, text="Xuất Audio...", command=self.export_audio).pack(pady=10)

        bottom_frame = ttk.Frame(right_pane, style="TFrame")
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        self.create_audio_status_bar(bottom_frame)

        self.save_state()
        self.toggle_audio_batch_mode() # MỚI: Đặt trạng thái ban đầu cho giao diện

    # MỚI: Hàm chuyển đổi giao diện giữa chế độ batch và single
    def toggle_audio_batch_mode(self):
        self.stop_audio()
        if self.audio_batch_mode.get(): # Chế độ hàng loạt
            self.single_audio_frame.pack_forget()
            self.list_lf.pack(expand=True, fill="both", pady=(5,0))
            self.on_audio_tree_select(None) # Cập nhật thanh seek bar
        else: # Chế độ một file
            self.list_lf.pack_forget()
            self.single_audio_frame.pack(fill="x", pady=(5,0))
            self.on_single_audio_select(None) # Cập nhật thanh seek bar
    
    # MỚI: Hàm xử lý khi chọn một file trong chế độ single
    def on_single_audio_select(self, *args):
        self.mark_preview_as_dirty()
        self.seek_offset = 0.0
        self.seek_var.set(0)
        self.current_time_label.config(text="00:00.0")
        selected_path = self.get_active_audio_path()
        if selected_path and os.path.exists(selected_path):
            duration = self.get_file_duration(selected_path)
            if duration is not None:
                self.seek_bar.config(to=duration)
                self.total_duration_label.config(text=self.format_time(duration))
            else:
                self.total_duration_label.config(text="--:--.-")
        else:
            self.seek_bar.config(to=100)
            self.total_duration_label.config(text="00:00.0")

    def get_check_image(self, checked):
        if not hasattr(self, "_check_images"): self._check_images = {}
        if checked not in self._check_images:
            im = Image.new("RGBA", (16, 16), (0,0,0,0))
            for i in range(2, 14): im.putpixel((i, 2), (0,0,0,255)); im.putpixel((i, 13), (0,0,0,255)); im.putpixel((2, i), (0,0,0,255)); im.putpixel((13, i), (0,0,0,255))
            if checked:
                for i in range(3): im.putpixel((5+i, 8+i), (0,0,0,255)); im.putpixel((6+i, 8+i), (0,0,0,255))
                for i in range(4): im.putpixel((7+i, 10-i), (0,0,0,255)); im.putpixel((8+i, 10-i), (0,0,0,255))
            self._check_images[checked] = ImageTk.PhotoImage(im)
        return self._check_images[checked]

    def create_audio_toolbar(self, parent):
        self.play_pause_btn = ttk.Button(parent, text="▶ Play", width=8, command=self.toggle_play_pause); self.play_pause_btn.pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="■ Stop", width=8, command=self.stop_audio).pack(side="left", padx=2, pady=5)
        ttk.Separator(parent, orient='vertical').pack(side='left', fill='y', padx=10, pady=5)
        ttk.Button(parent, text="↩ Undo", command=self.undo).pack(side="left", padx=2, pady=5)
        ttk.Button(parent, text="↪ Redo", command=self.redo).pack(side="left", padx=2, pady=5)

    def create_audio_status_bar(self, parent):
        self.audio_progress_bar = ttk.Progressbar(parent, orient="horizontal", length=100, mode="determinate"); self.audio_progress_bar.pack(fill="x", pady=5, padx=5)
        status_frame = ttk.Frame(parent); status_frame.pack(fill="x", padx=5)
        self.audio_status_label = ttk.Label(status_frame, text="Sẵn sàng", style="Status.TLabel", anchor="w"); self.audio_status_label.pack(side="left", fill="x", expand=True)
        self.audio_open_button = ttk.Button(status_frame, text="Mở thư mục", style="Open.TButton")
        
    def on_audio_tree_click(self, event):
        item_id = self.audio_tree.identify_row(event.y)
        if not item_id: return
        tags = list(self.audio_tree.item(item_id, "tags"))
        if 'checked' in tags: tags.remove('checked'); tags.append('unchecked')
        elif 'unchecked' in tags: tags.remove('unchecked'); tags.append('checked')
        self.audio_tree.item(item_id, tags=tuple(tags))

    def on_audio_tree_select(self, event):
        self.mark_preview_as_dirty(); self.seek_offset = 0.0; self.seek_var.set(0)
        self.current_time_label.config(text="00:00.0")
        selected_path = self.get_active_audio_path()
        if selected_path:
            duration = self.get_file_duration(selected_path)
            if duration is not None:
                self.seek_bar.config(to=duration); self.total_duration_label.config(text=self.format_time(duration))
            else: self.total_duration_label.config(text="--:--.-")
        else: self.total_duration_label.config(text="00:00.0")

    # SỬA: Đổi tên và logic để hoạt động với cả 2 chế độ
    def get_active_audio_path(self):
        if self.audio_batch_mode.get(): # Chế độ Batch
            selection = self.audio_tree.selection()
            if selection:
                item_id = self.audio_tree.focus() or selection[0]
                return self.audio_file_paths.get(item_id)
            return None
        else: # Chế độ Single
            return self.single_audio_path.get()

    def add_audio_files_to_list(self, file_paths):
        new_file_added = False
        for path in file_paths:
            if path not in self.audio_file_paths.values():
                filename = os.path.basename(path)
                item_id = self.audio_tree.insert("", "end", values=(filename,), tags=('unchecked',))
                self.audio_file_paths[item_id] = path; new_file_added = True
        if new_file_added and not self.audio_tree.selection():
             first_item = self.audio_tree.get_children()[0]
             self.audio_tree.selection_set(first_item); self.audio_tree.focus(first_item)

    def add_audio_files_from_folder(self, folder_path):
        audio_files, exts = [], ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts: audio_files.append(entry.path)
        if audio_files: self.add_audio_files_to_list(sorted(audio_files))
        else: messagebox.showinfo("Thông báo", "Không tìm thấy file audio trong thư mục.", parent=self)

    def toggle_all_audio_checks(self, check_state):
        tag = 'checked' if check_state else 'unchecked'
        for iid in self.audio_tree.get_children(): self.audio_tree.item(iid, tags=(tag,))

    def invert_audio_checks(self):
        for iid in self.audio_tree.get_children():
            tags = list(self.audio_tree.item(iid, "tags"))
            if 'checked' in tags: tags.remove('checked'); tags.append('unchecked')
            elif 'unchecked' in tags: tags.remove('unchecked'); tags.append('checked')
            self.audio_tree.item(iid, tags=tuple(tags))
            
    def get_checked_audio_files(self):
        files = []
        for iid in self.audio_tree.get_children():
            if 'checked' in self.audio_tree.item(iid, "tags"): files.append(self.audio_file_paths[iid])
        return files

    def run_batch_export(self, files, output_folder):
        total = len(files); self.audio_progress_bar['maximum'] = total; self.audio_progress_bar['value'] = 0
        state = self.get_current_state()
        for i, path in enumerate(files):
            fname = os.path.basename(path); self.audio_status_label.config(text=f"Đang xử lý {i+1}/{total}: {fname}"); self.update_idletasks()
            out_path = os.path.join(output_folder, fname); command = self.build_ffmpeg_command(path, out_path, state)
            try:
                startupinfo = None
                if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(command, check=True, capture_output=True, startupinfo=startupinfo, text=True, encoding='utf-8')
            except subprocess.CalledProcessError as e:
                print(f"Lỗi xử lý {fname}:\n{e.stderr}"); self.audio_status_label.config(text=f"Lỗi xử lý file: {fname}. Bỏ qua.")
                self.audio_progress_bar['value'] = i + 1; continue
            self.audio_progress_bar['value'] = i + 1
        self.audio_status_label.config(text=f"Hoàn thành! Đã xuất {total} files."); messagebox.showinfo("Hoàn thành", f"Đã xuất thành công {total} files.\nLưu tại: {output_folder}")
        
    def create_video_creator_tab(self, parent):
        self.video_image_path = tk.StringVar(); self.video_audio_path = tk.StringVar(); self.image_list_data = []; self.selected_image_index = -1
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL); paned.pack(expand=True, fill="both")
        left = ttk.Frame(paned, width=450); paned.add(left, weight=2)
        img_f = ttk.LabelFrame(left, text="1. Chọn ảnh", padding="10"); img_f.pack(fill="x", pady=10, padx=5)
        ttk.Entry(img_f, textvariable=self.video_image_path, state="readonly").pack(side="left", fill="x", expand=True)
        aud_f = ttk.LabelFrame(left, text="2. Chọn audio", padding="10"); aud_f.pack(fill="x", pady=10, padx=5)
        ttk.Entry(aud_f, textvariable=self.video_audio_path).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(aud_f, text="Duyệt...", command=lambda: self.browse_generic_file(self.video_audio_path, "audio")).pack(side="left")
        act_f = ttk.Frame(left, padding="10"); act_f.pack(fill="x", pady=20, padx=5)
        ttk.Label(act_f, text="Định dạng:").pack(side="left", padx=(0, 10))
        self.video_format_combo = ttk.Combobox(act_f, values=[".mp4", ".mkv", ".avi", ".mov"], state="readonly", width=10); self.video_format_combo.set(".mp4"); self.video_format_combo.pack(side="left", padx=(0, 20))
        ttk.Button(act_f, text="Tạo Video", command=self.start_video_creation_thread).pack(side="right")
        self.video_progress_bar = ttk.Progressbar(left, orient="horizontal", length=100, mode="determinate"); self.video_progress_bar.pack(fill="x", pady=10, padx=5)
        stat_f = ttk.Frame(left); stat_f.pack(fill="x", pady=(5, 0), padx=5)
        self.video_status_label = ttk.Label(stat_f, text="Sẵn sàng", style="Status.TLabel", anchor="w"); self.video_status_label.pack(side="left", fill="x", expand=True)
        self.video_open_button = ttk.Button(stat_f, text="Mở thư mục", style="Open.TButton")
        right = ttk.Frame(paned); paned.add(right, weight=1)
        img_list_lf = ttk.LabelFrame(right, text="Danh sách ảnh", padding="10"); img_list_lf.pack(expand=True, fill="both", padx=5)
        canv_f = ttk.Frame(img_list_lf); canv_f.pack(expand=True, fill="both")
        self.image_canvas = tk.Canvas(canv_f, bg="white", highlightthickness=0)
        scroll = ttk.Scrollbar(canv_f, orient=tk.VERTICAL, command=self.image_canvas.yview); self.image_canvas.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y"); self.image_canvas.pack(side="left", expand=True, fill="both")
        self.image_canvas.bind("<Configure>", lambda e: self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all")))
        self.image_canvas.bind("<Button-1>", self.on_image_canvas_click)
        self.image_canvas.bind_all("<MouseWheel>", lambda e: self.image_canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        img_btns_f = ttk.Frame(img_list_lf); img_btns_f.pack(fill="x", pady=(5,0))
        ttk.Button(img_btns_f, text="Thêm Ảnh...", command=self.browse_images_for_list).pack(side="left", expand=True, fill="x", padx=(0, 2))
        ttk.Button(img_btns_f, text="Thêm Thư mục...", command=self.browse_image_folder_for_list).pack(side="left", expand=True, fill="x", padx=(2, 2))
        ttk.Button(img_btns_f, text="Xóa hết", command=self.clear_image_list).pack(side="right", padx=(2, 0))

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

    def _create_slider_entry_pair(self, parent, label_text, from_val, to_val, initial_val, unit_text="", is_int=False, precision=2):
        frame = ttk.Frame(parent); frame.pack(fill="x", pady=5, padx=5)
        ttk.Label(frame, text=label_text, width=15).pack(side="left")
        num_var = tk.DoubleVar(value=initial_val)
        num_var.trace_add("write", self.mark_preview_as_dirty)
        def format_val(v): return f"{int(v)}" if is_int else f"{v:.{precision}f}"
        scale = ttk.Scale(frame, from_=from_val, to=to_val, orient="horizontal", variable=num_var); scale.pack(side="left", fill="x", expand=True, padx=(0, 10))
        entry = ttk.Entry(frame, width=10, justify='center'); entry.pack(side="left")
        def update_from_scale(*args): val = num_var.get(); entry.delete(0, tk.END); entry.insert(0, format_val(val))
        def update_from_entry(event=None):
            try: val = float(entry.get()); val = max(from_val, min(to_val, val)); num_var.set(val)
            except (ValueError, TclError): update_from_scale()
            entry.delete(0, tk.END); entry.insert(0, format_val(num_var.get())); frame.focus()
        num_var.trace_add("write", update_from_scale); entry.bind("<Return>", update_from_entry); entry.bind("<FocusOut>", update_from_entry)
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
        file_to_play = self.preview_file_path if self.preview_file_path and os.path.exists(self.preview_file_path) else self.get_active_audio_path()
        if not file_to_play or not os.path.exists(file_to_play): messagebox.showwarning("Chưa có file", "Vui lòng chọn một file âm thanh."); return
        try:
            pygame.mixer.music.load(file_to_play)
            pygame.mixer.music.play(start=self.seek_offset)
            self.play_pause_btn.config(text="❚❚ Pause")
            self.is_paused = False
            self.update_playback_progress()
        except pygame.error as e: messagebox.showerror("Lỗi phát nhạc", f"Không thể phát file: {e}")

    def stop_audio(self):
        pygame.mixer.music.stop(); pygame.mixer.music.unload(); self.play_pause_btn.config(text="▶ Play"); self.is_paused = False
        if self.playback_update_id: self.after_cancel(self.playback_update_id)
        self.seek_var.set(0); self.current_time_label.config(text="00:00.0")

    def on_seek_press(self, event): self.is_seeking = True

    def on_seek_release(self, event):
        if not self.is_seeking: return
        self.is_seeking = False;
        if not self.get_active_audio_path(): return
        self.seek_offset = self.seek_var.get()
        try:
            if pygame.mixer.music.get_busy() or self.is_paused:
                pygame.mixer.music.play(start=self.seek_offset)
                if self.is_paused: pygame.mixer.music.pause()
            self.current_time_label.config(text=self.format_time(self.seek_offset))
        except pygame.error as e: print(f"Lỗi khi tua nhạc: {e}")

    def update_playback_progress(self):
        if pygame.mixer.music.get_busy() and not self.is_paused:
            if not self.is_seeking:
                elapsed_time = pygame.mixer.music.get_pos() / 1000.0; current_pos_sec = self.seek_offset + elapsed_time
                total_duration = self.seek_bar.cget("to")
                if total_duration > 0 and current_pos_sec > total_duration: self.stop_audio(); return
                self.seek_var.set(current_pos_sec); self.current_time_label.config(text=self.format_time(current_pos_sec))
            self.playback_update_id = self.after(100, self.update_playback_progress)
        elif not self.is_paused and self.get_active_audio_path(): self.stop_audio()

    def format_time(self, seconds):
        if seconds < 0: seconds = 0
        mins = int(seconds // 60); secs = seconds % 60; return f"{mins:02d}:{secs:04.1f}"

    def get_current_state(self): return {'speed': self.speed_var.get(),'tempo': self.tempo_var.get(),'pitch': self.pitch_var.get(),'normalize': self.audio_normalize.get(),'noise_reduce': self.audio_noise_reduce.get(),'noise_type': self.noise_type_combo.get(),'noise_amp': self.noise_amp_var.get()}

    def apply_state(self, state):
        self.speed_var.set(state['speed']); self.tempo_var.set(state['tempo']); self.pitch_var.set(state['pitch'])
        self.audio_normalize.set(state['normalize']); self.audio_noise_reduce.set(state['noise_reduce'])
        self.noise_type_combo.set(state['noise_type']); self.noise_amp_var.set(state['noise_amp']); self.mark_preview_as_dirty()

    def save_state(self):
        current_state = self.get_current_state()
        if not self.undo_stack or self.undo_stack[-1] != current_state: self.undo_stack.append(current_state); self.redo_stack.clear()

    def undo(self):
        if len(self.undo_stack) > 1: self.redo_stack.append(self.undo_stack.pop()); self.apply_state(self.undo_stack[-1]); self.audio_status_label.config(text="Đã hoàn tác.")

    def redo(self):
        if self.redo_stack: self.undo_stack.append(self.redo_stack.pop()); self.apply_state(self.undo_stack[-1]); self.audio_status_label.config(text="Đã làm lại.")

    def mark_preview_as_dirty(self, *args): self.is_preview_dirty = True; self.duration_cache = {}; self.stop_audio()

    def browse_main_audio_file(self):
        # SỬA: Chuyển sang chế độ single nếu chưa
        if self.audio_batch_mode.get():
            self.audio_batch_mode.set(False)
            self.toggle_audio_batch_mode()
        self.browse_generic_file(self.single_audio_path, "audio")

    def browse_main_audio_folder(self):
        # SỬA: Chuyển sang chế độ batch nếu chưa
        if not self.audio_batch_mode.get():
            self.audio_batch_mode.set(True)
            self.toggle_audio_batch_mode()
        folder_path = filedialog.askdirectory(title="Chọn thư mục âm thanh")
        if folder_path: self.add_audio_files_from_folder(folder_path)

    def browse_generic_file(self, path_var, file_type):
        types = {"image": [("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")], "audio": [("Audio Files", "*.mp3 *.wav *.aac *.flac *.opus *.ogg *.m4a"), ("All files", "*.*")]}
        path = filedialog.askopenfilename(title=f"Chọn file {file_type}", filetypes=types.get(file_type))
        if path: path_var.set(path)

    def handle_global_drop(self, event):
        filepaths = self.tk.splitlist(event.data)
        current_tab_index = self.notebook.index(self.notebook.select())
        
        is_folder_drop = len(filepaths) == 1 and os.path.isdir(filepaths[0])
        
        if current_tab_index == 0: # Tab Sửa nhạc
            if is_folder_drop: # Nếu thả thư mục
                if not self.audio_batch_mode.get(): # Chuyển sang batch nếu đang single
                    self.audio_batch_mode.set(True)
                    self.toggle_audio_batch_mode()
                self.add_audio_files_from_folder(filepaths[0])
            else: # Nếu thả file
                audio_files = [p for p in filepaths if os.path.splitext(p)[1].lower() in ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']]
                if not audio_files: return
                if self.audio_batch_mode.get():
                    self.add_audio_files_to_list(audio_files)
                else: # Đang ở chế độ single, chỉ lấy file đầu tiên
                    self.single_audio_path.set(audio_files[0])
            return

        if current_tab_index == 1: # Tab Tạo video
            if is_folder_drop:
                self.add_images_from_folder(filepaths[0])
            else:
                image_files = [p for p in filepaths if os.path.splitext(p)[1].lower() in ['.jpg', '.jpeg', '.png', '.bmp']]
                audio_files = [p for p in filepaths if os.path.splitext(p)[1].lower() in ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']]
                if image_files: self.add_images_to_list(image_files)
                if audio_files: self.video_audio_path.set(audio_files[0])
            return

        if current_tab_index == 2: # Tab Xử lý nhanh
            if is_folder_drop:
                self.select_quick_folder(filepaths[0])
            return
            
    def get_file_duration(self, file_path):
        if file_path in self.duration_cache: return self.duration_cache[file_path]
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        try:
            startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(command, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            duration = float(result.stdout.strip())
            self.duration_cache[file_path] = duration
            return duration
        except Exception: return None

    def open_folder_and_select_file(self, path):
        if not os.path.exists(path): messagebox.showerror("Lỗi", "File không tồn tại."); return
        try:
            if sys.platform == "win32": subprocess.run(['explorer', '/select,', os.path.normpath(path)])
            elif sys.platform == "darwin": subprocess.run(['open', '-R', path])
            else: subprocess.run(['xdg-open', os.path.dirname(path)])
        except Exception as e: messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")

    def build_ffmpeg_command(self, input_path, output_path, state_dict=None):
        state = state_dict or self.get_current_state()
        command, main_chain = ['ffmpeg', '-i', input_path], []
        original_rate = 44100
        try:
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=sample_rate', '-of', 'default=noprint_wrappers=1:nokey=1', input_path]
            startupinfo = None
            if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            original_rate = int(result.stdout.strip())
        except Exception: pass
        p = 2**(state['pitch']/12.0); s = state['speed']; t = state['tempo']
        if abs(p * s - 1.0) > 1e-6: main_chain.append(f"asetrate={original_rate*p*s}")
        if main_chain: main_chain.append(f"aresample={original_rate}")
        if abs(t - 1.0) > 1e-6:
            while t < 0.5: main_chain.append("atempo=0.5"); t /= 0.5
            main_chain.append(f"atempo={t}")
        if state.get('normalize'): main_chain.append("dynaudnorm")
        if state.get('noise_reduce'): main_chain.append("anlmdn")
        if state.get('noise_type') != "Không":
            nc = {"Nhiễu trắng": "white", "Nhiễu hồng": "pink", "Nhiễu nâu": "brown"}[state['noise_type']]
            cs = ",".join(main_chain) if main_chain else "anull"
            dur = self.get_file_duration(input_path) or 60
            fc = f"[0:a:0]{cs}[main];anoisesrc=c={nc}:a={state['noise_amp']}:d={dur}[noise];[main][noise]amix=inputs=2:duration=first[out]"
            command.extend(['-filter_complex', fc, '-map', '[out]'])
        elif main_chain: command.extend(['-af', ",".join(main_chain)])
        elif os.path.splitext(output_path)[1].lower() == '.wav': command.extend(['-c:a', 'pcm_s16le'])
        command.extend(['-y', output_path]); return command

    def start_preview_generation(self, callback=None):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy."); return
        audio_file = self.get_active_audio_path()
        if not (audio_file and os.path.exists(audio_file)): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh."); return
        self.save_state()
        self.preview_file_path = os.path.join(TEMP_DIR, f"preview_{os.path.basename(audio_file)}.wav")
        command = self.build_ffmpeg_command(audio_file, self.preview_file_path)
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, audio_file, self.preview_file_path, True, self.audio_progress_bar, self.audio_status_label, self.audio_open_button, callback), daemon=True); self.active_thread.start()

    # SỬA: Cập nhật để xử lý cả 2 chế độ
    def export_audio(self):
        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy."); return

        if self.audio_batch_mode.get(): # Chế độ Batch
            checked_files = self.get_checked_audio_files()
            if not checked_files:
                messagebox.showerror("Lỗi", "Vui lòng tích chọn ít nhất một file để xuất."); return
            output_folder = filedialog.askdirectory(title="Chọn thư mục lưu các files")
            if not output_folder: return
            self.active_thread = threading.Thread(target=self.run_batch_export, args=(checked_files, output_folder), daemon=True)
            self.active_thread.start()
        else: # Chế độ Single
            input_file = self.get_active_audio_path()
            if not (input_file and os.path.exists(input_file)):
                messagebox.showerror("Thiếu thông tin", "Vui lòng chọn một file âm thanh hợp lệ."); return
            
            output_path = filedialog.asksaveasfilename(
                title="Lưu file audio",
                initialfile=os.path.basename(input_file),
                defaultextension=".mp3",
                filetypes=[("MP3 Audio", "*.mp3"), ("WAV Audio", "*.wav"), ("FLAC Audio", "*.flac"), ("All Files", "*.*")]
            )
            if not output_path: return
            
            command = self.build_ffmpeg_command(input_file, output_path)
            self.active_thread = threading.Thread(
                target=self.run_generic_process, 
                args=(command, input_file, output_path, False, self.audio_progress_bar, self.audio_status_label, self.audio_open_button), 
                daemon=True
            )
            self.active_thread.start()


    def start_video_creation_thread(self):
        if self.active_thread and self.active_thread.is_alive(): messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy."); return
        img_f, aud_f = self.video_image_path.get(), self.video_audio_path.get()
        if not all([img_f, aud_f, os.path.exists(img_f), os.path.exists(aud_f)]): messagebox.showerror("Thiếu thông tin", "Vui lòng chọn file ảnh và âm thanh hợp lệ."); return
        output_path = filedialog.asksaveasfilename(initialfile=os.path.splitext(os.path.basename(aud_f))[0], title="Lưu video", defaultextension=self.video_format_combo.get())
        if not output_path: return
        command = ['ffmpeg', '-loop', '1', '-i', img_f, '-i', aud_f, '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', '-shortest', '-y', output_path]
        self.active_thread = threading.Thread(target=self.run_generic_process, args=(command, aud_f, output_path, False, self.video_progress_bar, self.video_status_label, self.video_open_button), daemon=True); self.active_thread.start()

    def run_generic_process(self, command, input_file, output_path, is_preview, progress_bar, status_label, open_button, callback=None):
        progress_bar['value'] = 0
        open_button.pack_forget()
        status_label.config(text="Đang lấy thông tin...")
        self.update_idletasks()
        
        total_duration = self.get_file_duration(input_file)
        if total_duration is None:
            status_label.config(text="Lỗi: Không thể đọc thời lượng.")
            return
            
        status_label.config(text="Bắt đầu xử lý...")
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
        
        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        state = self.get_current_state()
        tempo, speed = (state['tempo'], state['speed']) if is_preview else (1.0, 1.0)
        output_duration = total_duration / speed / tempo if (speed * tempo) != 0 else total_duration
        
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
                if callback:
                    self.after(0, callback) # Sửa lỗi thụt lề ở đây
            else:
                open_button.config(command=lambda: self.open_folder_and_select_file(output_path))
                open_button.pack(side="right", padx=(5, 0))
                if output_path.lower().endswith(('.mp3', '.wav', '.flac', '.opus', '.m4a')):
                    # SỬA: Tự động chuyển qua tab Sửa Nhạc nếu đang ở chế độ single
                    if self.notebook.index(self.notebook.select()) != 0:
                         self.video_audio_path.set(output_path)
                         self.notebook.select(self.video_creator_tab)
                    else:
                        if not self.audio_batch_mode.get():
                            self.single_audio_path.set(output_path)

        else:
            status_label.config(text="Xử lý thất bại! Kiểm tra console.")
            print("="*60)
            print("LỖI FFMPEG:")
            print(f"  {' '.join(command)}")
            print("\nThông báo lỗi (dòng cuối):")
            for out_line in output_buffer:
                print(out_line, end='')
            print("\n" + "="*60)

    def select_quick_folder(self, folder_path=None):
        if not folder_path: folder_path = filedialog.askdirectory(title="Chọn thư mục nguồn")
        if not folder_path: return
        self.quick_input_folder.set(folder_path); self.quick_listbox.delete(0, tk.END)
        audio_files = []
        supported_exts = ['.mp3', '.wav', '.aac', '.flac', '.opus', '.ogg', '.m4a']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in supported_exts: audio_files.append(entry.path)
        for f in sorted(audio_files): self.quick_listbox.insert(tk.END, os.path.basename(f))
        self.quick_file_count_label.config(text=f" ({len(audio_files)} files)")

    def select_quick_output_folder(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục lưu")
        if folder_path: self.quick_output_folder.set(folder_path)
    
    def start_quick_process(self):
        """
        Bắt đầu quá trình xử lý hàng loạt trong tab "Xử lý nhanh".
        Hàm này lấy dữ liệu từ UI và khởi chạy `run_quick_process` trong một luồng riêng.
        """
        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Đang xử lý", "Một tác vụ khác đang chạy.", parent=self)
            return

        input_folder = self.quick_input_folder.get()
        output_folder = self.quick_output_folder.get()
        filenames = self.quick_listbox.get(0, tk.END)

        if not input_folder or not output_folder:
            messagebox.showerror("Thiếu thông tin", "Vui lòng chọn cả thư mục nguồn và thư mục lưu.", parent=self)
            return
        if not filenames:
            messagebox.showerror("Không có file", "Không có file nào trong danh sách để xử lý.", parent=self)
            return
            
        if not os.path.isdir(output_folder):
            if messagebox.askyesno("Tạo thư mục?", f"Thư mục '{os.path.basename(output_folder)}' không tồn tại.\nBạn có muốn tạo nó không?", parent=self):
                try:
                    os.makedirs(output_folder)
                except OSError as e:
                    messagebox.showerror("Lỗi", f"Không thể tạo thư mục:\n{e}", parent=self)
                    return
            else:
                return 

        self.active_thread = threading.Thread(
            target=self.run_quick_process,
            args=(input_folder, output_folder, filenames),
            daemon=True
        )
        self.active_thread.start()
    
    def run_quick_process(self, input_folder, output_folder, filenames):
        self.quick_progress_bar['maximum'] = len(filenames); self.quick_progress_bar['value'] = 0
        preset = self.quick_preset_var.get(); add_noise = self.quick_noise_var.get(); normalize = self.quick_normalize_var.get()
        state = {'speed': 1.0, 'tempo': 1.0, 'pitch': 0.0, 'normalize': normalize, 'noise_reduce': False, 'noise_type': 'Không', 'noise_amp': 0.0}
        if preset == "speed_up": state['speed'] = 1.005
        elif preset == "speed_down": state['speed'] = 0.990
        if add_noise: state['noise_type'] = "Nhiễu trắng"; state['noise_amp'] = 0.0005
        for i, filename in enumerate(filenames):
            self.quick_status_label.config(text=f"Đang xử lý {i+1}/{len(filenames)}: {filename}"); self.quick_progress_bar['value'] = i; self.update_idletasks()
            in_path = os.path.join(input_folder, filename); out_path = os.path.join(output_folder, filename); command = self.build_ffmpeg_command(in_path, out_path, state)
            try:
                startupinfo = None
                if sys.platform == "win32": startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(command, check=True, capture_output=True, startupinfo=startupinfo, text=True, encoding='utf-8')
            except subprocess.CalledProcessError as e: print(f"Lỗi xử lý {filename}:\n{e.stderr}"); self.quick_status_label.config(text=f"Lỗi xử lý file: {filename}. Bỏ qua."); continue
        self.quick_progress_bar['value'] = len(filenames); self.quick_status_label.config(text=f"Hoàn thành! Đã xử lý {len(filenames)} files."); messagebox.showinfo("Hoàn thành", f"Đã xử lý {len(filenames)} files.\nLưu tại: {output_folder}")

    def browse_images_for_list(self):
        paths = filedialog.askopenfilenames(title="Chọn ảnh", filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")])
        if paths: self.add_images_to_list(paths)

    def browse_image_folder_for_list(self):
        folder_path = filedialog.askdirectory(title="Chọn thư mục ảnh")
        if folder_path: self.add_images_from_folder(folder_path)

    def add_images_from_folder(self, folder_path):
        image_paths, exts = [], ['.jpg', '.jpeg', '.png', '.bmp']
        for entry in os.scandir(folder_path):
            if entry.is_file() and os.path.splitext(entry.name)[1].lower() in exts: image_paths.append(entry.path)
        if image_paths: self.add_images_to_list(image_paths)
        else: messagebox.showinfo("Thông báo", "Không tìm thấy file ảnh.", parent=self)

    def add_images_to_list(self, paths):
        for path in paths:
            if path not in self.image_list_data: self.image_list_data.append(path)
        self.update_image_list_display()

    def clear_image_list(self): self.image_list_data.clear(); self.video_image_path.set(""); self.selected_image_index = -1; self.update_image_list_display()

    def on_image_canvas_click(self, event):
        canvas_y = self.image_canvas.canvasy(event.y); item_height = 68; clicked_index = int(canvas_y // item_height)
        if 0 <= clicked_index < len(self.image_list_data):
            if self.selected_image_index != -1: self.update_image_selection_bg(self.selected_image_index, "white")
            self.selected_image_index = clicked_index
            self.video_image_path.set(self.image_list_data[self.selected_image_index]); self.update_image_selection_bg(self.selected_image_index, "#E0E8F0")

    def update_image_selection_bg(self, index, color):
        item_height = 68; y0 = 2 + (index * item_height)
        rect_id = self.image_canvas.find_closest(2, y0 + 2)[0]; self.image_canvas.itemconfig(rect_id, fill=color)

    def update_image_list_display(self):
        self.image_canvas.delete("all"); self.image_thumbnails.clear()
        y_pos, thumb_size, item_height = 2, (64, 64), 68
        for i, path in enumerate(self.image_list_data):
            try:
                img = Image.open(path); img.thumbnail(thumb_size, Image.Resampling.LANCZOS); photo_img = ImageTk.PhotoImage(img)
                self.image_thumbnails.append(photo_img)
                bg_color = "#E0E8F0" if i == self.selected_image_index else "white"
                self.image_canvas.create_rectangle(0, y_pos - 2, self.image_canvas.winfo_width(), y_pos + item_height - 2, fill=bg_color, outline="", tags=f"bg_{i}")
                self.image_canvas.create_image(4, y_pos, anchor="nw", image=photo_img)
                self.image_canvas.create_text(thumb_size[0] + 10, y_pos + item_height / 2, anchor="w", text=os.path.basename(path), font=("Segoe UI", 9))
                y_pos += item_height
            except Exception as e: print(f"Lỗi tải thumbnail cho {path}: {e}")
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox("all"))

if __name__ == "__main__":
    app = FfmpegGuiApp()
    app.mainloop()