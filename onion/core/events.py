import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Awaitable
from typing import Any, TypeVar, Protocol, runtime_checkable, Union

EventType = TypeVar("EventType")
EventListener = Union[
    Callable[[Any, EventType], None], Callable[[Any, EventType], Awaitable[None]]
]


@runtime_checkable
class EventSource(Protocol[EventType]):
    @property
    def listeners(self) -> Iterable[EventListener]:
        raise NotImplementedError()

    def add_listener(self, listener: EventListener) -> None:
        raise NotImplementedError()

    def remove_listener(self, listener: EventListener) -> None:
        raise NotImplementedError()

    def listen(self, listener: EventListener) -> EventListener:
        self.add_listener(listener)
        return listener


ListenerCollection = Iterable[EventListener[EventType]]


class EventDispatcher(ABC):
    @abstractmethod
    def dispatch(
        self, sender: Any, event: EventType, listeners: ListenerCollection
    ) -> None:
        raise NotImplementedError()

    def dispatch_for(self, sender: Any, event: EventType, source: EventSource) -> None:
        self.dispatch(sender, event, source.listeners)

    @abstractmethod
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

    def dispatch(
        self, sender: Any, event: EventType, listeners: ListenerCollection
    ) -> None:
        for listener in listeners:
            if asyncio.iscoroutinefunction(listener):
                task = self._loop.create_task(listener(sender, event))
                task.add_done_callback(self._done_callback)
                self._tasks.append(task)
            else:
                self._loop.call_soon(listener, sender, event)

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

    def add_listener(self, name: str, listener: EventListener) -> None:
        self._sources[name].add_listener(listener)

    def remove_listener(self, name: str, listener: EventListener) -> None:
        self._sources[name].remove_listener(listener)

    def __contains__(self, name: str) -> bool:
        return name in self._sources


class EventSourceImpl(EventSource[EventType]):

    _listeners: list[EventListener]

    def __init__(self):
        self._listeners = []

    @property
    def listeners(self) -> Iterable[EventListener]:
        return self._listeners

    def add_listener(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: EventListener) -> None:
        self._listeners.remove(listener)
