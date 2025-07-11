# fingers/thumb.py

from fingers.base_finger import BaseFinger
from module.hardware_config import FINGER_CONFIGS

class Pinky(BaseFinger):
    def __init__(self, pca):
        super().__init__(name="pinky", pca=pca, config=FINGER_CONFIGS["pinky"])
