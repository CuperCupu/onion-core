import asyncio

import pytest

from onion.declarations import ComponentSchema, DeclarationSchema


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        if isinstance(item, pytest.Function) and asyncio.iscoroutinefunction(
            item.function
        ):
            item.add_marker(pytest.mark.asyncio_cooperative)


def _create_default_schema(components: list[ComponentSchema]) -> DeclarationSchema:
    return DeclarationSchema(name="testing", version="testing", components=components)


@pytest.fixture
def default_schema():
    return _create_default_schema
