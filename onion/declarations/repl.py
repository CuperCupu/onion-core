from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar, Generic, Sequence

C = TypeVar("C")
K = TypeVar("K")
T = TypeVar("T")


class VariableReference(ABC, Generic[T, C, K]):
    container: C
    key: K

    def __init__(self, container: C, key: K):
        self.container = container
        self.key = key

    def _get(self) -> T:
        return self.container[self.key]

    def _set(self, value: T) -> None:
        self.container[self.key] = value

    value = property(_get, _set)


@dataclass
class Replaceable(Generic[T]):
    owner: Any
    location: Sequence[str]
    ref: VariableReference
    placeholder: T

    def replace(self, value: Any) -> None:
        self.ref.value = value

    class Config:
        arbitrary_types_allowed = True
