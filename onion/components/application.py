import asyncio
from contextlib import contextmanager

from onion.core.events import EventDispatcher, DefaultEventHub
from . import Setup, Runnable
from .container import ComponentContainer
from .factory import ComponentFactory


class Application(Runnable):
    def __init__(self, dispatcher: EventDispatcher):
        self.dispatcher = dispatcher
        self.event_hub = DefaultEventHub()
        self.components = ComponentContainer()

    @contextmanager
    def factory(self) -> ComponentFactory:
        loop = asyncio.get_running_loop()
        static = [self, self.components, self.dispatcher, loop]
        factory = ComponentFactory(
            self.dispatcher, self.event_hub, self.components, static
        )
        with factory:
            yield factory

    async def _setup_components(self) -> None:
        tasks = []
        for component in self.components:
            if isinstance(component, Setup):
                tasks.append(component.setup())
        if tasks:
            await asyncio.gather(*tasks)

    async def run(self) -> None:
        await self._setup_components()

        tasks = [self.dispatcher.run()]
        for component in self.components:
            if isinstance(component, Runnable):
                tasks.append(component.run())

        if tasks:
            await asyncio.gather(*tasks)

    async def stop(self) -> None:
        tasks = []
        for component in self.components:
            if isinstance(component, Runnable):
                tasks.append(component.stop())

        if tasks:
            await asyncio.gather(*tasks)
