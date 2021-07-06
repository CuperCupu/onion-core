from onion.components import Input
from onion.core.events import EventSource


class Actuator:
    event: EventSource[bool] = Input()
    worked: int

    def __init__(self):
        self.worked = 0

        assert self.event

        @self.event.listen
        def work(_, changed: bool):
            if changed:
                self.worked += 1
