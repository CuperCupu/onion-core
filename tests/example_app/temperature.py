import asyncio
import random

from onion.components import Runnable, Property, Input
from .thermometer import Thermometer


class TemperatureSimulator(Runnable):
    name: str
    thermometer: Thermometer
    interval: float
    fluctuation: Property[float] = Input()

    def __init__(self, interval: float, *, thermometer: Thermometer):
        self.thermometer = thermometer
        self.initial = self.thermometer.temperature.value
        self.interval = interval
        self.running = True

    async def run(self) -> None:
        while self.running:
            await asyncio.sleep(self.interval)
            self.thermometer.temperature.value = self.interval + (
                (random.random() - 0.5) * self.fluctuation.value
            )

    async def stop(self) -> None:
        self.running = False
