from __future__ import annotations

import importlib
from typing import Optional, Any, Union, List, TextIO, Iterable, TypeVar

import yaml
from pydantic import BaseModel, Field, PrivateAttr, validator

from onion.components import Input
from onion.components.reflection import ClassReflection
from .contextual import Evaluable, ConfigProperty, EvaluatedProperty
from .repl import Replaceable
from .util import validation_error

T = TypeVar("T")

RichType = Union[ConfigProperty[T], EvaluatedProperty[T], T]


def substitute(value):
    if isinstance(value, Evaluable):
        return value.evaluate()
    elif isinstance(value, list):
        return list(substitute(x) for x in value)
    elif isinstance(value, dict):
        return {k: substitute(v) for k, v in value.items()}
    return value


RichStr = RichType[str]
RichInt = RichType[str]


class SchemaBaseModel(BaseModel):
    @validator("*", each_item=False, always=True)
    def validate_each_item(cls, v):
        return substitute(v)


class Reference(SchemaBaseModel):
    ref: RichStr = Field(alias="$ref")
    prop: Optional[RichStr] = Field(alias="$prop", default=None)

    def resolve(self, references) -> Any:
        ref = references[self.ref]
        if self.prop is not None:
            ref = getattr(ref, self.prop)
        return ref

    @staticmethod
    def of(ref: str, prop: Optional[str] = None) -> "Reference":
        return Reference.parse_obj({"$ref": ref, "$prop": prop})


class ComponentSchema(SchemaBaseModel):
    """Declaration of a Component"""

    name: RichStr
    cls: Union[type, RichStr]  # Import name of the class
    args: list[
        Union[
            Reference,
            list[Reference],
            ComponentSchema,
            list[ComponentSchema],
            RichType[Any],
        ]
    ] = []
    kwargs: dict[
        str,
        Union[
            Reference,
            list[Reference],
            ComponentSchema,
            list[ComponentSchema],
            RichType[Any],
        ],
    ] = {}
    props: dict[
        str,
        Union[
            Reference,
            list[Reference],
            ComponentSchema,
            list[ComponentSchema],
            RichType[Any],
        ],
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


class DeclarationSchema(SchemaBaseModel):
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
