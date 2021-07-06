import asyncio
from dataclasses import dataclass
from typing import Any, Type, TypeVar, Iterable

from onion.core.events import (
    EventDispatcher,
    EventSourceImpl,
    EventSource,
    EventType,
    EventListener,
)
from .base import Property, ValueChangedEvent

T = TypeVar("T")


@dataclass
class Input:
    pass


class PropertyImpl(EventSourceImpl[ValueChangedEvent[T]], Property[T]):

    _value: T
    _type: Type[T]

    def __init__(self, owner: Any, initial_value: T, dispatcher: EventDispatcher):
        super().__init__()
        self._type = type(initial_value)
        self._value = initial_value
        self._loop = asyncio.get_running_loop()
        self._owner = owner
        self.dispatcher = dispatcher

    @property
    def owner(self) -> Any:
        return self._owner

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: T) -> None:
        prev_value = self._value
        self._value = value
        ev = ValueChangedEvent(value, prev_value)
        self.dispatcher.dispatch_for(self, ev, self)

    def __repr__(self):
        return f"Property(owner={self._owner}, type={self._type.__name__}, value={self._value})"


class PropertyView(Property[T], EventSource[ValueChangedEvent[T]]):
    def __init__(self, owner: Any, prop: Property[T]):
        self._prop = prop
        self._owner = owner

    @property
    def listeners(self) -> Iterable[EventListener[EventType]]:
        return self._prop.listeners

    @property
    def owner(self) -> Any:
        return self._owner

    @property
    def prop(self) -> Property[T]:
        return self._prop

    def add_listener(self, listener: EventListener[ValueChangedEvent[T]]) -> None:
        self._prop.add_listener(listener)

    def remove_listener(self, listener: EventListener[ValueChangedEvent[T]]) -> None:
        self._prop.remove_listener(listener)

    @property
    def value(self) -> T:
        return self._prop.value

    @value.setter
    def value(self, value: T) -> None:
        raise TypeError("View is not allowed to mutate property value")

    def __repr__(self):
        return f"PropertyView(owner={self._owner}, prop={self._prop})"


@dataclass
class Inject:
    type: type = ...
