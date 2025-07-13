from collections import deque, defaultdict

class FingerSmoother:
    def __init__(self, window_size=5, method='majority', hysteresis=(155, 165)):
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
