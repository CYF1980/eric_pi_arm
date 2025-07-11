# palm/palm.py

from fingers.thumb import Thumb
from fingers.index import Index
from fingers.middle import Middle
from fingers.ring import Ring
from fingers.pinky import Pinky

class Palm:
    def __init__(self, pca):
        self.fingers = {
            "thumb": Thumb(pca),
            "index": Index(pca),
            "middle": Middle(pca),
            "ring": Ring(pca),
            "pinky": Pinky(pca)
        }

    def gesture(self, gesture_dict):
        for name, angle in gesture_dict.items():
            finger = self.fingers.get(name)
            if finger:
                finger.move_to(angle)

    def relax(self):
        for finger in self.fingers.values():
            finger.relax()
