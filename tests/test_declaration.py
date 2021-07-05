import pytest

from onion.components import Application
from onion.core.events import DefaultEventDispatcher
from onion.declarations.declaration import Declaration


@pytest.mark.asyncio_cooperative
async def test_declaration():
    with open("tests/declaration.yaml") as f:
        declaration = Declaration.from_yaml(f)

    dispatcher = DefaultEventDispatcher()

    application = Application(dispatcher)

    with application.factory() as factory:
        declaration.create_with(factory)

    await application.run()
