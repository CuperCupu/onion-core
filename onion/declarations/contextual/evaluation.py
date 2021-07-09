import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Optional, Match, Generic, TypeVar

from pydantic import Field
from pydantic.generics import GenericModel

from .config import ConfigContext, ConfigProvider
from .config.base import ConfigNotFound

T = TypeVar("T")

config_syntax = re.compile(
    r"\$config\.(\w+(?:\.\w+)*)(?=\s|$|\+|-|\*|\*\*|\/|\/\/|%|@|<<|>>|&|\||\^|~|<|>|<=|>=|==|!=)"
)


class ConfigView(ConfigProvider):
    def __getitem__(self, item: str) -> Any:
        try:
            return self._config[item]
        except KeyError as e:
            raise ConfigNotFound(item) from e

    def __contains__(self, item: str) -> bool:
        return item in self._config

    def __init__(self, _config: ConfigProvider):
        self._config = _config


class EvaluationContext:

    _context = ContextVar("global_context")

    def __init__(self, static: dict[str, Any]):
        self.static = static

    @contextmanager
    def context(self):
        token = self._context.set(self)
        yield self
        self._context.reset(token)

    @classmethod
    def current(cls) -> Optional["EvaluationContext"]:
        try:
            return cls._context.get()
        except LookupError:
            return None

    def evaluate(self, expr: str) -> Any:
        config_context = ConfigContext.current()

        scopes = {**self.static, "config": ConfigView(config_context)}

        def get_config(match: Match):
            return f"config['{match.group(1)}']"

        parsed = config_syntax.sub(get_config, expr)

        rv = eval(parsed, scopes)

        return rv


class EvaluatedProperty(GenericModel, Generic[T]):
    expr: str = Field(alias="$eval")

    def evaluate(self) -> T:
        context = EvaluationContext.current()
        if context:
            result = context.evaluate(self.expr)
        else:
            result = eval(self.expr)
        return result

    @staticmethod
    def of(expr: str) -> "EvaluatedProperty":
        return EvaluatedProperty.parse_obj({"$eval": expr})
