# fingers/base_finger.py

from module.utils_pca9685 import angle_to_pwm

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

    def relax(self):
        self.move_to(90)
