import asyncio
from pico_config import PinConfig


class Blink(PinConfig):
    def __init__(self):
        pass
    async def run(self):
        while True:
            self.status_led.on()  # 50% Helligkeit
            await asyncio.sleep(0.5)
            self.status_led.off()     # Aus
            await asyncio.sleep(0.5)
