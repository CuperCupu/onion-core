import inspect
from functools import cached_property
from typing import get_origin, Optional, Any, get_args, Sequence, Tuple

from onion.core.events import EventSource
from .base import Property


class FieldReflection:
    def __init__(self, cls: type, name: str, type_: type = None):
        self.cls = cls
        self.name = name
        if type_ is None:
            if hasattr(cls, "__annotations__") and name in cls.__annotations__:
                self.type = cls.__annotations__[name]
            else:
                self.type = Any
        else:
            self.type = type_

    @cached_property
    def origin(self) -> Optional[type]:
        return get_origin(self.type)

    @cached_property
    def args(self) -> Sequence[Any]:
        return get_args(self.type)

    @cached_property
    def is_generic(self) -> bool:
        return self.origin is None

    @cached_property
    def default(self) -> Any:
        return getattr(self.cls, self.name, ...)

    def __repr__(self):
        return f"reflection.field(cls={self.cls}, name={self.name}, type={self.type}, default={self.default})"


class ClassReflection:
    def __init__(self, type_: type):
        self.type = type_

    @cached_property
    def init(
        self,
    ) -> Tuple[Sequence[Tuple[type, Any]], Sequence[Tuple[str, type, Any]]]:
        signature = inspect.signature(self.type.__init__)
        args = []
        kwargs = []
        for parameter in signature.parameters.values():
            if parameter.kind in (
                parameter.POSITIONAL_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
            ):
                type_ = (
                    Any
                    if parameter.annotation == parameter.empty
                    else parameter.annotation
                )
                def_value = (
                    ... if parameter.default == parameter.empty else parameter.default
                )
                args.append((type_, def_value))
            if parameter.kind in (
                parameter.POSITIONAL_OR_KEYWORD,
                parameter.KEYWORD_ONLY,
            ):
                type_ = (
                    Any
                    if parameter.annotation == parameter.empty
                    else parameter.annotation
                )
                def_value = (
                    ... if parameter.default == parameter.empty else parameter.default
                )
                kwargs.append((parameter.name, type_, def_value))
        return args, kwargs

    @cached_property
    def args(self) -> Sequence[Tuple[type, Any]]:
        return self.init[0]

    @cached_property
    def kwargs(self) -> Sequence[Tuple[str, type, Any]]:
        return self.init[1]

    @cached_property
    def props(self) -> list[FieldReflection]:
        return self._find_fields_for_generic(EventSource, Property)

    def get_prop(self, name: str) -> Optional[FieldReflection]:
        return next(filter(lambda x: x.name == name, self.props), None)

    def _find_fields_for_generic(self, *target):
        result = []
        if hasattr(self.type, "__annotations__"):
            annotations = self.type.__annotations__
            for field_name, field_type in annotations.items():
                field = FieldReflection(self.type, field_name, field_type)
                if field.origin in target:
                    result.append(field)
        return result

    @cached_property
    def properties(self) -> list[FieldReflection]:
        return self._find_fields_for_generic(Property)

    @cached_property
    def events(self) -> list[FieldReflection]:
        return self._find_fields_for_generic(EventSource)

    def __repr__(self):
        return f"reflection.class(cls={self.type})"
