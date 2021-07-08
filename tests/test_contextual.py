import pytest

from onion.declarations.contextual import (
    ConfigProperty,
    ConfigResolver,
    GlobalContext,
    EvaluatedProperty,
)
from onion.declarations.schema import ComponentSchema


@pytest.mark.parametrize(
    ("value", "config"),
    (
        (5.0, ConfigProperty.of("temperature")),
        (100.0, {"$config": "temperature"}),
        (25.0, ConfigProperty.of("temperature")),
    ),
)
async def test_config_resolution(default_app, default_schema, value: float, config):
    resolver = ConfigResolver(backends=[{"temperature": value}])
    with resolver.context():
        schema = default_schema(
            components=[
                ComponentSchema(
                    name="thermometer",
                    cls="example_app.Thermometer",
                    props=dict(temperature=config),
                ),
            ]
        )

    application = default_app(schema)

    thermometer = application.components["thermometer"]

    assert thermometer.temperature.value == value


@pytest.mark.parametrize(("value", "expr"), ((5.0, {"$eval": "5"}),))
async def test_evaluation(default_app, default_schema, value: float, expr):
    resolver = ConfigResolver(backends=[{"temperature": 5}])
    context = GlobalContext({})

    with resolver.context():
        with context.context():
            schema = default_schema(
                components=[
                    ComponentSchema(
                        name="thermometer",
                        cls="example_app.Thermometer",
                        props=dict(temperature=expr),
                    ),
                    ComponentSchema(
                        name="thermometer2",
                        cls="example_app.Thermometer",
                        props=dict(
                            temperature=EvaluatedProperty.of("$config.temperature")
                        ),
                    ),
                ]
            )

    application = default_app(schema)

    thermometer = application.components["thermometer"]
    thermometer2 = application.components["thermometer2"]

    assert thermometer.temperature.value == value
    assert thermometer2.temperature.value == value
