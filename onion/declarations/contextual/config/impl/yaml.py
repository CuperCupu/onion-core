import asyncio
from typing import Union, Iterable, Any, Type, Callable, Awaitable

import yaml
from pydantic import BaseModel

from onion.declarations.util import validation_error
from ..factory import ConfigResolver


class YamlResolverConfig(BaseModel):
    filename: str


ReadFileFunc = Union[Callable[[str], bytes], Callable[[str], Awaitable[bytes]]]


def default_read_file(filename: str) -> bytes:
    with open(filename, "rb") as f:
        return f.read()


class YamlConfigResolver(ConfigResolver[YamlResolverConfig]):
    def __init__(self, read_file: ReadFileFunc = default_read_file):
        self.read_file = read_file

    @property
    def name(self) -> str:
        return "yaml"

    @property
    def args_model(self) -> Type[YamlResolverConfig]:
        return YamlResolverConfig

    async def get_values(
        self, args: YamlResolverConfig
    ) -> Union[Iterable[tuple[str, Any]], dict[str, Any]]:
        try:
            if asyncio.iscoroutinefunction(self.read_file):
                data = await self.read_file(args.filename)
            else:
                data = self.read_file(args.filename)
            parsed = yaml.safe_load(data)
        except Exception as e:
            raise validation_error(self.args_model, e, ("filename",))

        if not isinstance(parsed, dict):
            raise validation_error(
                self.args_model,
                TypeError(f"Expected 'dict' type, got '{type(data)}'"),
                ("filename",),
            )

        return parsed.items()
