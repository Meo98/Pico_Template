import uasyncio as asyncio


class Blink():
    def __init__(self, led):
        self.led = led
        
    async def run(self):
        while True:
            self.led.duty_u16(32768)  # 50% Helligkeit
            await asyncio.sleep(0.5)
            self.led.duty_u16(0)      # Aus
            await asyncio.sleep(0.5)
