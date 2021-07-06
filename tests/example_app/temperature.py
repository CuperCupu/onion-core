from .thermometer import Thermometer


class TemperatureSimulator:
    name: str

    def __init__(self, initial: float, *, thermometer: Thermometer):
        thermometer.temperature.value = initial
