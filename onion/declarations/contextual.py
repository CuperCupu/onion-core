from contextlib import contextmanager
from contextvars import ContextVar
from typing import runtime_checkable, Protocol, Any, Collection, Generic, TypeVar

from pydantic import BaseModel, Field


@runtime_checkable
class Evaluable(Protocol):
    def evaluate(self) -> Any:
        raise NotImplementedError()


class ConfigProvider(Protocol):
    def __getitem__(self, item: str) -> Any:
        raise NotImplementedError()

    def __contains__(self, item: str) -> bool:
        raise NotImplementedError()


class ConfigResolver:

    _context = ContextVar("config_context")

    def __init__(self, backends: Collection[ConfigProvider]):
        self._backends = backends

    @contextmanager
    def context(self):
        token = self._context.set(self)
        yield self
        self._context.reset(token)

    def __getitem__(self, name: str) -> Any:
        for backend in self._backends:
            try:
                return backend[name]
            except KeyError:
                continue
        raise KeyError(name)

    def __contains__(self, item: str) -> bool:
        if self._backends:
            return any(map(lambda x: item in x, self._backends))
        return False

    @classmethod
    def current(cls) -> ConfigProvider:
        try:
            return cls._context.get()
        except LookupError:
            return {}


T = TypeVar("T")


class _Empty:
    pass


class ConfigProperty(BaseModel, Generic[T]):
    config: str = Field(alias="$config")
    default: Any = Field(alias="$default", default=_Empty)

    def evaluate(self) -> T:
        try:
            return ConfigResolver.current()[self.config]
        except KeyError:
            if self.default is _Empty:
                raise
            else:
                if isinstance(self.default, list):
                    return list(self.default)
                elif isinstance(self.default, dict):
                    return dict(self.default)
                return self.default

    @staticmethod
    def of(config: str, default: Any = ...) -> "ConfigProperty":
        return ConfigProperty(**{"$config": config, "$default": default})


class EvaluatedProperty(BaseModel, Generic[T]):
    script: str = Field(alias="eval")

    def evaluate(self) -> T:
        return None
