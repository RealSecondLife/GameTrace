import json
from collections import defaultdict

# --- 常量定义 ---
HOLD_THRESHOLD = 0.15 

def summarize_user_actions(file_path):
    raw_events = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # 使用 enumerate 可以方便地在出错时报告行号
            for line_number, line in enumerate(f, 1):
                # 跳过空行
                if not line.strip():
                    continue
                try:
                    # 尝试解析当前行
                    event = json.loads(line)
                    raw_events.append(event)
                except json.JSONDecodeError as e:
                    # 如果仅当前行解析失败，打印警告并跳过，继续处理下一行
                    print(f"警告：第 {line_number} 行JSON解析失败，已跳过。错误：{e}")
                    print(f"   --> 内容: {line.strip()}")
                    
    except FileNotFoundError:
        print(f"错误：文件未找到: {file_path}")
        return {}


    # 1. 事件分组
    event_groups = []
    consumed_indices = set()
    i = 0
    while i < len(raw_events):
        if i in consumed_indices: i += 1; continue
        event = raw_events[i]
        
        if event['type'] in ['mouse_move', 'mouse_scroll']:
            event_groups.append([event]); consumed_indices.add(i); i += 1; continue

        if event['type'].endswith('_press'):
            group, end_index = extract_action_group(raw_events, i)
            if group:
                event_groups.append(group)
                for j in range(i, end_index + 1): consumed_indices.add(j)
                i = end_index + 1
            else: i += 1
        else: i += 1
            
    # 2. 处理分组
    processed_events = []
    for group in event_groups:
        events_from_group = process_group_to_schema_v4(group)
        processed_events.extend(events_from_group)
                
    # 3. 聚合
    final_events = aggregate_simple_events_v3(processed_events)
    return {"events": final_events}

def extract_action_group(events, start_index):
    """与之前版本相同：提取一个完整的动作组。"""
    group, active_holds = [], {}
    initial_event = events[start_index]
    actor = initial_event.get('key') or initial_event.get('button', 'left')
    active_holds[actor] = initial_event
    group.append(initial_event)
    
    for i in range(start_index + 1, len(events)):
        event = events[i]
        group.append(event)
        evt_type = event['type']
        
        if evt_type.endswith('_press'):
            actor = event.get('key') or event.get('button', 'left')
            if actor not in active_holds: active_holds[actor] = event
        elif evt_type.endswith('_release'):
            actor = event.get('key') or event.get('button', 'left')
            if actor in active_holds: del active_holds[actor]
        
        if not active_holds: return group, i
            
    return group, len(events) - 1

def process_group_to_schema_v4(group):
    """
    v4: 智能区分 combo 内的 "wrapper" (down/release) 和 "inner" (press) 行为。
    """
    if not group: return []
    
    events_to_return = []
    actors_pressed = {e.get('key') or e.get('button', 'left') for e in group if e['type'].endswith('_press')}
    is_combo = len(actors_pressed) > 1

    if is_combo:
        # --- 1. 创建更智能的 Combo 对象 ---
        steps_with_time = []
        
        # a. 聚合鼠标移动
        combo_moves = [e for e in group if e['type'] == 'mouse_move']
        if combo_moves:
            first_move, last_move = combo_moves[0], combo_moves[-1]
            total_dx = last_move['position'][0] - first_move['position'][0]
            total_dy = last_move['position'][1] - first_move['position'][1]
            duration = max(0.0, last_move['time'] - first_move['time'])
            move_step = { "type": "mouse", "action": "move", "x_range": sorted([0, total_dx]), "y_range": sorted([0, total_dy]), "duration_range": [duration, duration] }
            steps_with_time.append({'time': first_move['time'], 'data': move_step})
            
        # b. 区分 wrapper 和 inner 键盘/鼠标行为
        actor_event_map = defaultdict(list)
        for e in group:
            if e['type'].endswith(('_press', '_release')):
                actor = e.get('key') or e.get('button', 'left')
                actor_event_map[actor].append(e)

        combo_start_time, combo_end_time = group[0]['time'], group[-1]['time']
        
        for actor, event_list in actor_event_map.items():
            presses = sorted([e for e in event_list if e['type'].endswith('_press')], key=lambda x: x['time'])
            if not presses: continue
            first_press = presses[0]
            release = next((e for e in sorted(event_list, key=lambda x:x['time']) if e['type'].endswith('_release') and e['time'] > first_press['time']), None)
            
            # 判断是 "inner" 还是 "wrapper"
            is_wrapper = True
            if release:
                duration = release['time'] - first_press['time']
                # 如果动作时间短，并且不是在 combo 的边缘发生，则认为是 inner
                if duration < HOLD_THRESHOLD and (first_press['time'] - combo_start_time > 0.01) and (combo_end_time - release['time'] > 0.01):
                    is_wrapper = False
            
            # c. 创建步骤
            actor_type = "keyboard" if 'key' in first_press else "mouse"
            actor_key_name = "keys" if actor_type == "keyboard" else "buttons"

            if is_wrapper:
                steps_with_time.append({'time': first_press['time'], 'data': {"type": actor_type, "action": "down", actor_key_name: [actor]}})
                if release:
                    steps_with_time.append({'time': release['time'], 'data': {"type": actor_type, "action": "release", actor_key_name: [actor]}})
            else: # Inner action
                if actor_type == "keyboard":
                    steps_with_time.append({'time': first_press['time'], 'data': {"type": "keyboard", "action": "press", "keys": [actor]}})
                else:
                    steps_with_time.append({'time': first_press['time'], 'data': {"type": "mouse", "action": "click", "buttons": [actor], "clicks": 1, "interval_range": [duration, duration]}})

        steps_with_time.sort(key=lambda x: x['time'])
        final_steps = [s['data'] for s in steps_with_time]
        desc = "Combo: " + " + ".join(sorted(list(actors_pressed)))
        events_to_return.append({"type": "combo", "description": desc, "steps": final_steps})

    # --- 2. 提取所有独立的按键/点击行为 (无论是否是 combo) ---
    # (此部分逻辑与上一版相同，以实现事件双重记录)
    actor_event_map_for_simple = defaultdict(list)
    for e in group:
        if e['type'].endswith(('_press', '_release')):
            actor = e.get('key') or e.get('button', 'left')
            actor_event_map_for_simple[actor].append(e)

    for actor, event_list in actor_event_map_for_simple.items():
        presses = sorted([e for e in event_list if e['type'].endswith('_press')], key=lambda x: x['time'])
        if not presses: continue
        releases = sorted([e for e in event_list if e['type'].endswith('_release')], key=lambda x: x['time'])
        
        first_press, last_release = presses[0], releases[-1] if releases else None
        
        is_hold = (len(presses) > 1) or (not last_release)
        duration = (last_release['time'] if last_release else group[-1]['time']) - first_press['time']
        if duration >= HOLD_THRESHOLD: is_hold = True

        if 'key' in first_press:
            action = "hold" if is_hold else "press"
            simple_event = {"type": "keyboard", "action": action, "keys": [actor]}
            if action == "hold": simple_event["hold_duration"] = duration
        else:
            simple_event = {"type": "mouse", "action": "click", "buttons": [actor], "click_duration": duration}
        
        events_to_return.append(simple_event)

    # 3. 处理独立的 move/scroll
    if not actor_event_map_for_simple and group:
        event = group[0]
        if event['type'] == 'mouse_move': events_to_return.append({"type": "mouse", "action": "move", "raw_event": event})
        elif event['type'] == 'mouse_scroll': events_to_return.append({"type": "mouse", "action": "scroll", "dx": 0, "dy": event.get('scroll', 0)})

    return events_to_return


def aggregate_simple_events_v3(events):
    """与上一版相同：聚合所有简单事件，并分离出 combo。"""
    aggregated = defaultdict(lambda: defaultdict(list))
    combos = [e for e in events if e['type'] == 'combo']
    simple_events = [e for e in events if e['type'] != 'combo']
    
    last_pos = None
    for e in simple_events:
        action = e['action']
        if e['type'] == 'keyboard':
            aggregated[f'keyboard_{action}']['keys'].extend(e['keys'])
            if 'hold_duration' in e: aggregated[f'keyboard_{action}']['durations'].append(e['hold_duration'])
        elif e['type'] == 'mouse':
            if action == 'click':
                aggregated['mouse_click']['buttons'].extend(e['buttons'])
                aggregated['mouse_click']['durations'].append(e['click_duration'])
            elif action == 'scroll':
                aggregated['mouse_scroll']['dx'].append(e['dx'])
                aggregated['mouse_scroll']['dy'].append(e['dy'])
            elif action == 'move' and 'raw_event' in e:
                pos = e['raw_event']['position']
                if last_pos:
                    aggregated['mouse_move']['x'].append(pos[0] - last_pos[0])
                    aggregated['mouse_move']['y'].append(pos[1] - last_pos[1])
                last_pos = pos

    output = []
    # Keyboard
    if aggregated['keyboard_press']['keys']: output.append({"type":"keyboard", "keys":sorted(list(set(aggregated['keyboard_press']['keys']))), "action":"press"})
    if aggregated['keyboard_hold']['keys']:
        d = aggregated['keyboard_hold']['durations']
        output.append({"type":"keyboard", "keys":sorted(list(set(aggregated['keyboard_hold']['keys']))), "action":"hold", "hold_duration_range":[min(d), max(d)]})
    # Mouse
    if aggregated['mouse_click']['buttons']:
        d = aggregated['mouse_click']['durations']
        output.append({"type":"mouse", "buttons":sorted(list(set(aggregated['mouse_click']['buttons']))), "action":"click", "clicks":1, "interval_range":[min(d), max(d)]})
    
    output.extend(combos)
    return output

# Example usage based on the uploaded file
file_path = "C:\\Users\\59681\\OneDrive\\桌面\\game trace\\GameTrace-main\\GameTrace-main\\data\\record_20250714_173014.jsonl"

# Get the summary of actions
summary = summarize_user_actions(file_path)

game_name = "Black Myth: Wukong"
output_path = "data\game_event_space.json"
# Output the summary as JSON
with open(output_path, "w") as f_out:
    f_out.write(json.dumps({game_name: summary}, indent=4))
