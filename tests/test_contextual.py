import pytest

from onion.components import Application
from onion.core.events import DefaultEventDispatcher
from onion.declarations import DeclarationProcessor, ValidationError
from onion.declarations.contextual import ConfigProperty, ConfigResolver
from onion.declarations.schema import ComponentSchema, Reference


@pytest.mark.parametrize("value", (5.0, 100.0, 25.0))
async def test_config_resolution(default_app, default_schema, value: float):
    resolver = ConfigResolver(backends=[{"temperature": value}])
    with resolver.context():
        schema = default_schema(
            components=[
                ComponentSchema(
                    name="thermometer",
                    cls="example_app.Thermometer",
                    # props=dict(temperature=ConfigProperty.of("temperature")),
                    props=dict(temperature={"$config": "temperature"}),
                ),
            ]
        )

    application = default_app(schema)

    thermometer = application.components["thermometer"]

    assert thermometer.temperature.value == value
