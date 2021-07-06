from typing import Mapping, Iterator

from .base import Component


class ComponentContainer(Mapping[str, Component]):
    _components: dict[str, Component]

    def __init__(self):
        self._components = {}

    def add(self, component: Component) -> None:
        if component.name in self._components:
            raise KeyError(f"Component with name '{component.name}' already exists")
        self._components[component.name] = component

    def __getitem__(self, k: str) -> Component:
        return self._components[k]

    def __len__(self) -> int:
        return len(self._components)

    def __iter__(self) -> Iterator[Component]:
        return iter(self._components.values())
