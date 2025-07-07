import json
import math

def summarize_user_actions(file_path):
    """
    分析用户行为日志 (jsonl)，总结成结构化的事件列表。

    Args:
        file_path (str): 输入的 jsonl 文件路径。

    Returns:
        list: 包含总结后行为信息的字典列表。
    """
    # ----- 1. 初始化数据存储结构 -----
    
    # 键盘事件相关
    key_press_events = {}  # 存储 {key: press_time}
    key_actions = {
        "press": {"keys": set(), "durations": []},
        "press_down": {"keys": set()},
        "press_up": {"keys": set()},
    }
    modifier_keys = {"ctrl", "shift", "alt", "cmd", "win"} # 定义修饰键

    # 鼠标事件相关
    mouse_press_events = {} # 存储 {button: press_time}
    mouse_actions = {
        "click": {"buttons": set(), "durations": []},
        "move": {"distances_x": [], "distances_y": []},
        "scroll": {"scrolls": []},
    }
    last_mouse_position = None
    
    # 原始事件计数器，用于计算权重
    action_counts = {
        "keyboard_press": 0,
        "keyboard_press_down": 0,
        "keyboard_press_up": 0,
        "mouse_click": 0,
        "mouse_move": 0,
        "mouse_scroll": 0
    }

    # ----- 2. 逐行读取和处理日志文件 -----
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    event_type = event.get("type")
                    event_time = event.get("time")

                    # --- 处理键盘事件 ---
                    if event_type == "key_press":
                        key = event.get("key")
                        if key:
                            key_press_events[key] = event_time
                            if key in modifier_keys:
                                key_actions["press_down"]["keys"].add(key)
                                action_counts["keyboard_press_down"] += 1
                            else:
                                # 这是为 'press' 动作做准备，但只有在 release 时才记录
                                pass

                    elif event_type == "key_release":
                        key = event.get("key")
                        if key and key in key_press_events:
                            duration = event_time - key_press_events.pop(key)
                            if key in modifier_keys:
                                key_actions["press_up"]["keys"].add(key)
                                action_counts["keyboard_press_up"] += 1
                            else:
                                key_actions["press"]["keys"].add(key)
                                key_actions["press"]["durations"].append(duration)
                                action_counts["keyboard_press"] += 1
                    
                    # --- 处理鼠标事件 ---
                    elif event_type == "mouse_press":
                        button = event.get("button", "left") # 默认为左键
                        mouse_press_events[button] = event_time

                    elif event_type == "mouse_release":
                        button = event.get("button", "left")
                        if button in mouse_press_events:
                            duration = event_time - mouse_press_events.pop(button)
                            mouse_actions["click"]["buttons"].add(button)
                            mouse_actions["click"]["durations"].append(duration)
                            action_counts["mouse_click"] += 1

                    elif event_type == "mouse_move":
                        position = event.get("position")
                        if position and last_mouse_position:
                            dx = position[0] - last_mouse_position[0]
                            dy = position[1] - last_mouse_position[1]
                            mouse_actions["move"]["distances_x"].append(dx)
                            mouse_actions["move"]["distances_y"].append(dy)
                        last_mouse_position = position
                        action_counts["mouse_move"] += 1
                        
                    elif event_type == "mouse_scroll":
                        scroll_amount = event.get("scroll")
                        if scroll_amount:
                           mouse_actions["scroll"]["scrolls"].append(scroll_amount)
                           action_counts["mouse_scroll"] += 1

                except json.JSONDecodeError:
                    print(f"警告：无法解析行: {line.strip()}")

    except FileNotFoundError:
        print(f"错误：文件未找到: {file_path}")
        return []

    # ----- 3. 整理和计算最终结果 -----
    summary = []
    total_actions = sum(action_counts.values())

    def get_weight(action_name):
        return round(action_counts.get(action_name, 0) / total_actions if total_actions > 0 else 0, 2)

    # 键盘 - press
    if key_actions["press"]["keys"]:
        summary.append({
            "type": "keyboard",
            "action": "press",
            "key": list(key_actions["press"]["keys"]),
            "duration": {
                "min": round(min(key_actions["press"]["durations"]), 4) if key_actions["press"]["durations"] else 0.0,
                "max": round(max(key_actions["press"]["durations"]), 4) if key_actions["press"]["durations"] else 0.0,
            },
            "weight": get_weight("keyboard_press")
        })

    # 键盘 - press_down
    if key_actions["press_down"]["keys"]:
        summary.append({
            "type": "keyboard",
            "action": "press_down",
            "key": list(key_actions["press_down"]["keys"]),
            "weight": get_weight("keyboard_press_down")
        })

    # 键盘 - press_up
    if key_actions["press_up"]["keys"]:
        summary.append({
            "type": "keyboard",
            "action": "press_up",
            "key": list(key_actions["press_up"]["keys"]),
            "weight": get_weight("keyboard_press_up")
        })

    # 鼠标 - click
    if mouse_actions["click"]["buttons"]:
        summary.append({
            "type": "mouse",
            "action": "click",
            "button": list(mouse_actions["click"]["buttons"]),
            "duration": {
                "min": round(min(mouse_actions["click"]["durations"]), 4) if mouse_actions["click"]["durations"] else 0.0,
                "max": round(max(mouse_actions["click"]["durations"]), 4) if mouse_actions["click"]["durations"] else 0.0,
            },
            "weight": get_weight("mouse_click")
        })

    # 鼠标 - move
    if mouse_actions["move"]["distances_x"]:
        # 为了简化输出，这里可以考虑将x和y的移动范围合并
        # 或者分别提供。这里我们提供一个综合的范围。
        all_distances = mouse_actions["move"]["distances_x"] + mouse_actions["move"]["distances_y"]
        summary.append({
            "type": "mouse",
            "action": "move",
            "distance": {
                "min": min(all_distances),
                "max": max(all_distances),
            },
            "weight": get_weight("mouse_move")
        })

    # 鼠标 - scroll
    if mouse_actions["scroll"]["scrolls"]:
        summary.append({
            "type": "mouse",
            "action": "scroll",
            "scroll": {
                "min": min(mouse_actions["scroll"]["scrolls"]),
                "max": max(mouse_actions["scroll"]["scrolls"]),
            },
            "weight": get_weight("mouse_scroll")
        })

    return summary

# Example usage based on the uploaded file
file_path = "C:\\Users\\59681\\OneDrive\\桌面\\game trace\\GameTrace-main\\GameTrace-main\\data\\record_20250707_171253.jsonl"

# Get the summary of actions
summary = summarize_user_actions(file_path)

game_name = "Black Myth: Wukong"
output_path = "data\game_event_space.json"
# Output the summary as JSON
with open(output_path, "w") as f_out:
    f_out.write(json.dumps({game_name: summary}, indent=4))
