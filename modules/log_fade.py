import math
import time

class Fade:
    def __init__(self, led, start_value, end_value, steps):
        self.led = led
        self.start_value = start_value
        self.end_value = end_value
        self.steps = steps
        self.leds = 0
        self.values = []
        self.generate_pwm_list()
        self.old_time = 0
        self.target_position = 0
        self.sleep = 0
  
    def generate_pwm_list(self):
            # Exponentieller Anstieg
        for i in range(self.steps):
            value = self.start_value * math.exp(i * math.log(self.end_value/self.start_value) / (self.steps-1))
            self.values.append(min(round(value), self.end_value))
        print(self.values)

    def fade(self, target_position, sleep):
        self.target_position = target_position
        self.sleep = sleep
    
    def update(self):
        if time.ticks_diff(time.ticks_ms(), self.old_time) > self.sleep: 
            self.old_time = time.ticks_ms()
            if self.leds < self.target_position:
                self.leds += 1
            elif self.leds > self.target_position:
                self.leds -= 1
        self.led.duty_u16(self.values[self.leds])
        
        
    
    def set_led(self, value):
        self.target_position = value

        self.leds = value

        self.led.duty_u16(self.values[self.leds])
