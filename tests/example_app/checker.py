from onion.components import Property, Input
from onion.components.base import ValueChangedEvent


class ThresholdChecker:
    name: str
    temperature: Property[float] = Input()
    threshold: Property[float]
    test: float = 55.0

    def __init__(self):
        print(self.temperature.value)

        @self.threshold.add_listener
        def value_change(event: ValueChangedEvent):
            print(event)

    def exceed_threshold(self, value: float) -> bool:
        return self.threshold.value < value
