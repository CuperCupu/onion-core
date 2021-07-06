from typing import Any, Union, List

from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper

from onion.components.factory import ComponentFactory
from .repl import DictReference, ListReference, Replaceable
from .schema import Reference, ComponentSchema, DeclarationSchema


class DeclarationException(Exception):
    pass


class DeclarationProcessor:

    def __init__(self, schema: DeclarationSchema):
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
            ref = Reference.create(ref=declared.placeholder.name)
            ref_repl = Replaceable(declared.owner, declared.location, ref)
            to_refer.append(ref_repl)
            declared.replace(ref)
        self._to_refer.extend(to_refer)
        self.schema.components = [*new_schemas, *self.schema.components]
        self._travel_schemas(new_schemas)

    def _parse_components(self, components: list[ComponentSchema]) -> tuple[list[Replaceable[Reference]], list[
        Replaceable[
            ComponentSchema]]]:
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
                            NameError(
                                f"Invalid reference '{field_value.ref}' for field {fields_type} of {schema.name}"),
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
