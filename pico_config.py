from machine import Pin, ADC, PWM
from modules import Button

print("template_1.0")
print("pico_w is booting")


class PinConfig:

    
    status_led = PWM(Pin(25)) # GPIO25: led

    thunder_en_l = Pin(2, Pin.OUT)
    thunder_en_r = Pin(3, Pin.OUT)
    thunder_pwm_l = PWM(Pin(4))
    thunder_pwm_r = PWM(Pin(5))

    # --- Buttons ---
    # Wir erstellen hier direkt das Button-Objekt!
    # Damit ist die Pin-Nummer (14) und die Config (PULL_UP) hier sicher verstaut.
    pin_obj = Pin(14, Pin.IN, Pin.PULL_UP)
    thunder_btn = Button(pin_obj, active_low=True)