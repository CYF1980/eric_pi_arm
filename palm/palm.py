# palm/palm.py

from fingers.thumb import Thumb
from fingers.index import Index
from fingers.middle import Middle
from fingers.ring import Ring
from fingers.pinky import Pinky
import time
from module.utils_pca9685 import angle_to_pwm

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

    def gesture_smooth_sync(self, gesture_dict, smooth_factor=0.1, delay=0.02, epsilon=1):
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

    def relax(self):
        for finger in self.fingers.values():
            finger.relax()