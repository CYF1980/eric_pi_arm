# main.py

import time
from module.utils_pca9685 import find_pca9685_bus
from adafruit_pca9685 import PCA9685
from palm.palm import Palm
from motions.gestures import GESTURES

if __name__ == "__main__":
    i2c = find_pca9685_bus()
    if i2c is None:
        print("找不到 PCA9685，請檢查硬體！")
        exit(1)

    pca = PCA9685(i2c)
    pca.frequency = 50

    palm = Palm(pca)

    try:
        palm.gesture(GESTURES["relax"])
        time.sleep(1)
        palm.gesture(GESTURES["fist"])
        time.sleep(2)
        palm.gesture(GESTURES["open"])
        time.sleep(2)
        palm.gesture(GESTURES["rock"])
        time.sleep(2)
        palm.relax()
    finally:
        pca.deinit()
        print("🧹 測試結束，已釋放資源")
