# utils_pca9685.py

import os
import board
import busio
from adafruit_bus_device.i2c_device import I2CDevice

def find_pca9685_bus(address=0x40):
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        while not i2c.try_lock():
            pass
        devices = i2c.scan()
        i2c.unlock()
        if address in devices:
            return i2c
    except Exception as e:
        print(f"❌ I2C 初始化失敗: {e}")
    return None

def angle_to_pwm(angle, min_us=500, max_us=2500, freq=50):
    """
    將角度轉為 PCA9685 duty_cycle (16bit)
    angle: 0~180
    min_us/max_us: 此伺服的最小最大脈寬（微秒）
    freq: PCA9685 PWM 頻率
    """
    pulse_us = min_us + (angle / 180) * (max_us - min_us)
    period_us = 1000000 // freq  # eg. 20_000us for 50Hz
    duty_cycle_fraction = pulse_us / period_us
    return int(duty_cycle_fraction * 65535)
