import json
import random
import time
from typing import List, Dict, Any, Union
import pyautogui

# ---------- 完整 Schema 定义说明 ----------
# 顶层字段：
# - events: List[Event]
#
# Event 类型：
# 1. Keyboard 单键事件
#    - type: "keyboard"
#    - keys: List[str]，候选单键
#    - action: "press" / "hold" / "release"
#    - hold_duration_range: [min, max]（action="hold" 时有效，单位秒）
#    - 说明：从 keys 随机选一个键执行。
#
# 2. Mouse 单按钮事件
#    - type: "mouse"
#    - buttons: List[str]，候选按钮（"left","right","middle"）
#    - action: "click" / "move" / "scroll"
#      - click:
#          - clicks: int
#          - interval_range: [min, max]
#      - move:
#          - x_range: [min, max]
#          - y_range: [min, max]
#          - duration_range: [min, max]
#      - scroll:
#          - dx_range: [min, max]
#          - dy_range: [min, max]
#    - 说明：从 buttons 随机选一个按钮执行；move/scroll 不使用 buttons。
#
# 3. Combo 组合事件（可键盘多键、鼠标多按钮、或键鼠混合）
#    - type: "combo"
#    - description: str，可选
#    - steps: List[Event]，按序执行，每项可为 keyboard 或 mouse 子事件
#    - 说明：每个 step 按其 own schema 随机采样。
#
# ---------- 示例 JSON ----------
# {
#   "events": [
#     {"type":"keyboard","keys":["a","b","c"],"action":"press"},
#     {"type":"keyboard","keys":["x","y"],"action":"hold","hold_duration_range":[0.2,0.5]},
#     {"type":"mouse","buttons":["left","right"],"action":"click","clicks":1,"interval_range":[0,0.1]},
#     {"type":"mouse","action":"move","x_range":[100,400],"y_range":[100,400],"duration_range":[0.05,0.2]},
#     {
#       "type":"combo",
#       "description":"复制并粘贴",
#       "steps":[
#         {"type":"keyboard","keys":["ctrl"],"action":"hold","hold_duration_range":[0.1,0.2]},
#         {"type":"keyboard","keys":["c"],"action":"press"},
#         {"type":"keyboard","keys":["v"],"action":"press"},
#         {"type":"keyboard","keys":["ctrl"],"action":"release"}
#       ]
#     },
#     {
#       "type":"combo",
#       "description":"按住 Ctrl 然后左键点击",
#       "steps":[
#         {"type":"keyboard","keys":["ctrl"],"action":"down"},
#         {"type":"mouse","buttons":["left"],"action":"click","clicks":1,"interval_range":[0,0.1]},
#         {"type":"keyboard","keys":["ctrl"],"action":"release"}
#       ]
#     }
#   ]
# }


def load_events(schema_json: Union[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    if isinstance(schema_json, str):
        data = json.loads(schema_json)
    else:
        data = schema_json
    return data.get("events", [])


def choose_key(keys: List[str]) -> str:
    return random.choice(keys)


def choose_button(buttons: List[str]) -> str:
    return random.choice(buttons)


def execute_keyboard(event: Dict[str, Any]):
    key = choose_key(event["keys"])
    action = event.get("action", "press")
    if action == "press":
        pyautogui.press(key)
    elif action == "hold":
        duration = random.uniform(*event.get("hold_duration_range", [0.1, 0.1]))
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
    elif action == "release":
        pyautogui.keyUp(key)
    else:
        raise ValueError(f"Unknown keyboard action: {action}")


def execute_mouse(event: Dict[str, Any]):
    action = event.get("action")
    if action == "click":
        button = choose_button(event.get("buttons", ["left"]))
        clicks = event.get("clicks", 1)
        interval = random.uniform(*event.get("interval_range", [0, 0]))
        pyautogui.click(button=button, clicks=clicks, interval=interval)
    elif action == "move":
        x = random.randint(*event["x_range"])
        y = random.randint(*event["y_range"])
        duration = random.uniform(*event.get("duration_range", [0, 0]))
        pyautogui.moveTo(x, y, duration=duration)
    elif action == "scroll":
        if event.get("dx_range"):
            pyautogui.hscroll(random.randint(*event.get("dx_range")))
        if event.get("dy_range"):
            pyautogui.vscroll(random.randint(*event.get("dy_range")))
    else:
        raise ValueError(f"Unknown mouse action: {action}")


def sample_and_execute(event: Dict[str, Any]) -> None:
    etype = event.get("type")
    if etype == "keyboard":
        execute_keyboard(event)
    elif etype == "mouse":
        execute_mouse(event)
    elif etype == "combo":
        for step in event.get("steps", []):
            sample_and_execute(step)
    else:
        raise ValueError(f"Unsupported event type: {etype}")


def main(schema: Union[str, Dict[str, Any]], iterations: int = None):
    events = load_events(schema)
    if not events:
        print("No events defined.")
        return
    count = 0
    try:
        while iterations is None or count < iterations:
            evt = random.choice(events)
            sample_and_execute(evt)
            count += 1
            time.sleep(random.uniform(0.2, 1.0))
    except KeyboardInterrupt:
        print("Execution stopped by user.")


if __name__ == '__main__':
    dct = {
      "events": [
        {"type":"keyboard","keys":["a","b","c"],"action":"press"},
        {"type":"keyboard","keys":["x","y"],"action":"hold","hold_duration_range":[0.2,0.5]},
        {"type":"mouse","buttons":["left","right"],"action":"click","clicks":1,"interval_range":[0,0.1]},
        {"type":"mouse","action":"move","x_range":[100,400],"y_range":[100,400],"duration_range":[0.05,0.2]},
        {
          "type":"combo",
          "description":"复制并粘贴",
          "steps":[
            {"type":"keyboard","keys":["ctrl"],"action":"hold","hold_duration_range":[0.1,0.2]},
            {"type":"keyboard","keys":["c"],"action":"press"},
            {"type":"keyboard","keys":["v"],"action":"press"},
            {"type":"keyboard","keys":["ctrl"],"action":"release"}
          ]
        },
        {
          "type":"combo",
          "description":"按住 Ctrl 然后左键点击",
          "steps":[
            {"type":"keyboard","keys":["ctrl"],"action":"press"},
            {"type":"mouse","buttons":["left"],"action":"click","clicks":1,"interval_range":[0,0.1]},
            {"type":"keyboard","keys":["ctrl"],"action":"release"}
          ]
        }
      ]
    }
    main(dct)

