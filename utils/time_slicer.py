from time import ticks_ms

class TimeSlicer:
    def __init__(self, function, wait):
        self.function = function
        self.wait = wait
        self.stamp = 0

    def update(self):
        ticks = ticks_ms()
        if ticks - self.stamp >= self.wait:
            self.stamp = ticks
            self.function()