import pytest
from pydantic import ValidationError

from onion.components import Application
from onion.core.events import DefaultEventDispatcher
from onion.declarations import DeclarationProcessor
from onion.declarations.schema import ComponentSchema, Reference


async def test_declaration(default_schema):
    schema = default_schema(
        components=[
            ComponentSchema(
                name="actuator",
                cls="example_app.actuator.Actuator",
                props=dict(
                    threshold=10.0,
                    event=Reference.create("thermometer", "temperature")
                )
            ),
            ComponentSchema(
                name="checker",
                cls="example_app.checker.ThresholdChecker",
                props=dict(
                    threshold=10.0,
                    temperature=Reference.create("thermometer", "temperature")
                )
            ),
            ComponentSchema(
                name="thermometer",
                cls="example_app.thermometer.Thermometer",
                props=dict(
                    temperature=5.0
                )
            )
        ]
    )

    processor = DeclarationProcessor(
        schema
    )

    dispatcher = DefaultEventDispatcher()

    application = Application(dispatcher)

    with application.factory() as factory:
        processor.create_with(factory)

    thermometer = application.components["thermometer"]
    actuator = application.components["actuator"]

    await application.run()

    assert actuator.worked == 0

    thermometer.temperature.value = 50.0

    await application.run()

    assert actuator.worked == 1


def test_parsing_declaration(default_schema):
    schema = default_schema(
        components=[
            ComponentSchema(
                name="checker",
                cls="example_app.checker.ThresholdChecker",
                props=dict(
                    threshold=10.0,
                    temperature=Reference.create("thermometer", "temperature")
                )
            ),
        ]
    )

    with pytest.raises(ValidationError):
        DeclarationProcessor(schema)

    schema = default_schema(
        components=[
            ComponentSchema(
                name="checker",
                cls="example_app.checker.ThresholdChecker",
                props=dict(
                    threshold=10.0,
                    temperature=Reference.create("thermometer", "temperature")
                )
            ),
        ]
    )