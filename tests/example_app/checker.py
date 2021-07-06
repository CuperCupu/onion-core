from onion.components import Property, Input, Inject, ValueChangedEvent
from onion.core.events import EventDispatcher, EventSource


class ThresholdChecker:
    name: str
    temperature: Property[float] = Input()
    threshold: Property[float]
    changed: EventSource[bool]

    def __init__(self, *, dispatcher: EventDispatcher = Inject()):
        super().__init__()

        assert self.changed

        last_value = self.exceed_threshold(self.temperature.value)

        @self.temperature.add_listener
        def value_change(_, event: ValueChangedEvent):
            nonlocal last_value

            new_value = self.exceed_threshold(event.value)
            if new_value != last_value:
                dispatcher.dispatch_for(self, new_value, self.changed)
            last_value = new_value

    def exceed_threshold(self, value: float) -> bool:
        return self.threshold.value < value
