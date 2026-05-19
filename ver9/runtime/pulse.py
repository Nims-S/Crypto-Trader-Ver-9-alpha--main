from statistics import mean


class Pulse:
    def __init__(self):
        self.values = []

    def add(self, value: float) -> float:
        self.values.append(value)
        return mean(self.values[-10:])
