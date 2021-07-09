import pytest

from onion.declarations import DeclarationProcessor, ValidationError
from onion.declarations.schema import ComponentSchema, Reference


async def test_declaration(default_app, default_schema):
    schema = default_schema(
        components=[
            ComponentSchema(
                name="actuator",
                cls="example_app.Actuator",
                props=dict(
                    threshold=10.0, event=Reference.of("thermometer", "temperature")
                ),
            ),
            ComponentSchema(
                name="checker",
                cls="example_app.ThresholdChecker",
                props=dict(
                    threshold=10.0,
                    temperature=Reference.of("thermometer", "temperature"),
                ),
            ),
            ComponentSchema(
                name="thermometer",
                cls="example_app.Thermometer",
                props=dict(temperature=5.0),
            ),
        ]
    )

    application = default_app(schema)

    thermometer = application.components["thermometer"]
    actuator = application.components["actuator"]

    await application.run()

    assert actuator.worked == 0

    thermometer.temperature.value = 50.0

    await application.run()

    assert actuator.worked == 1


def test_parsing_component_schema(default_schema):
    with pytest.raises(ValidationError):
        # Test for missing input property
        ComponentSchema(name="checker", cls="example_app.ThresholdChecker")

    with pytest.raises(ValidationError):
        # Test for missing input event
        ComponentSchema(name="actuator", cls="example_app.Actuator")


def test_parsing_missing_reference(default_schema):
    with pytest.raises(ValidationError):
        # Test for missing reference
        schema = default_schema(
            components=[
                ComponentSchema(
                    name="checker",
                    cls="example_app.ThresholdChecker",
                    props=dict(
                        threshold=10.0,
                        temperature=Reference.of("thermometer", "temperature"),
                    ),
                ),
            ]
        )

        DeclarationProcessor(schema)


@pytest.mark.parametrize(
    "reference",
    (
        Reference.of("thermometer"),
        Reference.of("checker"),
        Reference.of("checker", "changed"),
    ),
)
def test_parsing_mismatch_reference(default_schema, reference: Reference):
    with pytest.raises(ValidationError):
        # Test for mismatch reference type
        schema = default_schema(
            components=[
                ComponentSchema(
                    name="thermometer2",
                    cls="example_app.Thermometer",
                    props=dict(temperature=reference),
                ),
                ComponentSchema(
                    name="checker",
                    cls="example_app.ThresholdChecker",
                    props=dict(temperature=Reference.of("thermometer", "temperature")),
                ),
                ComponentSchema(
                    name="thermometer",
                    cls="example_app.Thermometer",
                    props=dict(temperature=5.0),
                ),
            ]
        )

        DeclarationProcessor(schema)


async def test_nested_component(default_app, default_schema):
    schema = default_schema(
        components=[
            ComponentSchema(
                name="simulator",
                cls="example_app.TemperatureSimulator",
                args=[10.0],
                kwargs=dict(
                    thermometer=ComponentSchema(
                        name="thermometer",
                        cls="example_app.Thermometer",
                        props=dict(temperature=5.0),
                    ),
                ),
            ),
        ]
    )

    application = default_app(schema)

    simulator = application.components["simulator"]
    thermometer = application.components["simulator.thermometer"]

    assert thermometer.temperature.value == 10.0
