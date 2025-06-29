import os
import sys
import time
import json
import tkinter as tk
from tkinter import messagebox
import threading
import subprocess
from pynput import keyboard, mouse
import ctypes
import datetime


video_filename = "screen_recording.mp4"
event_filename = "events.jsonl"
ffmpeg_process = None
recording = False

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

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(sys._MEIPASS, "ffmpeg.exe")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg.exe")

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
def start_recording():
    global ffmpeg_process, recording, video_filename, event_filename
    if recording:
        return
    if not os.path.exists(get_ffmpeg_path()):
        messagebox.showerror("错误", "找不到 ffmpeg.exe，请将其放在程序目录下")
        return
    
    base_name = generate_filename()
    video_filename = f"{base_name}.mp4"
    event_filename = f"{base_name}.jsonl"

    # 删除同名文件
    for f in [video_filename, event_filename]:
        if os.path.exists(f):
            os.remove(f)

    width, height = get_screen_size()
    ffmpeg_cmd = [
        get_ffmpeg_path(),
        '-y',
        '-f', 'gdigrab',
        '-framerate', '8',
        '-video_size', f'{width}x{height}',
        '-i', 'desktop',
        '-vf', 'format=yuv420p',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '23',
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

    threading.Thread(target=finalize).start()

def create_gui():
    global status_var
    app = tk.Tk()
    app.title("游戏录制器")
    app.geometry("300x160")
    app.resizable(False, False)

    tk.Button(app, text="开始录制", font=("Arial", 14), command=start_recording).pack(pady=10)
    tk.Button(app, text="停止录制", font=("Arial", 14), command=stop_recording).pack(pady=10)

    status_var = tk.StringVar()
    status_var.set("准备就绪")
    tk.Label(app, textvariable=status_var, font=("Arial", 12)).pack(pady=5)

    app.mainloop()

if __name__ == "__main__":
    create_gui()
