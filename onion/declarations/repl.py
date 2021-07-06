from dataclasses import dataclass
from typing import runtime_checkable, Protocol, Any, TypeVar, Generic


@runtime_checkable
class VariableReference(Protocol):

    def _get(self) -> Any:
        raise NotImplementedError()

    def _set(self, value: Any) -> None:
        raise NotImplementedError()

    value = property(_get, _set)


@dataclass
class DictReference:
    container: dict[str, Any]
    key: str

    def _get(self) -> Any:
        return self.container[self.key]

    def _set(self, value: Any) -> None:
        self.container[self.key] = value

    value = property(_get, _set)


@dataclass
class ListReference:
    container: list[Any]
    key: int

    def _get(self) -> Any:
        return self.container[self.key]

    def _set(self, value: Any) -> None:
        self.container[self.key] = value

    value = property(_get, _set)


T = TypeVar("T")


@dataclass
class Replaceable(Generic[T]):
    owner: str
    location: VariableReference
    placeholder: T

    def replace(self, value: Any) -> None:
        self.location.value = value

    class Config:
        arbitrary_types_allowed = True
