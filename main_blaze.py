import numpy as np
import cv2
import os
from datetime import datetime
import glob
import subprocess
import getpass
import socket
import sys
import argparse
from collections import deque, defaultdict

sys.path.append(os.path.abspath('./blaze_common/'))
from blaze_hailo.hailo_inference import HailoInference
from blaze_hailo.blazedetector import BlazeDetector
from blaze_hailo.blazelandmark import BlazeLandmark
from visualization import draw_detections, draw_landmarks, draw_roi, HAND_CONNECTIONS

# 參數設定
scale = 1.0
text_fontType = cv2.FONT_HERSHEY_SIMPLEX
text_fontSize = 0.75 * scale
text_color = (0, 0, 255)
text_lineSize = max(1, int(2 * scale))
text_lineType = cv2.LINE_AA

# 簡化，只做 hand
blaze_detector_type = "blazepalm"
blaze_landmark_type = "blazehandlandmark"
blaze_title = "BlazeHandLandmark"
detector_model = 'blaze_hailo/models/palm_detection_full.hef'
landmark_model = 'blaze_hailo/models/hand_landmark_full.hef'

FINGER_TIPS = {'thumb': 4, 'index': 8, 'middle': 12, 'ring': 16, 'pinky': 20}
FINGER_BASES = {'thumb': 2, 'index': 5, 'middle': 9, 'ring': 13, 'pinky': 17}
FINGER_NAMES_ZH = {'thumb': '大拇指', 'index': '食指', 'middle': '中指', 'ring': '無名指', 'pinky': '小指'}

def get_media_dev_by_name(src):
    devices = glob.glob("/dev/media*")
    for dev in sorted(devices):
        proc = subprocess.run(['media-ctl','-d',dev,'-p'], capture_output=True, encoding='utf8')
        for line in proc.stdout.splitlines():
            if src in line:
                return dev

def get_video_dev_by_name(src):
    devices = glob.glob("/dev/video*")
    for dev in sorted(devices):
        proc = subprocess.run(['v4l2-ctl','-d',dev,'-D'], capture_output=True, encoding='utf8')
        for line in proc.stdout.splitlines():
            if src in line:
                return dev

# === 夾角計算 ===
def calc_angle(a, b, c):
    ab = a - b
    cb = c - b
    ab_norm = ab / np.linalg.norm(ab)
    cb_norm = cb / np.linalg.norm(cb)
    angle = np.arccos(np.clip(np.dot(ab_norm, cb_norm), -1.0, 1.0))
    return np.degrees(angle)

def finger_is_straight(landmarks, finger):
    if finger == 'thumb':
        a, b, c = np.array(landmarks[0]), np.array(landmarks[2]), np.array(landmarks[4])
    else:
        base_idx = FINGER_BASES[finger]
        mid_idx = base_idx + 1
        tip_idx = FINGER_TIPS[finger]
        a, b, c = np.array(landmarks[base_idx]), np.array(landmarks[mid_idx]), np.array(landmarks[tip_idx])
    angle = calc_angle(a, b, c)
    return angle, "伸直" if angle > 160 else "彎曲"

# ----------- 滑動視窗平滑 -------------
class FingerSmoother:
    def __init__(self, window_size=5, method='majority', hysteresis=(155, 165)):
        """
        method: 'majority', 'angle_mean', 'hysteresis'
        hysteresis: (lower, upper) for hysteresis threshold
        """
        self.window_size = window_size
        self.method = method
        self.states = defaultdict(lambda: deque(maxlen=window_size))
        self.angles = defaultdict(lambda: deque(maxlen=window_size))
        self.last_state = defaultdict(lambda: None)
        self.hysteresis = hysteresis

    def update(self, finger, state, angle=None):
        self.states[finger].append(state)
        if angle is not None:
            self.angles[finger].append(angle)

    def get_state(self, finger):
        if self.method == 'majority':
            vals = list(self.states[finger])
            count_straight = vals.count("伸直")
            count_bend = vals.count("彎曲")
            return "伸直" if count_straight >= count_bend else "彎曲"
        elif self.method == 'angle_mean':
            if not self.angles[finger]:
                return None
            mean_angle = sum(self.angles[finger]) / len(self.angles[finger])
            return "伸直" if mean_angle > 160 else "彎曲"
        elif self.method == 'hysteresis':
            if not self.angles[finger]:
                return None
            mean_angle = sum(self.angles[finger]) / len(self.angles[finger])
            low, high = self.hysteresis
            last = self.last_state[finger]
            if last is None:
                state = "伸直" if mean_angle > high else "彎曲"
            elif last == "彎曲" and mean_angle > high:
                state = "伸直"
            elif last == "伸直" and mean_angle < low:
                state = "彎曲"
            else:
                state = last
            self.last_state[finger] = state
            return state
        else:
            if self.states[finger]:
                return self.states[finger][-1]
            return None

# ----------- argparse 新增 smoothing mode -------------
ap = argparse.ArgumentParser()
ap.add_argument('-i', '--input', type=str, default="", help="Video input device. Default auto-detect.")
ap.add_argument('-d', '--debug', default=False, action='store_true', help="Enable Debug mode.")
ap.add_argument('-w', '--withoutview', default=False, action='store_true', help="Disable Output viewing.")
ap.add_argument('-f', '--fps', default=False, action='store_true', help="Enable FPS display.")
ap.add_argument('--smooth', type=str, default='hysteresis', choices=['majority', 'angle_mean', 'hysteresis', 'all'],
                help='Smoothing method for finger states')
ap.add_argument('--window', type=int, default=5, help='Sliding window size')
args = ap.parse_args()

user = getpass.getuser()
host = socket.gethostname()
print("[INFO] user@host : ", user+"@"+host)

print("[INFO] Searching for USB camera ...")
dev_video = get_video_dev_by_name("uvcvideo")
input_video = dev_video if args.input == "" else args.input
print("[INFO] Input Video : ", input_video)

output_dir = './captured-images'
if not os.path.exists(output_dir):
    os.mkdir(output_dir)

# Open video
cap = cv2.VideoCapture(input_video)
frame_width = 320
frame_height = 240
cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)
print("camera", input_video, " (", frame_width, ",", frame_height, ")")

hailo_infer = HailoInference()
blaze_detector = BlazeDetector(blaze_detector_type, hailo_infer)
blaze_detector.set_debug(debug=args.debug)
blaze_detector.display_scores(debug=False)
blaze_detector.load_model(detector_model)

blaze_landmark = BlazeLandmark(blaze_landmark_type, hailo_infer)
blaze_landmark.set_debug(debug=args.debug)
blaze_landmark.load_model(landmark_model)

print("================================================================")
print("Blaze Detect Live Demo")
print("================================================================")
print("\tPress ESC to quit ...")
print("----------------------------------------------------------------")
print("\tPress 'w' to take a photo ...")
print("================================================================")

bViewOutput = not args.withoutview
bShowFPS = args.fps

# --------- 初始化三種 smoothing ---------
smoother_majority = FingerSmoother(window_size=args.window, method='majority')
smoother_angle = FingerSmoother(window_size=args.window, method='angle_mean')
smoother_hysteresis = FingerSmoother(window_size=args.window, method='hysteresis', hysteresis=(155, 165))

def get_finger_states(landmarks, mode='hysteresis'):
    status = {}
    for f in FINGER_TIPS:
        zh_name = FINGER_NAMES_ZH[f]
        angle, raw_state = finger_is_straight(landmarks, f)
        # 更新三種平滑器
        smoother_majority.update(zh_name, raw_state)
        smoother_angle.update(zh_name, raw_state, angle)
        smoother_hysteresis.update(zh_name, raw_state, angle)
        # 根據 mode 回傳
        if mode == 'majority':
            smoothed = smoother_majority.get_state(zh_name)
        elif mode == 'angle_mean':
            smoothed = smoother_angle.get_state(zh_name)
        elif mode == 'hysteresis':
            smoothed = smoother_hysteresis.get_state(zh_name)
        elif mode == 'all':
            smoothed = {
                "majority": smoother_majority.get_state(zh_name),
                "angle_mean": smoother_angle.get_state(zh_name),
                "hysteresis": smoother_hysteresis.get_state(zh_name),
            }
        else:
            smoothed = raw_state
        status[zh_name] = smoothed
    return status

frame_count = 0
while True:
    flag, frame = cap.read()
    if not flag:
        print("[ERROR] cap.read() FAILED!")
        break
    frame_count += 1
    image = frame.copy()
    output = image.copy()
    # Run blaze pipeline
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    img1, scale1, pad1 = blaze_detector.resize_pad(image_rgb)
    normalized_detections = blaze_detector.predict_on_image(img1)
    if len(normalized_detections) > 0:
        detections = blaze_detector.denormalize_detections(normalized_detections, scale1, pad1)
        xc, yc, scale, theta = blaze_detector.detection2roi(detections)
        roi_img, roi_affine, roi_box = blaze_landmark.extract_roi(image_rgb, xc, yc, theta, scale)
        flags, normalized_landmarks = blaze_landmark.predict(roi_img)
        landmarks = blaze_landmark.denormalize_landmarks(normalized_landmarks, roi_affine)
        for landmark, flag in zip(landmarks, flags):
            finger_status = get_finger_states(landmark, mode=args.smooth)
            print('五指狀態（{}）：'.format(args.smooth), finger_status)
            draw_landmarks(output, landmark[:, :2], HAND_CONNECTIONS, size=2)
        draw_roi(output, roi_box)
        draw_detections(output, detections)
    if bShowFPS:
        fps = cap.get(cv2.CAP_PROP_FPS)
        cv2.putText(output, "FPS: {:.2f}".format(fps), (10, frame_height-10), text_fontType, text_fontSize, text_color, text_lineSize, text_lineType)
    if bViewOutput:
        cv2.imshow(blaze_title + " Demo", output)
    key = cv2.waitKey(1)
    if key == 27 or key == ord('q'):
        break
    if key == ord('w'):
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = os.path.join(output_dir, f"hand-{ts}.jpg")
        cv2.imwrite(out_path, output)
        print(f"[INFO] Saved: {out_path}")

cap.release()
cv2.destroyAllWindows()
