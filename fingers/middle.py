# fingers/thumb.py

from fingers.base_finger import BaseFinger
from module.hardware_config import FINGER_CONFIGS

class Middle(BaseFinger):
    def __init__(self, pca):
        super().__init__(name="middle", pca=pca, config=FINGER_CONFIGS["middle"])
