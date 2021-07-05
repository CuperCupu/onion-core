from dataclasses import dataclass
from typing import runtime_checkable, Protocol, TypeVar, Any, Generic

from onion.core.events import EventSource, Event


@runtime_checkable
class Component(Protocol):

    @property
    def name(self) -> str:
        raise NotImplementedError()


@runtime_checkable
class Setup(Protocol):

    async def setup(self) -> None:
        pass


@runtime_checkable
class Runnable(Protocol):

    async def run(self) -> None:
        """Waits until this component is done running."""

    async def stop(self) -> None:
        """Ask this component to stop the running process."""


T = TypeVar("T")
E = TypeVar("E")


@dataclass
class ValueChangedEvent(Event, Generic[T]):
    sender: Any
    value: T
    prev_value: T


@runtime_checkable
class Input(EventSource[ValueChangedEvent[T]], Protocol[T]):

    @property
    def owner(self) -> Any:
        raise NotImplementedError()

    async def receive_input(self, value: T) -> None:
        raise NotImplementedError()


@runtime_checkable
class Output(Protocol[T]):

    @property
    def owner(self) -> Any:
        raise NotImplementedError()

    async def add_destination(self, dest: Input[T]) -> None:
        raise NotImplementedError()

    async def remove_destination(self, dest: Input[T]) -> None:
        raise NotImplementedError()

    async def send(self, value: T) -> None:
        raise NotImplementedError()


@runtime_checkable
class Property(EventSource[ValueChangedEvent[T]], Protocol[T]):

    @property
    def owner(self) -> Any:
        raise NotImplementedError()

    value: T
