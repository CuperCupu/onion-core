from dataclasses import dataclass
from typing import Any

from onion.core.events import EventSourceImpl, EventSource, DefaultEventDispatcher


@dataclass
class ExampleEvent:
    value: int


async def test_default_dispatcher():
    dispatcher = DefaultEventDispatcher()

    value = 0

    async def listener(sender: Any, event: ExampleEvent) -> None:
        nonlocal value
        assert sender == dispatcher

        value += event.value

    dispatcher.dispatch(dispatcher, ExampleEvent(5), [listener])

    await dispatcher.run()


async def test_source():
    dispatcher = DefaultEventDispatcher()

    source: EventSource[ExampleEvent] = EventSourceImpl()

    value = 0

    @source.listen
    async def listener(sender: Any, event: ExampleEvent) -> None:
        nonlocal value
        assert sender == source

        value += event.value

    dispatcher.dispatch_for(source, ExampleEvent(5), source)

    await dispatcher.run()

    assert value == 5

    source.remove_listener(listener)

    dispatcher.dispatch_for(source, ExampleEvent(5), source)

    await dispatcher.run()

    assert value == 5
