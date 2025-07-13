import os
import cv2
import argparse
import getpass
import socket
from datetime import datetime

# ==== 模組化 import（你要搬出來） ====
from utils.video_devices import get_video_dev_by_name
from motions.constants import FINGER_TIPS, FINGER_NAMES_ZH
from motions.hand_analysis import finger_is_straight, finger_status_to_angle
from motions.finger_smoother import FingerSmoother
from palm.init_palm import setup_palm

from blaze_hailo.hailo_inference import HailoInference
from blaze_hailo.blazedetector import BlazeDetector
from blaze_hailo.blazelandmark import BlazeLandmark

import sys
sys.path.append(os.path.abspath('./blaze_common/'))
from visualization import draw_detections, draw_landmarks, draw_roi, HAND_CONNECTIONS

# ==== 參數設定 ====
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('-i', '--input', type=str, default="", help="Video input device. Default auto-detect.")
    ap.add_argument('-d', '--debug', default=False, action='store_true', help="Enable Debug mode.")
    ap.add_argument('-w', '--withoutview', default=False, action='store_true', help="Disable Output viewing.")
    ap.add_argument('-f', '--fps', default=False, action='store_true', help="Enable FPS display.")
    ap.add_argument('--smooth', type=str, default='hysteresis', choices=['majority', 'angle_mean', 'hysteresis', 'all'])
    ap.add_argument('--window', type=int, default=5, help='Sliding window size')
    return ap.parse_args()

def init_detectors(args):
    # 模型路徑
    detector_model = 'blaze_hailo/models/palm_detection_full.hef'
    landmark_model = 'blaze_hailo/models/hand_landmark_full.hef'
    # 初始化
    hailo_infer = HailoInference()
    blaze_detector = BlazeDetector("blazepalm", hailo_infer)
    blaze_detector.set_debug(debug=args.debug)
    blaze_detector.display_scores(debug=False)
    blaze_detector.load_model(detector_model)

    blaze_landmark = BlazeLandmark("blazehandlandmark", hailo_infer)
    blaze_landmark.set_debug(debug=args.debug)
    blaze_landmark.load_model(landmark_model)

    return blaze_detector, blaze_landmark

def get_finger_states(landmarks, smoother_dict, mode='hysteresis'):
    status = {}
    for f in FINGER_TIPS:
        zh_name = FINGER_NAMES_ZH[f]
        angle, raw_state = finger_is_straight(landmarks, f)
        for sm in smoother_dict.values():
            sm.update(zh_name, raw_state, angle)
        if mode in smoother_dict:
            smoothed = smoother_dict[mode].get_state(zh_name)
        elif mode == 'all':
            smoothed = {k: sm.get_state(zh_name) for k, sm in smoother_dict.items()}
        else:
            smoothed = raw_state
        status[zh_name] = smoothed
    return status

def main():
    args = parse_args()
    user = getpass.getuser()
    host = socket.gethostname()
    print(f"[INFO] user@host : {user}@{host}")

    # ==== 影像輸入初始化 ====
    input_video = get_video_dev_by_name("uvcvideo") if args.input == "" else args.input
    print(f"[INFO] Input Video : {input_video}")
    cap = cv2.VideoCapture(input_video)
    frame_width = 320
    frame_height = 240
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    # ==== 模型與手掌初始化 ====
    blaze_detector, blaze_landmark = init_detectors(args)
    palm = setup_palm()

    # ==== 平滑器 ====
    smoother_dict = {
        'majority': FingerSmoother(window_size=args.window, method='majority'),
        'angle_mean': FingerSmoother(window_size=args.window, method='angle_mean'),
        'hysteresis': FingerSmoother(window_size=args.window, method='hysteresis', hysteresis=(155, 165)),
    }
    prev_angles = None
    output_dir = './captured-images'
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    print("================================================================")
    print("Blaze Detect Live Demo")
    print("Press ESC to quit, 'w' to take a photo ...")
    print("================================================================")

    # ==== 影像主迴圈 ====
    while True:
        flag, frame = cap.read()
        if not flag:
            print("[ERROR] cap.read() FAILED!")
            break

        output = frame.copy()
        # ----------- 推理 ----------
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img1, scale1, pad1 = blaze_detector.resize_pad(image_rgb)
        normalized_detections = blaze_detector.predict_on_image(img1)

        if len(normalized_detections) > 0:
            detections = blaze_detector.denormalize_detections(normalized_detections, scale1, pad1)
            xc, yc, scale, theta = blaze_detector.detection2roi(detections)
            roi_img, roi_affine, roi_box = blaze_landmark.extract_roi(image_rgb, xc, yc, theta, scale)
            flags, normalized_landmarks = blaze_landmark.predict(roi_img)
            landmarks = blaze_landmark.denormalize_landmarks(normalized_landmarks, roi_affine)
            for landmark, flag in zip(landmarks, flags):
                finger_status = get_finger_states(landmark, smoother_dict, mode=args.smooth)
                angles = finger_status_to_angle(finger_status)

                # ---- 只在角度變動時才下指令 ----
                if angles != prev_angles:
                    palm.gesture_smooth_sync_humanlike(angles)
                    prev_angles = angles.copy()

                print('五指狀態（{}）：'.format(args.smooth), finger_status)
                draw_landmarks(output, landmark[:, :2], HAND_CONNECTIONS, size=2)
            draw_roi(output, roi_box)
            draw_detections(output, detections)

        # ==== 顯示、拍照與鍵盤輸入處理 ====
        if not args.withoutview:
            cv2.imshow("BlazeHandLandmark Demo", output)
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

if __name__ == "__main__":
    main()
