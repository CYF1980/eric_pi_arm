# fingers/base_finger.py

from module.utils_pca9685 import angle_to_pwm
import time

class BaseFinger:
    def __init__(self, name, pca, config):
        self.name = name
        self.pca = pca
        self.channel = config.get("channel")
        self.min_angle = config.get("min_angle", 0)
        self.max_angle = config.get("max_angle", 180)
        self.offset = config.get("offset", 0)
        self.current_angle = 90

    def move_to(self, angle):
        real_angle = max(self.min_angle, min(self.max_angle, angle + self.offset))
        pwm = angle_to_pwm(real_angle)
        self.pca.channels[self.channel].duty_cycle = pwm
        self.current_angle = real_angle
        print(f"[{self.name}] 角度設為 {real_angle}° (通道 {self.channel})，PWM: {pwm}")

    def move_to_smooth(self, target_angle, smooth_factor=0.1, delay=0.02, epsilon=1):
        """ 平滑移動手指到目標角度
        - smooth_factor: 介於 0~1, 越大越快 (建議 0.05~0.2)
        - delay: 每次 step 間延遲 (秒)
        - epsilon: 距離目標多少以內算完成
        """
        target_angle = max(self.min_angle, min(self.max_angle, target_angle + self.offset))
        while abs(self.current_angle - target_angle) > epsilon:
            # 指數平滑
            self.current_angle = self.current_angle * (1 - smooth_factor) + target_angle * smooth_factor
            pwm = angle_to_pwm(self.current_angle)
            self.pca.channels[self.channel].duty_cycle = int(pwm)
            print(f"[{self.name}] 平滑移動到 {self.current_angle:.1f}° (通道 {self.channel})，PWM: {int(pwm)}")
            time.sleep(delay)
        # 最後補一刀直接到精確值
        self.move_to(target_angle)

    def relax(self):
        self.move_to(90)
