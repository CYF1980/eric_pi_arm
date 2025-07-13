from palm.palm import Palm
from module.utils_pca9685 import find_pca9685_bus
from adafruit_pca9685 import PCA9685

def setup_palm():
    i2c = find_pca9685_bus()
    if i2c is None:
        print("找不到 PCA9685，請檢查硬體！")
        exit(1)
    pca = PCA9685(i2c)
    pca.frequency = 50
    palm = Palm(pca)
    return palm
