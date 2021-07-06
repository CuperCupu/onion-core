import asyncio

import pytest

from onion.components import Application
from onion.core.events import DefaultEventDispatcher
from onion.declarations import ComponentSchema, DeclarationSchema, DeclarationProcessor


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if isinstance(item, pytest.Function) and asyncio.iscoroutinefunction(
            item.function
        ):
            item.add_marker(pytest.mark.asyncio_cooperative)


def _create_default_schema(components: list[ComponentSchema]) -> DeclarationSchema:
    return DeclarationSchema(name="testing", version="testing", components=components)


def _create_default_app(schema: DeclarationSchema) -> Application:
    dispatcher = DefaultEventDispatcher()

    application = Application(dispatcher)

    processor = DeclarationProcessor(schema)

    with application.factory() as factory:
        processor.create_with(factory)

    return application


@pytest.fixture
def default_schema():
    return _create_default_schema


@pytest.fixture
def default_app():
    return _create_default_app
