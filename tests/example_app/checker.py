from onion.components import Input, Property
from onion.components.base import ValueChangedEvent


class ThresholdChecker:
    name: str
    temperature: Input[float] = 10.0
    threshold: Property[float]
    test: float = 55.0

    def __init__(self):
        @self.threshold.add_listener
        def value_change(event: ValueChangedEvent):
            print(event)

    def exceed_threshold(self, value: float) -> bool:
        return self.threshold.value < value