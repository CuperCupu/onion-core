from __future__ import annotations

import importlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, TextIO, Optional, Union, Protocol, runtime_checkable, Generic, TypeVar, List

import yaml
from pydantic import BaseModel, validator, Field, ValidationError, PrivateAttr
from pydantic.error_wrappers import ErrorWrapper

from onion.components.factory import ComponentFactory, ClassReflection


class CompType(str, Enum):
    COMPONENT = "component"


class Reference(BaseModel):
    ref: str = Field(alias="$ref")
    prop: Optional[str] = Field(alias="$prop", default=None)

    def resolve(self, references) -> Any:
        ref = references[self.ref]
        if self.prop is not None:
            ref = getattr(ref, self.prop)
        return ref


class ComponentSchema(BaseModel):
    """Declaration of a Component"""
    name: str
    cls: type  # Import name of the class
    args: list[Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any]] = []
    kwargs: dict[str, Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any]] = {}
    props: dict[str, Union[Reference, list[Reference], ComponentSchema, list[ComponentSchema], Any]] = {}  # The initial value of properties
    _to_refer: list[Replaceable[Reference]] = PrivateAttr([])

    @property
    def to_refer(self) -> List[Replaceable[Reference]]:
        return self._to_refer

    @validator("cls", pre=True)
    def validate_cls(cls, v):
        module_name, cls_name = v.rsplit(".", maxsplit=1)
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            raise ValueError(f"No module named '{module_name}'")
        cls_ = getattr(module, cls_name, ...)
        if cls_ is ...:
            raise ValueError(f"'{cls_name}' is not found module '{module_name}'")

        return cls_

    @validator("props")
    def validate_properties(cls, v, values):
        reflection = ClassReflection(values["cls"])
        reflection.properties

        return v


ComponentSchema.update_forward_refs()


# class ComponentDecl(BaseModel):
#     name: str
#     type: CompType
#     _value: Union[ComponentSchema] = PrivateAttr()
#
#     @property
#     def value(self) -> Union[ComponentSchema]:
#         return self._value
#
#     def __init__(self, **data: Any):
#         super().__init__(**data)
#
#         if self.type == CompType.COMPONENT:
#             self._value = ComponentSchema.parse_obj(data)
#         else:
#             raise TypeError(f"Unknown component type: {self.type}")


class DeclarationSchema(BaseModel):
    name: str
    version: str
    requirements: list[str] = []
    includes: list[str] = []
    components: list[ComponentSchema]


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


class DeclarationException(Exception):
    pass


class Declaration:

    def __init__(self, schema: Union[dict[str, Any], DeclarationSchema]):
        if isinstance(schema, dict):
            self.schema = DeclarationSchema.parse_obj(schema)
        else:
            self.schema = schema.copy(deep=True)
        self._schemas = {}
        for component in self.schema.components:
            self._register_schema(component)

        self._to_refer: List[Replaceable[Reference]] = []

        self._travel_schemas(self.schema.components)
        self._created = False

    def create_with(self, factory: ComponentFactory) -> list[Any]:
        if self._created:
            raise ValueError("Unable to reuse declaration")
        self._created = True

        to_instantiate = []
        visited = set()

        def visit(schema_: ComponentSchema):
            if schema_.name in visited:
                return
            visited.add(schema_.name)

            for repl_ in schema_.to_refer:
                ref_ = repl_.placeholder.ref
                ref_schema = self._schemas[ref_]
                visit(ref_schema)

            to_instantiate.append(schema_)

        for schema in self.schema.components:
            visit(schema)

        components = []
        references = {}
        for schema in to_instantiate:
            for repl in schema.to_refer:
                ref = repl.placeholder
                repl.replace(ref.resolve(references))

            component = factory.add(
                name=schema.name,
                type_=schema.cls,
                args=schema.args,
                kwargs=schema.kwargs,
                properties=schema.props
            )
            references[component.name] = component

            components.append(component)

        return components

    def _register_schema(self, schema: ComponentSchema, root: str = None) -> None:
        root = root.split(".") if root else []
        if schema.name in self._schemas:
            raise ValidationError(
                [ErrorWrapper(ValueError(f"Duplicate component name '{schema.name}'"), loc=("components", *root))],
                DeclarationSchema
            )
        self._schemas[schema.name] = schema

    def _travel_schemas(self, components: list[ComponentSchema]) -> None:
        """Travel the components schema to flatten nested definitions."""
        if not components:
            return
        to_refer, to_declare = self._parse_components(components)
        new_schemas = []
        for declared in to_declare:
            self._register_schema(declared.placeholder, declared.owner)
            new_schemas.append(declared.placeholder)
            ref = Reference.parse_obj({"$ref": declared.placeholder.name})
            ref_repl = Replaceable(declared.owner, declared.location, ref)
            to_refer.append(ref_repl)
            declared.replace(ref)
        self._to_refer.extend(to_refer)
        self.schema.components = [*new_schemas, *self.schema.components]
        self._travel_schemas(new_schemas)

    def _parse_components(self, components: list[ComponentSchema]) -> tuple[list[Replaceable[Reference]], list[Replaceable[ComponentSchema]]]:
        references = []
        declarations = []
        for component in components:
            ref_1, decl_1 = self._process_field(component, component.args, "args")
            ref_2, decl_2 = self._process_field(component, component.kwargs, "kwargs")
            ref_3, decl_3 = self._process_field(component, component.props, "prop")

            references.extend(ref_1)
            references.extend(ref_2)
            references.extend(ref_3)
            declarations.extend(decl_1)
            declarations.extend(decl_2)
            declarations.extend(decl_3)

        return references, declarations

    def _process_field(self, schema: ComponentSchema, fields: Union[list[Any], dict[str, Any]], fields_type: str):
        references = []
        declaration = []

        def parse_field(field, field_name, field_value):
            ref_cls = DictReference if isinstance(field, dict) else ListReference
            if isinstance(field_value, Reference):
                if field_value.ref not in self._schemas:
                    raise ValidationError(
                        [ErrorWrapper(
                            NameError(f"Invalid reference '{field_value.ref}' for field {fields_type} of {schema.name}"),
                            loc=(schema.name, field_name,)
                        )],
                        type(schema)
                    )
                references.append(Replaceable(
                    schema.name,
                    location=ref_cls(field, field_name),
                    placeholder=field_value
                ))
            elif isinstance(field_value, ComponentSchema):
                field_value.name = schema.name + "." + field_value.name
                declaration.append(Replaceable(
                    schema.name,
                    location=ref_cls(field, field_name),
                    placeholder=field_value
                ))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    parse_field(value, i, item)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    parse_field(value, sub_key, sub_value)

        if isinstance(fields, list):
            for key, value in enumerate(fields):
                parse_field(fields, key, value)
        elif isinstance(fields, dict):
            for key, value in fields.items():
                parse_field(fields, key, value)

        schema.to_refer.extend(references)

        return references, declaration

    @staticmethod
    def from_yaml(f: TextIO) -> 'Declaration':
        data = yaml.full_load(f)
        return Declaration(data)
