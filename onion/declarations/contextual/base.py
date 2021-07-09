from typing import (
    runtime_checkable,
    Protocol,
    Any,
)


@runtime_checkable
class Evaluable(Protocol):
    def evaluate(self) -> Any:
        raise NotImplementedError()
