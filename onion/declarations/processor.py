from typing import Any, Union, Sequence

from onion.components.factory import ComponentFactory
from .repl import Replaceable, VariableReference
from .schema import Reference, ComponentSchema, DeclarationSchema
from .util import validation_error


class DeclarationException(Exception):
    pass


class DeclarationProcessor:
    _schemas: dict[str, ComponentSchema]
    _to_refer: list[Replaceable[Reference]]

    def __init__(self, schema: DeclarationSchema):
        self.schema = schema.copy(deep=True)
        self._schemas = {}
        for component in self.schema.components:
            self._register_schema(component)

        self._to_refer = []

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
                properties=schema.props,
            )
            references[component.name] = component

            components.append(component)

        return components

    def _register_schema(self, schema: ComponentSchema, root: str = None) -> None:
        root = root.split(".") if root else []
        if schema.name in self._schemas:
            raise validation_error(
                DeclarationSchema,
                ValueError(f"Duplicate component name '{schema.name}'"),
                ("components", *root),
            )
        self._schemas[schema.name] = schema

    def _travel_schemas(self, components: list[ComponentSchema]) -> None:
        """Travel the components schema to flatten nested definitions."""
        if not components:
            return
        to_refer, to_declare = self._parse_components(components)
        new_schemas = []
        for declared in to_declare:
            self._register_schema(declared.placeholder, declared.owner.name)
            new_schemas.append(declared.placeholder)
            ref = Reference.of(ref=declared.placeholder.name)
            ref_repl = Replaceable(declared.owner, declared.location, declared.ref, ref)
            to_refer.append(ref_repl)
            declared.owner.to_refer.append(ref_repl)
            declared.replace(ref)
        self._to_refer.extend(to_refer)
        self.schema.components = [*new_schemas, *self.schema.components]
        self._travel_schemas(new_schemas)

    def _parse_components(
        self, components: list[ComponentSchema]
    ) -> tuple[list[Replaceable[Reference]], list[Replaceable[ComponentSchema]]]:
        references = []
        declarations = []
        for component in components:
            ref_1, decl_1 = self._process_field(
                component, component.args, (component.name, "args")
            )
            ref_2, decl_2 = self._process_field(
                component, component.kwargs, (component.name, "kwargs")
            )
            ref_3, decl_3 = self._process_field(
                component, component.props, (component.name, "props")
            )

            references.extend(ref_1)
            references.extend(ref_2)
            references.extend(ref_3)
            declarations.extend(decl_1)
            declarations.extend(decl_2)
            declarations.extend(decl_3)

        return references, declarations

    def _process_field(
        self,
        schema: ComponentSchema,
        fields: Union[list[Any], dict[str, Any]],
        root_loc: Sequence[str],
    ):
        references = []
        declaration = []

        def parse_field(field, field_name, field_value, loc: Sequence[str]):
            if isinstance(field_value, Reference):
                if field_value.ref not in self._schemas:
                    raise validation_error(
                        type(schema),
                        NameError(f"Invalid reference: '{field_value.ref}'"),
                        loc,
                    )
                if len(loc) == 3:
                    expected_type = ...
                    field_type = loc[1]
                    if field_type == "props":
                        prop = schema.reflection.get_prop(field_name)
                        if prop is not None:
                            expected_type = prop.origin or prop.type
                    if expected_type is not ...:
                        ref_schema = self._schemas[field_value.ref]
                        if field_value.prop:
                            ref_field = ref_schema.reflection.get_prop(field_value.prop)
                            actual_type = ref_field.origin or ref_field.type
                        else:
                            actual_type = ref_schema.cls
                        if not issubclass(actual_type, expected_type):
                            raise validation_error(
                                type(schema),
                                TypeError(
                                    f"Reference type mismatch:"
                                    f"\n    {field_value}"
                                    f"\n    actual_type={actual_type}"
                                    f"\n    expected_type={expected_type}\n"
                                ),
                                loc,
                            )

                references.append(
                    Replaceable(
                        schema,
                        location=loc,
                        ref=VariableReference(field, field_name),
                        placeholder=field_value,
                    )
                )
            elif isinstance(field_value, ComponentSchema):
                field_value.name = schema.name + "." + field_value.name
                declaration.append(
                    Replaceable(
                        schema,
                        location=loc,
                        ref=VariableReference(field, field_name),
                        placeholder=field_value,
                    )
                )
            elif isinstance(field_value, list):
                for i, item in enumerate(field_value):
                    parse_field(field_value, i, item, (*loc, i))
            elif isinstance(field_value, dict):
                for sub_key, sub_value in field_value.items():
                    parse_field(field_value, sub_key, sub_value, (*loc, sub_key))

        if isinstance(fields, list):
            for key, value in enumerate(fields):
                parse_field(fields, key, value, (*root_loc, key))
        elif isinstance(fields, dict):
            for key, value in fields.items():
                parse_field(fields, key, value, (*root_loc, key))

        schema.to_refer.extend(references)

        return references, declaration
