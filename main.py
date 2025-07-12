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
        #palm.gesture(GESTURES["relax"])
        palm.gesture_smooth_sync(GESTURES["relax"])
        time.sleep(1)
        #palm.gesture(GESTURES["fist"])
        palm.gesture_smooth_sync(GESTURES["fist"])
        time.sleep(1)
        #palm.gesture(GESTURES["open"])
        palm.gesture_smooth_sync(GESTURES["open"])
        time.sleep(1)
        #palm.gesture(GESTURES["rock"])
        palm.gesture_smooth_sync(GESTURES["rock_on"])
        time.sleep(1)
        #palm.relax()
        palm.gesture_smooth_sync(GESTURES["fucku"])

        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["one"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["four"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["two"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["five"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["three"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["ok"])
        time.sleep(1)
        palm.gesture_smooth_sync(GESTURES["relax"])
    finally:
        pca.deinit()
        print("🧹 測試結束，已釋放資源")
