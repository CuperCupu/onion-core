import asyncio
from dataclasses import dataclass
from typing import Any, TypeVar, Protocol, Collection, runtime_checkable, Callable, Awaitable


@dataclass
class Event:
    sender: Any


EventType = TypeVar("EventType", bound=Event, covariant=True)
EventListener = Callable[[EventType], Awaitable[None]]


@runtime_checkable
class EventSource(Protocol[EventType]):

    def add_listener(self, listener: EventListener[EventType]) -> None:
        raise NotImplementedError()

    def remove_listener(self, listener: EventListener[EventType]) -> None:
        raise NotImplementedError()

    def dispatch(self, event: Event):
        raise NotImplementedError()


@runtime_checkable
class EventDispatcher(Protocol):

    def dispatch(self, event: EventType, listeners: Collection[EventListener[EventType]]) -> None:
        raise NotImplementedError()

    async def run(self) -> None:
        raise NotImplementedError()


@runtime_checkable
class EventHub(Protocol):

    def register(self, name: str, source: EventSource) -> None:
        raise NotImplementedError()

    def deregister(self, name: str) -> None:
        raise NotImplementedError()

    def add_listener(self, name: str, listener: EventListener[EventType]) -> None:
        raise NotImplementedError()

    def remove_listener(self, name: str, listener: EventListener[EventType]) -> None:
        raise NotImplementedError()

    def __contains__(self, name: str) -> bool:
        raise NotImplementedError()


class DefaultEventDispatcher(EventDispatcher):

    def __init__(self):
        self._loop = asyncio.get_running_loop()
        self._tasks = []

    def _done_callback(self, task: asyncio.Task) -> None:
        self._tasks.remove(task)

    def dispatch(self, event: EventType, listeners: Collection[EventListener]) -> None:
        for listener in listeners:
            if asyncio.iscoroutinefunction(listener):
                task = self._loop.create_task(
                    listener(event)
                )
                task.add_done_callback(self._done_callback)
                self._tasks.append(task)
            else:
                self._loop.call_soon(listener, event)

    async def run(self) -> None:
        await asyncio.gather(*self._tasks)


class DefaultEventHub(EventHub):

    _sources: dict[str, EventSource]

    def __init__(self):
        self._sources = {}

    def register(self, name: str, source: EventSource) -> None:
        self._sources[name] = source

    def deregister(self, name: str) -> None:
        del self._sources[name]

    def add_listener(self, name: str, listener: EventListener[EventType]) -> None:
        self._sources[name].add_listener(listener)

    def remove_listener(self, name: str, listener: EventListener[EventType]) -> None:
        self._sources[name].remove_listener(listener)

    def __contains__(self, name: str) -> bool:
        return name in self._sources


class EventSourceImpl(EventSource[EventType]):

    listeners: list[EventListener[EventType]]

    def __init__(self, dispatcher: EventDispatcher):
        self.dispatcher = dispatcher
        self.listeners = []

    def add_listener(self, listener: EventListener[EventType]) -> None:
        self.listeners.append(listener)

    def remove_listener(self, listener: EventListener[EventType]) -> None:
        self.listeners.remove(listener)

    def dispatch(self, event: Event) -> None:
        self.dispatcher.dispatch(event, self.listeners)
