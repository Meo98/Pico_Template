import asyncio
from pico_config import PinConfig

class Thunder(PinConfig):
    def __init__(self, thunder_en_l, thunder_en_r, thunder_pwm_l, thunder_pwm_r, thunder_btn):
        self.thunder_en_l = thunder_en_l
        self.thunder_en_r = thunder_en_r
        self.thunder_pwm_l = thunder_pwm_l
        self.thunder_pwm_r = thunder_pwm_r
        self.btn = thunder_btn


        # Event für manuellen Trigger
        self.manual_trigger = asyncio.Event()
        
        # Den Button verknüpfen
        self.btn.on_click(self.trigger_once)
    
    async def trigger_once(self):
        print("Klick! Blitz ausgelöst.")
        self.manual_trigger.set()

    async def run(self):
        print("Thunder gestartet")
        while True:
            if await self.manual_trigger.wait():
                self.manual_trigger.clear()
                
                # Blitz links
                self.thunder_en_l.value(1)
                for _ in range(3):
                    self.thunder_pwm_l.duty_u16(32500)
                    await asyncio.sleep_ms(200)
                    self.thunder_pwm_l.duty_u16(0)
                    await asyncio.sleep_ms(200)
                
                self.thunder_en_l.value(0)
                
                await asyncio.sleep_ms(500)  # Pause zwischen den Seiten
                
                # Blitz rechts
                self.thunder_en_r.value(1)
                for _ in range(3):
                    self.thunder_pwm_r.duty_u16(32500)
                    await asyncio.sleep_ms(200)
                    self.thunder_pwm_r.duty_u16(0)
                    await asyncio.sleep_ms(200)