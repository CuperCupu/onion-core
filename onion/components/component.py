import asyncio
from dataclasses import dataclass
from typing import Generic, Any, Type, TypeVar

from onion.core.events import Event, EventDispatcher, EventSourceImpl
from .base import Input, Output, Property, ValueChangedEvent

T = TypeVar("T")


class InputImpl(EventSourceImpl[ValueChangedEvent[T]], Input[T]):

    _value: T

    def __init__(self, owner: Any, initial_value: T, dispatcher: EventDispatcher):
        self._owner = owner
        super().__init__(dispatcher)
        self._value = initial_value

    @property
    def owner(self) -> Any:
        return self._owner

    async def receive_input(self, value: T) -> None:
        """Invoked by external source to indicate that this object has received an input."""
        prev_value = self._value
        self._value = value
        ev = ValueChangedEvent(self, value, prev_value)
        self.dispatch(ev)

    @property
    def value(self) -> T:
        return self._value


class OutputImpl(Output[T]):

    _destinations: list[Input[T]]

    def __init__(self, owner: Any):
        self._owner = owner
        self._destinations = []

    @property
    def owner(self) -> Any:
        return self._owner

    async def add_destination(self, dest: Input[T]) -> None:
        self._destinations.append(dest)

    async def remove_destination(self, dest: Input[T]) -> None:
        self._destinations.remove(dest)

    async def send(self, value: T) -> None:
        if self._destinations:
            await asyncio.gather(
                *(dest.receive_input(value) for dest in self._destinations)
            )


class PropertyImpl(EventSourceImpl[ValueChangedEvent[T]], Property[T]):

    _value: T
    _type: Type[T]

    def __init__(self, owner: Any, initial_value: T, dispatcher: EventDispatcher):
        super().__init__(dispatcher)
        self._type = type(initial_value)
        self._value = initial_value
        self._loop = asyncio.get_running_loop()
        self._owner = owner

    @property
    def owner(self) -> Any:
        return self._owner

    def _set_value(self, value: T) -> None:
        prev_value = self._value
        self._value = value
        ev = ValueChangedEvent(self, value, prev_value)
        self.dispatch(ev)

    def _get_value(self) -> T:
        return self._value

    value = property(_get_value, _set_value)

    def __repr__(self):
        return f"Property(owner={self._owner}, type={self._type.__name__}, value={self._value})"


@dataclass
class Inject:
    type: type = ...
