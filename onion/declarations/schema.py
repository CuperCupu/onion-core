from __future__ import annotations

import importlib
from functools import cached_property
from typing import Optional, Any, Union, List, TextIO, Iterable

import yaml
from pydantic import BaseModel, Field, PrivateAttr, validator

from onion.components.reflection import ClassReflection
from .repl import Replaceable
from .util import validation_error
from ..components import Input


class Reference(BaseModel):
    ref: str = Field(alias="$ref")
    prop: Optional[str] = Field(alias="$prop", default=None)

    def resolve(self, references) -> Any:
        ref = references[self.ref]
        if self.prop is not None:
            ref = getattr(ref, self.prop)
        return ref

    @staticmethod
    def of(ref: str, prop: Optional[str] = None) -> "Reference":
        return Reference.parse_obj({"$ref": ref, "$prop": prop})


class ComponentSchema(BaseModel):
    """Declaration of a Component"""

    name: str
    cls: Union[type, str]  # Import name of the class
    args: list[
        Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any]
    ] = []
    kwargs: dict[
        str,
        Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any],
    ] = {}
    props: dict[
        str,
        Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any],
    ] = {}  # The initial value of properties
    _to_refer: list[Replaceable[Reference]] = PrivateAttr([])

    @property
    def to_refer(self) -> List[Replaceable[Reference]]:
        return self._to_refer

    @validator("cls", pre=True)
    def validate_cls(cls, v):
        if isinstance(v, str):
            module_name, cls_name = v.rsplit(".", maxsplit=1)
            try:
                module = importlib.import_module(module_name)
            except ModuleNotFoundError:
                raise ValueError(f"No module named '{module_name}'")
            cls_ = getattr(module, cls_name, ...)
            if cls_ is ...:
                raise ValueError(f"'{cls_name}' is not found module '{module_name}'")
        elif isinstance(v, type):
            cls_ = v
        else:
            raise TypeError(type(v))

        return cls_

    def _error(self, location: Iterable[str], error: Exception):
        raise validation_error(
            ComponentSchema, error, (*self.name.split("."), *location)
        )

    _reflection: ClassReflection = PrivateAttr()

    @property
    def reflection(self) -> ClassReflection:
        return self._reflection

    def validate_schema(self):
        self._reflection = ClassReflection(self.cls)
        for field in self.reflection.properties:
            if field.name not in self.props:
                if field.default is ...:
                    self._error(
                        ("props", field.name),
                        AttributeError("Missing default property value"),
                    )
                elif isinstance(field.default, Input):
                    self._error(("props", field.name), AttributeError("Missing input"))
        for field in self.reflection.events:
            if field.name not in self.props and isinstance(field.default, Input):
                self._error(
                    ("props", field.name), AttributeError("Missing input event")
                )

    def __init__(self, **data: Any):
        super().__init__(**data)
        self.validate_schema()


class DeclarationSchema(BaseModel):
    name: str
    version: str
    requirements: list[str] = []
    includes: list[str] = []
    components: list[ComponentSchema]

    @staticmethod
    def from_yaml(f: TextIO, safe: bool = True) -> "DeclarationSchema":
        if safe:
            data = yaml.safe_load(f)
        else:
            data = yaml.full_load(f)
        return DeclarationSchema.parse_obj(data)


ComponentSchema.update_forward_refs()
