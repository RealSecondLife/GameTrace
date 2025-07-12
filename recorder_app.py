import os
import sys
import time
import json
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import subprocess
from pynput import keyboard, mouse
import ctypes
import datetime
import shutil
import re
import tkinter.ttk as ttk

video_filename = "screen_recording.mp4"
event_filename = "events.jsonl"
ffmpeg_process = None
recording = False
# ffmpeg_path_var = None  # 新增全局变量
storage_path_var = None  # 新增全局变量
resolution_var = None  # 新增全局变量，用于记录录制质量

# 获取临时文件名
def generate_filename():
    now = datetime.datetime.now()
    return now.strftime("record_%Y%m%d_%H%M%S")

def get_screen_size():
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height

# 获取 ffmpeg 跂径，注意只能获取本地的
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        local_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
    if os.path.exists(local_path):
        return local_path
    return ""

def write_event(event):
    with open(event_filename, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

############################## 鼠标键盘事件录制
def start_input_listeners():
    def on_key_press(key):
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)
        write_event({"type": "key_press", "key": key_str, "time": time.time()})

    def on_key_release(key):
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)
        write_event({"type": "key_release", "key": key_str, "time": time.time()})

    def on_click(x, y, button, pressed):
        write_event({
            "type": "mouse_press" if pressed else "mouse_release",
            "position": (x, y),
            "button": str(button),
            "time": time.time()
        })
    
    def on_move(x, y):
        write_event({
            "type": "mouse_move",
            "position": (x, y),
            "time": time.time()
        })

    threading.Thread(target=lambda: keyboard.Listener(on_press=on_key_press, on_release=on_key_release).run(), daemon=True).start()
    threading.Thread(target=lambda: mouse.Listener(on_click=on_click, on_move=on_move).run(), daemon=True).start()

############################## 录制分辨率选择
def get_resolution_scale(resolution, screen_width, screen_height):
    """
    返回对应的视频尺寸 (width, height)
    如果用户选择的分辨率高于当前屏幕分辨率，则返回屏幕原生分辨率
    """
    resolutions = {
        "无损": None,     # 不缩放，保持原生分辨率
        "4K": (3840, 2160),
        "2K": (2560, 1440),
        "1080p": (1920, 1080),
        "720p": (1280, 720),
        "480p": (854, 480)
    }
    
    scale_size = resolutions.get(resolution, None)

    if scale_size:
        target_width, target_height = scale_size
        # 如果用户选择的分辨率大于屏幕，就用屏幕分辨率
        if target_width > screen_width or target_height > screen_height:
            return (screen_width, screen_height)
        else:
            return (target_width, target_height)
    else:
        # 无损模式：直接返回屏幕分辨率
        scale_size = (screen_width, screen_height)
        return (scale_size, screen_width, screen_height)

############################## 音频录制
def list_audio_devices():
    """
    返回所有可用的dshow音频设备列表
    """
    try:
        proc = subprocess.Popen(
            [get_ffmpeg_path(), '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        _, stderr = proc.communicate(timeout=5)
        devices = []
        audio_section = False
        for line in stderr.splitlines():
            # 只匹配音频设备
            m = re.search(r'\[dshow @ [^\]]+\] +\"(.+?)\"', line)
            if m and 'audio devices' in line.lower():
                devices.clear()  # 新一组音频设备
            elif m:
                devices.append(m.group(1))
        final_devices = []
        # 优先选立体声混音
        for dev in devices:
            if '立体声混音' in dev or 'stereo mix' in dev.lower():
                final_devices.append(dev)
        # 再选扬声器
        for dev in devices:
            if '扬声器' in dev or 'speaker' in dev.lower():
                final_devices.append(dev)
        return final_devices
    except Exception as e:
        print("音频设备枚举失败：", e)
        return []

# 直接返回界面选择的音频设备
def get_speaker_device():
    global audio_device_var
    return audio_device_var.get()


############################## 屏幕录制
def start_recording():
    global ffmpeg_process, recording, video_filename, event_filename
    if recording:
        return
    
    # 获取ffmpeg路径
    ffmpeg_path = get_ffmpeg_path()
    
    # 已在create_ui位置检查ffmpeg是否存在
    # if not os.path.exists(ffmpeg_path):
    #     messagebox.showwarning("未能找到 ffmpeg.exe，请联系开发者获取完整打包的exe文件")
    #     return
    
    # 检查音频设备是否已选择
    if not audio_device_var.get():
        messagebox.showwarning("警告", "请先启用“立体声混音”设备（控制面板 > 声音设置 > 录音设备中启用），然后选择一个音频输入设备。")
        return

    # 检查输出路径是否已选择
    storage_path = get_storage_path()
    if not storage_path:
        messagebox.showwarning("警告", "请先选择一个有效的存储文件夹！")
        return

    base_name = generate_filename()
    # video_filename = os.path.join(storage_path, f"{base_name}.m4a")
    video_filename = os.path.join(storage_path, f"{base_name}.mp4")
    event_filename = os.path.join(storage_path, f"{base_name}.jsonl")

    # 删除同名文件
    for f in [video_filename, event_filename]:
        if os.path.exists(f):
            os.remove(f)

    # 获取屏幕长宽与音频信息
    screen_width, screen_height = get_screen_size()
    speaker_device = get_speaker_device()

    # 获取用户选择的分辨率
    selected_resolution = resolution_var.get()
    scale_size, target_width, target_height = get_resolution_scale(selected_resolution, screen_width, screen_height)
    
    if (target_width, target_height) != scale_size and scale_size != None:
        messagebox.showinfo("提示", f"您选择的 {selected_resolution} 分辨率高于当前屏幕支持，已自动适配为 {screen_width}x{screen_height}")

    # 构建 ffmpeg 命令
    ffmpeg_cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'gdigrab',
        '-framerate', '24',
        '-video_size', f'{screen_width}x{screen_height}',
        '-i', 'desktop',
        '-f', 'dshow',
        '-i', f'audio={speaker_device}',
        '-vf', f'scale={target_width}:{target_height}',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '18',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'libmp3lame', '-b:a', '192k',
        video_filename
    ]

    ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    recording = True
    status_var.set("录制中...")
    start_input_listeners()

def stop_recording():
    global ffmpeg_process, recording
    if not recording:
        return
    recording = False
    status_var.set("正在结束录制...")

    def finalize():
        if ffmpeg_process:
            try:
                ffmpeg_process.stdin.write(b'q')
                ffmpeg_process.stdin.flush()
                ffmpeg_process.wait()
            except Exception as e:
                print("关闭 ffmpeg 失败:", e)
        status_var.set("录制完成 ✔")
        messagebox.showinfo("录制结束", f"✅ 视频保存为：{video_filename}\n🖱️ 键鼠事件记录：{event_filename}")
        app.quit()  # 录制结束后退出主程序

    threading.Thread(target=finalize).start()

# def browse_ffmpeg():
#     path = filedialog.askopenfilename(
#         title="请选择 ffmpeg.exe",
#         filetypes=[("ffmpeg 可执行文件", "ffmpeg.exe"), ("所有文件", "*.*")]
#     )
#     if path:
#         ffmpeg_path_var.set(path)
#         ffmpeg_status_var.set("已选择 ffmpeg 路径")
#     else:
#         if not ffmpeg_path_var.get():
#             ffmpeg_status_var.set("未能自动找到 ffmpeg，请手动选择")

# def auto_fill_ffmpeg_path():
#     # 自动查找并填入
#     if getattr(sys, 'frozen', False):
#         local_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
#     else:
#         local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
#     if os.path.exists(local_path):
#         ffmpeg_path_var.set(local_path)
#         ffmpeg_status_var.set("已在本地路径中找到 ffmpeg")
#         return
#     ffmpeg_in_path = shutil.which("ffmpeg")
#     if ffmpeg_in_path:
#         ffmpeg_path_var.set(ffmpeg_in_path)
#         ffmpeg_status_var.set("已在系统PATH中找到 ffmpeg")
#         return
#     ffmpeg_path_var.set("")
#     ffmpeg_status_var.set("未能自动找到 ffmpeg.exe，请手动选择")

# def get_storage_path():
#     if storage_path_var is not None:
#         path = storage_path_var.get()
#         if os.path.isdir(path):
#             return path
#     # 默认 data 文件夹
#     default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
#     if not os.path.exists(default_path):
#         os.makedirs(default_path)
#     return default_path

# 默认选择路径为空
def get_storage_path():
    if storage_path_var is not None:
        path = storage_path_var.get()
        if os.path.isdir(path):
            return path
    return ""  # 默认为空

def browse_storage_path():
    path = filedialog.askdirectory(
        title="请选择存储文件夹"
    )
    if path:
        storage_path_var.set(path)

def create_gui():
    global status_var, storage_path_var, app, audio_device_var, resolution_var

    # 启动时检查 ffmpeg 是否存在
    ffmpeg_path = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        messagebox.showerror("错误", "未找到 ffmpeg.exe，请将其放在程序所在目录下。")
        sys.exit(1)

    app = tk.Tk()
    app.title("游戏录制器")
    app.geometry("600x360")
    app.resizable(False, False)

    main_frame = tk.Frame(app)
    main_frame.place(relx=0.5, rely=0.5, anchor="center")

    # ffmpeg 路径
    # ffmpeg_path_var = tk.StringVar()
    # ffmpeg_status_var = tk.StringVar()
    # auto_fill_ffmpeg_path()
    # tk.Label(main_frame, text="ffmpeg 路径（可自动识别/手动选择）", font=("Arial", 12), anchor="w", justify="left").pack(anchor="w", padx=24, pady=(18, 0))
    # ffmpeg_row = tk.Frame(main_frame)
    # ffmpeg_row.pack(fill=tk.X, padx=18, pady=(2, 0))
    # ffmpeg_entry = tk.Entry(ffmpeg_row, textvariable=ffmpeg_path_var, width=54, font=("Arial", 11))
    # ffmpeg_entry.pack(side=tk.LEFT, padx=(0, 6))
    # tk.Button(ffmpeg_row, text="浏览...", font=("Arial", 11), width=8, command=browse_ffmpeg).pack(side=tk.LEFT)
    
    # 存储路径
    storage_path_var = tk.StringVar()
    # default_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    # if not os.path.exists(default_data_path):
    #     os.makedirs(default_data_path)
    # storage_path_var.set(default_data_path)
    storage_path_var.set("")  # 修改,初始化路径为空
    tk.Label(main_frame, text="存储路径（默认 data 文件夹，可更改）", font=("Arial", 12), anchor="w", justify="left").pack(anchor="w", padx=24, pady=(14, 0))
    storage_row = tk.Frame(main_frame)
    storage_row.pack(fill=tk.X, padx=18, pady=(2, 0))
    storage_entry = tk.Entry(storage_row, textvariable=storage_path_var, width=54, font=("Arial", 11))
    storage_entry.pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(storage_row, text="浏览...", font=("Arial", 11), width=8, command=browse_storage_path).pack(side=tk.LEFT)

    # 音频设备选择
    tk.Label(main_frame, text="音频输入设备（可选）", font=("Arial", 12), anchor="w").pack(anchor="w", padx=24, pady=(14, 0))
    audio_device_var = tk.StringVar()
    audio_devices = list_audio_devices()
    if audio_devices:
        audio_device_var.set(audio_devices[0])
    else:
        audio_device_var.set("")
    audio_combo = ttk.Combobox(main_frame, textvariable=audio_device_var, values=audio_devices, font=("Arial", 11), width=52, state="readonly")
    audio_combo.pack(padx=24, pady=(2, 0))

    # 分辨率选择
    tk.Label(main_frame, text="录制分辨率", font=("Arial", 12), anchor="w").pack(anchor="w", padx=24, pady=(14, 0))
    resolution_var = tk.StringVar(value="无损")  # 默认值
    resolutions = ["无损", "2K", "1080p", "720p", "480p"]
    resolution_combo = ttk.Combobox(main_frame, textvariable=resolution_var, values=resolutions, font=("Arial", 11), width=52, state="readonly")
    resolution_combo.pack(padx=24, pady=(2, 0))

    # 状态栏
    status_var = tk.StringVar()
    status_var.set("准备就绪")
    tk.Label(main_frame, textvariable=status_var, font=("Arial", 12), anchor="w").pack(fill=tk.X, pady=(18, 0), padx=18)

    # 录制按钮行
    btn_row = tk.Frame(main_frame)
    btn_row.pack(pady=(18, 0))
    tk.Button(btn_row, text="开始录制", font=("Arial", 14), width=16, command=start_recording).pack(side=tk.LEFT, padx=18)
    tk.Button(btn_row, text="停止录制", font=("Arial", 14), width=16, command=stop_recording).pack(side=tk.LEFT, padx=18)

    app.mainloop()

if __name__ == "__main__":
    create_gui()
