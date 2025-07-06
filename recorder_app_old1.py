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
ffmpeg_path_var = None  # 新增全局变量
storage_path_var = None  # 新增全局变量

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

# 获取 ffmpeg 跂径,如果本地路径没有则在系统 PATH 中查找
def get_ffmpeg_path():
    # 优先用界面上的路径
    if ffmpeg_path_var is not None:
        path = ffmpeg_path_var.get()
        if os.path.exists(path):
            return path
    # 自动查找
    if getattr(sys, 'frozen', False):
        local_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
    if os.path.exists(local_path):
        return local_path
    # 检查系统PATH
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        return ffmpeg_in_path
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


############################## 屏幕录制
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

# def get_speaker_device():
#     """
#     自动检测dshow下的扬声器设备名称，优先包含'立体声混音'、'stereo mix'、'speaker'或'扬声器'的设备
#     """
#     try:
#         result = subprocess.run(
#             [get_ffmpeg_path(), '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True,
#             encoding='utf-8'
#         )
#         devices = []
#         for line in result.stderr.splitlines():
#             # 只匹配音频设备
#             m = re.search(r'\[dshow @ [^\]]+\] +\"(.+?)\"', line)
#             if m and 'audio devices' in line.lower():
#                 devices.clear()  # 新一组音频设备
#             elif m:
#                 devices.append(m.group(1))
#         # 优先选立体声混音
#         for dev in devices:
#             if '立体声混音' in dev or 'stereo mix' in dev.lower():
#                 return dev
#         # 再选扬声器
#         for dev in devices:
#             if '扬声器' in dev or 'speaker' in dev.lower():
#                 return dev
#         # 若没有，返回第一个音频设备
#         if devices:
#             return devices[0]
#     except Exception as e:
#         print("自动检测扬声器失败：", e)
#     # 没有检测到任何音频设备时返回空字符串
#     return ''

# 直接返回界面选择的音频设备
def get_speaker_device():
    global audio_device_var
    return audio_device_var.get()


def start_recording():
    global ffmpeg_process, recording, video_filename, event_filename
    if recording:
        return
    ffmpeg_path = get_ffmpeg_path()
    if not os.path.exists(ffmpeg_path):
        ffmpeg_status_var.set("未能找到 ffmpeg.exe，请手动选择")
        return
    
    # 检查音频设备是否已选择
    if not audio_device_var.get():
        messagebox.showwarning("警告", "请先打开电脑的“立体声混音”功能，再先选择一个音频输入设备！")
        return

    storage_path = get_storage_path()
    base_name = generate_filename()
    # video_filename = os.path.join(storage_path, f"{base_name}.m4a")
    video_filename = os.path.join(storage_path, f"{base_name}.mp4")
    event_filename = os.path.join(storage_path, f"{base_name}.jsonl")

    # 删除同名文件
    for f in [video_filename, event_filename]:
        if os.path.exists(f):
            os.remove(f)

    width, height = get_screen_size()
    speaker_device = get_speaker_device()

    # 录制压缩版视频
    # ffmpeg_cmd = [
    #     ffmpeg_path,
    #     '-y',
    #     '-f', 'gdigrab',
    #     '-framerate', '12',
    #     '-video_size', f'{width}x{height}',
    #     '-i', 'desktop',
    #     '-f', 'dshow',
    #     '-i', f'audio={speaker_device}',
    #     # '-vf', 'format=yuv420p,scale=854:480', # 分辨率854:480(480p) 
    #     '-vf', 'format=yuv420p,scale=1920:1080', # 分辨率854:480(480p) 
    #     '-c:v', 'libx264',
    #     '-preset', 'ultrafast',
    #     '-crf', '23',
    #     # '-c:a', 'flac',  # 无损音频
    #     '-c:a', 'libmp3lame', '-b:a', '128k', # mp3
    #     video_filename
    # ]
    
    ffmpeg_cmd = [
        ffmpeg_path,
        '-y',
        '-f', 'gdigrab',
        '-framerate', '12',  # 可以提高到 30，看 CPU 承受能力
        '-video_size', f'{width}x{height}',
        '-i', 'desktop',
        '-f', 'dshow',
        '-i', f'audio={speaker_device}',
        '-vf', 'format=yuv444p',  # 更高质量像素格式
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '0',  # 0 表示无损压缩
        '-pix_fmt', 'yuv444p',
        '-c:a', 'libmp3lame', '-b:a', '192k',  # 可选更高音频比特率
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

def browse_ffmpeg():
    path = filedialog.askopenfilename(
        title="请选择 ffmpeg.exe",
        filetypes=[("ffmpeg 可执行文件", "ffmpeg.exe"), ("所有文件", "*.*")]
    )
    if path:
        ffmpeg_path_var.set(path)
        ffmpeg_status_var.set("已选择 ffmpeg 路径")
    else:
        if not ffmpeg_path_var.get():
            ffmpeg_status_var.set("未能自动找到 ffmpeg，请手动选择")

def auto_fill_ffmpeg_path():
    # 自动查找并填入
    if getattr(sys, 'frozen', False):
        local_path = os.path.join(sys._MEIPASS, "ffmpeg.exe")
    else:
        local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")
    if os.path.exists(local_path):
        ffmpeg_path_var.set(local_path)
        ffmpeg_status_var.set("已在本地路径中找到 ffmpeg")
        return
    ffmpeg_in_path = shutil.which("ffmpeg")
    if ffmpeg_in_path:
        ffmpeg_path_var.set(ffmpeg_in_path)
        ffmpeg_status_var.set("已在系统PATH中找到 ffmpeg")
        return
    ffmpeg_path_var.set("")
    ffmpeg_status_var.set("未能自动找到 ffmpeg.exe，请手动选择")

def get_storage_path():
    if storage_path_var is not None:
        path = storage_path_var.get()
        if os.path.isdir(path):
            return path
    # 默认 data 文件夹
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if not os.path.exists(default_path):
        os.makedirs(default_path)
    return default_path

def browse_storage_path():
    path = filedialog.askdirectory(
        title="请选择存储文件夹"
    )
    if path:
        storage_path_var.set(path)

def create_gui():
    global status_var, ffmpeg_path_var, ffmpeg_status_var, storage_path_var, app, audio_device_var

    app = tk.Tk()
    app.title("游戏录制器")
    app.geometry("600x360")
    app.resizable(False, False)

    main_frame = tk.Frame(app)
    main_frame.place(relx=0.5, rely=0.5, anchor="center")

    # ffmpeg 路径
    ffmpeg_path_var = tk.StringVar()
    ffmpeg_status_var = tk.StringVar()
    auto_fill_ffmpeg_path()
    tk.Label(main_frame, text="ffmpeg 路径（可自动识别/手动选择）", font=("Arial", 12), anchor="w", justify="left").pack(anchor="w", padx=24, pady=(18, 0))
    ffmpeg_row = tk.Frame(main_frame)
    ffmpeg_row.pack(fill=tk.X, padx=18, pady=(2, 0))
    ffmpeg_entry = tk.Entry(ffmpeg_row, textvariable=ffmpeg_path_var, width=54, font=("Arial", 11))
    ffmpeg_entry.pack(side=tk.LEFT, padx=(0, 6))
    tk.Button(ffmpeg_row, text="浏览...", font=("Arial", 11), width=8, command=browse_ffmpeg).pack(side=tk.LEFT)
    
    # 存储路径
    storage_path_var = tk.StringVar()
    default_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if not os.path.exists(default_data_path):
        os.makedirs(default_data_path)
    storage_path_var.set(default_data_path)
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
