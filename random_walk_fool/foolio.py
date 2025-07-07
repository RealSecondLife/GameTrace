import random
import time
import json
from pynput import keyboard, mouse
from pynput.mouse import Button
from pynput.keyboard import Key

# 更新后的输入事件schema定义
"""
事件列表是一个JSON数组，每个事件包含以下字段：
[
  {
    "type": "keyboard" | "mouse",  # 事件类型
    "action": "press" | "press_down" | "press_up" | "click" | "move" | "scroll",  # 具体动作
    
    # 按键可以是单个键名或键名列表(随机选择一个)
    "key": "a" | ["ctrl", "alt"] | ... (键盘事件需要),
    
    # 鼠标按钮可以是单个按钮名或按钮名列表(随机选择一个)
    "button": "left" | ["left", "right"] (鼠标点击需要),
    
    "duration": {"min": 0.1, "max": 0.5} (仅press/click需要),  # 按下持续时间(秒)
    "distance": {"min": -100, "max": 100} (仅鼠标移动需要),  # 移动距离(像素)
    "scroll": {"min": -5, "max": 5} (仅滚轮需要),  # 滚动量
    "weight": 1.0  # 事件权重(概率)
  },
  ...
]
"""

class EventExecutor:
    def __init__(self, events):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.events = events
        self.total_weight = sum(event.get('weight', 1.0) for event in events)
    
    def _get_random_value(self, param_spec):
        """从参数范围中随机生成值"""
        if isinstance(param_spec, dict):
            min_val = param_spec.get('min', 0)
            max_val = param_spec.get('max', 0)
            if isinstance(min_val, int) and isinstance(max_val, int):
                return random.randint(min_val, max_val)
            return random.uniform(min_val, max_val)
        return param_spec
    
    def _parse_key(self, key_spec):
        """将按键规范转换为Key对象或字符，支持单个键或键列表"""
        if isinstance(key_spec, list):
            # 从列表中随机选择一个键
            return self._parse_key(random.choice(key_spec))
        
        try:
            # 尝试转换为特殊键
            return getattr(Key, key_spec)
        except AttributeError:
            # 普通字符键
            return key_spec
    
    def _parse_button(self, button_spec):
        """将按钮规范转换为鼠标按钮对象，支持单个按钮或按钮列表"""
        if isinstance(button_spec, list):
            # 从列表中随机选择一个按钮
            return self._parse_button(random.choice(button_spec))
        
        return getattr(Button, button_spec)
    
    def select_random_event(self):
        """根据权重随机选择一个事件"""
        rand_val = random.uniform(0, self.total_weight)
        cumulative = 0
        for event in self.events:
            cumulative += event.get('weight', 1.0)
            if rand_val <= cumulative:
                return event
    
    def execute_event(self, event):
        """执行单个事件"""
        event_type = event['type']
        action = event['action']
        
        try:
            if event_type == 'keyboard':
                key = self._parse_key(event['key'])
                
                if action == 'press':
                    duration = self._get_random_value(event.get('duration', {'min': 0.1, 'max': 0.3}))
                    with self.keyboard_controller.pressed(key):
                        time.sleep(duration)
                elif action == 'press_down':
                    self.keyboard_controller.press(key)
                elif action == 'press_up':
                    self.keyboard_controller.release(key)
            
            elif event_type == 'mouse':
                if action == 'click':
                    button = self._parse_button(event['button'])
                    duration = self._get_random_value(event.get('duration', {'min': 0.05, 'max': 0.2}))
                    self.mouse_controller.press(button)
                    time.sleep(duration)
                    self.mouse_controller.release(button)
                
                elif action == 'move':
                    dx = self._get_random_value(event.get('distance', {'min': -50, 'max': 50}))
                    dy = self._get_random_value(event.get('distance', {'min': -50, 'max': 50}))
                    self.mouse_controller.move(dx, dy)
                
                elif action == 'scroll':
                    dx = self._get_random_value(event.get('scroll', {'min': -3, 'max': 3}))
                    dy = self._get_random_value(event.get('scroll', {'min': -3, 'max': 3}))
                    self.mouse_controller.scroll(dx, dy)
        
        except Exception as e:
            print(f"执行事件失败: {e}")

    def run_random_event(self):
        """随机选择并执行一个事件"""
        event = self.select_random_event()
        if event:
            # 生成友好的事件描述
            desc = f"{event['type']}.{event['action']}"
            
            if event['type'] == 'keyboard' and 'key' in event:
                key = event['key']
                if isinstance(key, list):
                    desc += f" [keys: {', '.join(key)}]"
                else:
                    desc += f" [key: {key}]"
            
            if event['type'] == 'mouse' and event['action'] == 'click' and 'button' in event:
                button = event['button']
                if isinstance(button, list):
                    desc += f" [buttons: {', '.join(button)}]"
                else:
                    desc += f" [button: {button}]"
            
            print(f"执行事件: {desc}")
            self.execute_event(event)
        else:
            print("没有可用事件")

# 示例用法
if __name__ == "__main__":
    # 示例事件配置（包含按键/按钮列表）
    events_config = """
    [
        {
            "type": "keyboard",
            "action": "press",
            "key": ["a", "b", "c", "d"],
            "duration": {"min": 0.1, "max": 0.3},
            "weight": 2.0
        },
        {
            "type": "keyboard",
            "action": "press_down",
            "key": ["ctrl", "shift", "alt"],
            "weight": 1.0
        },
        {
            "type": "keyboard",
            "action": "press_up",
            "key": ["ctrl", "shift", "alt"],
            "weight": 1.0
        },
        {
            "type": "mouse",
            "action": "click",
            "button": ["left", "right"],
            "duration": {"min": 0.05, "max": 0.2},
            "weight": 1.5
        },
        {
            "type": "mouse",
            "action": "move",
            "distance": {"min": -100, "max": 100},
            "weight": 3.0
        },
        {
            "type": "mouse",
            "action": "scroll",
            "scroll": {"min": -5, "max": 5},
            "weight": 1.0
        }
    ]
    """
    
    # 加载事件配置
    events = json.loads(events_config)
    executor = EventExecutor(events)
    
    # 执行10个随机事件
    for i in range(10):
        executor.run_random_event()
        time.sleep(0.5)  # 事件间暂停