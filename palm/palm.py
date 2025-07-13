# palm/palm.py

from fingers.thumb import Thumb
from fingers.index import Index
from fingers.middle import Middle
from fingers.ring import Ring
from fingers.pinky import Pinky
import time
from module.utils_pca9685 import angle_to_pwm
import random
import math

class Palm:
    def __init__(self, pca):
        self.fingers = {
            "thumb": Thumb(pca),
            "index": Index(pca),
            "middle": Middle(pca),
            "ring": Ring(pca),
            "pinky": Pinky(pca)
        }

    def gesture(self, gesture_dict, smooth=False):
        for name, angle in gesture_dict.items():
            finger = self.fingers.get(name)
            if finger:
                if smooth:
                    finger.move_to_smooth(angle)
                else:
                    finger.move_to(angle)

    def gesture_smooth_sync(self, gesture_dict, smooth_factor=0.2, delay=0.02, epsilon=1):
        """ 同步平滑移動所有手指到目標 gesture
        - smooth_factor: 越大越快
        - delay: 每次 step 間延遲 (秒)
        - epsilon: 距離目標多少以內算完成
        """
        # 計算每個目標角度（已考慮 offset）
        targets = {}
        for name, angle in gesture_dict.items():
            finger = self.fingers.get(name)
            if finger:
                t = max(finger.min_angle, min(finger.max_angle, angle + finger.offset))
                targets[name] = t

        done = False
        while not done:
            done = True
            for name, target in targets.items():
                finger = self.fingers.get(name)
                if finger is None:
                    continue
                if abs(finger.current_angle - target) > epsilon:
                    # 指數平滑
                    finger.current_angle = finger.current_angle * (1 - smooth_factor) + target * smooth_factor
                    pwm = angle_to_pwm(finger.current_angle)
                    finger.pca.channels[finger.channel].duty_cycle = int(pwm)
                    print(f"[{name}] sync move to {finger.current_angle:.1f}° (通道 {finger.channel})，PWM: {int(pwm)}")
                    done = False
            time.sleep(delay)

        # 全部補一刀直接設為最終精確角度
        for name, target in targets.items():
            finger = self.fingers.get(name)
            if finger:
                finger.move_to(target)

    def _easing(t):  # 可選的easing function (ease-in-out cubic)
        return 3 * t ** 2 - 2 * t ** 3

    def gesture_smooth_sync_humanlike(
        self, gesture_dict, 
        base_smooth=0.1, base_delay=0.02, epsilon=1,
        randomize=True, stagger=True
    ):
        # 計算每個手指的 target, 記錄初始角度
        fingers_info = {}
        for name, angle in gesture_dict.items():
            finger = self.fingers.get(name)
            if finger:
                t = max(finger.min_angle, min(finger.max_angle, angle + finger.offset))
                # 隨機smooth/delay
                smooth = base_smooth + random.uniform(-0.03, 0.03) if randomize else base_smooth
                delay = base_delay + random.uniform(0, 0.01) if randomize else base_delay
                # 隨機起始延遲
                stagger_delay = random.uniform(0, 0.12) if stagger else 0
                fingers_info[name] = {
                    'finger': finger,
                    'target': t,
                    'start_angle': finger.current_angle,
                    'smooth': smooth,
                    'delay': delay,
                    'stagger_delay': stagger_delay,
                    'progress': 0.0,
                    'done': False,
                }

        max_steps = 40
        for step in range(max_steps):
            all_done = True
            for name, info in fingers_info.items():
                finger = info['finger']
                # Stagger: 等待該手指的stagger_delay時機
                if step * info['delay'] < info['stagger_delay']:
                    continue
                # Progress: 0~1
                progress = min(1, (step * info['delay'] - info['stagger_delay']) / (max_steps * info['delay']))
                progress_eased = _easing(progress)
                # 插值到目標
                cur_angle = info['start_angle'] * (1 - progress_eased) + info['target'] * progress_eased
                pwm = angle_to_pwm(cur_angle)
                finger.pca.channels[finger.channel].duty_cycle = int(pwm)
                finger.current_angle = cur_angle
                if abs(cur_angle - info['target']) > epsilon:
                    all_done = False
                print(f"[{name}] humanlike move to {cur_angle:.1f}° (通道 {finger.channel})，PWM: {int(pwm)}")
            if all_done:
                break
            time.sleep(base_delay)
        # 最後精確到位
        for name, info in fingers_info.items():
            info['finger'].move_to(info['target'])

    def relax(self):
        for finger in self.fingers.values():
            finger.relax()