from dataclasses import dataclass

import pytest

from onion.core.events import EventSourceImpl, EventSource, Event, DefaultEventDispatcher


@dataclass
class ExampleEvent(Event):
    value: int


@pytest.mark.asyncio_cooperative
async def test_default_dispatcher():
    dispatcher = DefaultEventDispatcher()

    value = 0

    async def listener(event: ExampleEvent) -> None:
        nonlocal value
        assert event.sender == dispatcher

        value += event.value

    dispatcher.dispatch(ExampleEvent(dispatcher, 5), [listener])

    await dispatcher.run()


@pytest.mark.asyncio_cooperative
async def test_source():
    dispatcher = DefaultEventDispatcher()

    source: EventSource[ExampleEvent] = EventSourceImpl(dispatcher)

    value = 0

    @source.listen
    async def listener(event: ExampleEvent) -> None:
        nonlocal value
        assert event.sender == source

        value += event.value

    source.dispatch(ExampleEvent(source, 5))

    await dispatcher.run()

    assert value == 5

    source.remove_listener(listener)

    source.dispatch(ExampleEvent(source, 5))

    await dispatcher.run()

    assert value == 5
