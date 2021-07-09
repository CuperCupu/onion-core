from functools import reduce
from typing import Protocol, Iterable, Any, Type, runtime_checkable, TypeVar, Union

from pydantic import BaseModel, Field

from onion.declarations.contextual.config import ConfigProvider
from onion.declarations.util import validation_error

T = TypeVar("T", bound=BaseModel)


class ConfigResolverException(Exception):
    pass


class InvalidConfigResolver(KeyError, ConfigResolverException):
    pass


@runtime_checkable
class ConfigResolver(Protocol[T]):
    @property
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def args_model(self) -> Type[T]:
        raise NotImplementedError()

    async def get_values(
        self, args: T
    ) -> Union[Iterable[tuple[str, Any]], dict[str, Any]]:
        raise NotImplementedError()


class BaseConfigResolverSchema(BaseModel):
    prefix: str = ""


class ConfigProviderFactory:

    _backends: dict[str, ConfigResolver[Any]]

    def __init__(self, backends: Iterable[ConfigResolver] = None):
        self._backends = {}
        self._to_build = []
        self._backend_config_models = None

        if backends:
            for backend in backends:
                self.register_backend(backend)

    @property
    def config_models(self):
        return self._backend_config_models

    def schema(self):
        schemas = []

        for name, backend in self._backends.items():

            schemas.append(
                type(
                    "ConfigResolverSchema_" + name,
                    (BaseConfigResolverSchema, backend.args_model),
                    {
                        "__annotations__": {"backend": str},
                        "backend": Field(name, const=True),
                    },
                )
            )

        schema = reduce(lambda x, y: Union[x, y], schemas)

        builder = self

        class Builder(BaseModel):
            configurations: list[schema]

            async def build(self) -> ConfigProvider:
                values = {}
                for i, config in enumerate(self.configurations):
                    backend = builder._backends[config.backend]
                    try:
                        loaded_values = list(
                            (config.prefix + k, v)
                            for k, v in await backend.get_values(config)
                        )
                        values.update(loaded_values)
                    except Exception as e:
                        raise validation_error(Builder, e, ("configurations", i))
                return values

        return Builder

    def register_backend(self, backend: ConfigResolver) -> None:
        self._backends[backend.name] = backend
        if self._backend_config_models is None:
            self._backend_config_models = backend.args_model
        else:
            self._backend_config_models = Union[
                self._backend_config_models, backend.args_model
            ]

    # def parse_config(self, config: dict):
    #     if "backend" in config:
    #         backend_type = config["backend"]
    #         backend = self._backends[backend_type]
    #         return backend.args_model.parse_object(config)
    #     raise InvalidConfigResolver(config)
    #
    # def add(self, config: ConfigResolverSchema):
    #     self._to_build.append(config)
    #
    # async def build(self) -> ConfigProvider:
    #     values = {}
    #     for config in self._to_build:
    #         resolver_config = self.parse_config(config.data)
    #         backend = self._backends[resolver_config.name]
    #         values.update(await backend.get_values(resolver_config))
    #     return values
