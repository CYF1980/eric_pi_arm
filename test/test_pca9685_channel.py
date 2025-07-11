import time
import threading
from digitalio import DigitalInOut
from adafruit_pca9685 import PCA9685
from module.utils_pca9685 import angle_to_pwm, find_pca9685_bus

print("🔍 嘗試偵測 PCA9685 (I2C 位址 0x40)...")
i2c = find_pca9685_bus()

if i2c is None:
    print("❌ 找不到 PCA9685 裝置，請檢查接線與硬體")
    exit(1)

print("✅ 找到 PCA9685，初始化中...")

pca = PCA9685(i2c)
pca.frequency = 50  # MG996R 使用 50Hz

def set_servo(channel, angle, offset=0):
    angle = max(0, min(180, angle + offset))  # 校正用
    pwm = angle_to_pwm(angle, freq=pca.frequency)
    pca.channels[channel].duty_cycle = pwm
    print(f"➡️ MG996R (通道 {channel}) 設定為 {angle}°，PWM: {pwm}")

def test_servo_sequence(channel, delay=0):
    time.sleep(delay)
    print(f"⚙️ 測試 MG996R (channel {channel}) 開始，延遲 {delay} 秒")
    try:
        set_servo(channel, 90)
        time.sleep(1)
        set_servo(channel, 60)
        time.sleep(1)
        set_servo(channel, 110)
        time.sleep(1)
        set_servo(channel, 30)
        time.sleep(1)
        set_servo(channel, 110)
        time.sleep(1)
        set_servo(channel, 30)
        time.sleep(1)
        set_servo(channel, 110)
        time.sleep(1)
        set_servo(channel, 90)
        time.sleep(1)
        print(f"✅ Channel {channel} 測試完成")
    except Exception as e:
        print(f"❌ Channel {channel} 發生錯誤：{e}")
    finally:
        pass  # 可以視需要加回正角度

threads = []
for i, ch in enumerate([3, 4, 5, 6, 7]):
    t = threading.Thread(target=test_servo_sequence, args=(ch, i))
    t.start()
    threads.append(t)

try:
    for t in threads:
        t.join()
except KeyboardInterrupt:
    print("\n🛑 中斷操作，全部回正")
    for ch in [4, 5, 6, 7]:
        set_servo(ch, 90)

finally:
    pca.deinit()
    print("🧹 清理完畢，測試結束")
