from dataclasses import dataclass
from typing import runtime_checkable, Protocol, TypeVar, Any, Generic

from onion.core.events import EventSource


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
class ValueChangedEvent(Generic[T]):
    value: T
    prev_value: T


@runtime_checkable
class Property(EventSource[ValueChangedEvent[T]], Protocol[T]):

    @property
    def owner(self) -> Any:
        raise NotImplementedError()

    value: T
