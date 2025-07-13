import numpy as np
from .constants import FINGER_TIPS, FINGER_BASES, FINGER_NAMES_ZH, FINGER_NAME_MAP, FINGER_ACTION_ANGLE

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

def finger_status_to_angle(finger_status):
    angles = {}
    for zh_name, status in finger_status.items():
        eng_name = FINGER_NAME_MAP[zh_name]
        angle = FINGER_ACTION_ANGLE[eng_name].get(status, 90)
        angles[eng_name] = angle
    return angles
