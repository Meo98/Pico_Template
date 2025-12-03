import asyncio
from thunder import Thunder
from blink import Blink
from pico_config import PinConfig

async def main():
    pc = PinConfig()

    thunder = Thunder()
    blink = Blink()
    
    # Tasks starten (laufen parallel)
    asyncio.create_task(blink.run())
    asyncio.create_task(thunder.run())

    while True:
        await asyncio.sleep(1) # Herzschlag, 1 Sekunde warten
    
try:
    asyncio.run(main())
except KeyboardInterrupt:
    PinConfig.status_led.off()