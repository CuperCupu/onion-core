import inspect
from collections import abc
from typing import TypeVar, Any, Type, get_origin, get_args, Union, Iterable

from onion.components.component import Inject, PropertyImpl, PropertyView, Input
from onion.core.events import EventHub, EventSource, EventSourceImpl, EventDispatcher
from .base import Component, Property
from .container import ComponentContainer
from .reflection import ClassReflection, FieldReflection

T = TypeVar("T")


class ComponentException(Exception):
    pass


class DependencyNotFound(ComponentException):
    def __init__(self, component: str, type_: type):
        super().__init__(
            f"Component '{component}' depends on type {type_} with no known instance"
        )
        self.component = component
        self.type = type_


class AmbiguousDependency(ComponentException):
    def __init__(self, component: str, type_: type, candidates: list[Any]):
        candidate_string = "\n".join(f"\t{x.name}: {x}" for x in candidates)
        super().__init__(
            f"Component '{component}' depends on type {type_} with multiple possibility:\n{candidate_string}"
        )
        self.component = component
        self.type = type_
        self.candidates = candidates


class _ObjectInitializer:
    def __init__(
        self,
        name: str,
        instance: Any,
        kwargs: dict,
        dispatcher: EventDispatcher,
        event_hub: EventHub,
    ):
        self.name = name
        self.instance = instance
        self.type = type(instance)
        self.kwargs = kwargs
        self.dispatcher = dispatcher
        self.event_hub = event_hub
        self._initialize_fields()

    @staticmethod
    def need_initializing(type_: type) -> bool:
        return hasattr(type_, "__annotations__")

    def _initialize_fields(self) -> None:
        reflection = ClassReflection(self.type)
        for field in reflection.properties:
            self._add_property(field)
        for field in reflection.events:
            self._add_event(field)

    def _resolve_field(self, field: FieldReflection, default=None):
        if field.name in self.kwargs:
            value = self.kwargs.pop(field.name)
            if isinstance(field.default, Input) and not isinstance(value, field.origin):
                raise TypeError(field.name, type(value), value)
        else:
            if field.default is ...:
                if default:
                    value = default()
                else:
                    prop_type = field.args[0]
                    if get_origin(prop_type) == Union and type(None) in get_args(
                        prop_type
                    ):
                        value = None
                    else:
                        raise ValueError(field.name)
            elif isinstance(field.default, Input):
                raise ValueError(field.name)
            else:
                value = field.default
        return value

    def _add_property(self, field: FieldReflection) -> None:
        try:
            value = self._resolve_field(field)
        except ValueError as exc:
            raise ValueError(
                f"Missing value for property '{field.name}' for component '{self.name}'"
            ) from exc
        except TypeError as exc:
            value = PropertyImpl(None, exc.args[2], self.dispatcher)
        if isinstance(value, Property):
            prop = PropertyView(self.instance, value)
        else:
            prop = PropertyImpl(self.instance, value, self.dispatcher)
            self.event_hub.register(f"{self.name}!{field.name}", prop)
        setattr(self.instance, field.name, prop)

    def _add_event(self, field: FieldReflection) -> None:
        try:
            value = self._resolve_field(field, EventSourceImpl)
        except ValueError as exc:
            raise ValueError(
                f"Missing value for event '{field.name}' for component '{self.name}'"
            ) from exc
        except TypeError as exc:
            raise ValueError(
                f"Invalid value for event '{field.name}' for component '{self.name}'. An instance of "
                f"EventSource is required, not {exc.args[1]}"
            ) from exc
        if isinstance(value, EventSource):
            prop = value
        else:
            prop = EventSourceImpl()
            self.event_hub.register(f"{self.name}!{field.name}", prop)
        setattr(self.instance, field.name, prop)


class ComponentFactory:
    def __init__(
        self,
        dispatcher: EventDispatcher,
        event_hub: EventHub,
        container: ComponentContainer = None,
        static: list[Any] = None,
    ):
        self.dispatcher = dispatcher
        self.event_hub = event_hub
        self.container = container
        self._component_of_types = {}
        self._to_initialize = []
        if static:
            for item in static:
                self._save_component_type(type(item), item)

    def _get(self, type_: Type[T], singular=True) -> T:
        if type_ not in self._component_of_types:
            raise KeyError(type_)
        components = self._component_of_types[type_]
        if singular:
            if len(components) > 1:
                raise ValueError(components)
            return components[0]
        return list(components)

    def _get_dependency(self, depend_on_type: Any, singular: bool = True) -> Any:
        origin = get_origin(depend_on_type)
        if origin is None:
            depend_on = self._get(depend_on_type, singular)
        else:
            if origin == Union:
                types = []
                optional = False
                for arg in get_args(depend_on_type):
                    if arg is None:
                        optional = True
                    else:
                        types.append(arg)

                if singular:
                    depend_on = None

                    for type_ in types:
                        try:
                            depend_on = self._get_dependency(type_)
                            break
                        except KeyError:
                            continue

                    if depend_on is None and not optional:
                        raise KeyError(depend_on_type)
                else:
                    depend_on = []

                    for type_ in types:
                        try:
                            depend_on.append(self._get_dependency(type_))
                        except KeyError:
                            continue

                    if len(depend_on) == 0 and not optional:
                        raise KeyError(depend_on_type)

            elif issubclass(origin, (abc.Collection, abc.Container, abc.Iterable)):
                depend_on_type = get_args(depend_on_type)[0]
                depend_on = self._get_dependency(depend_on_type, False)
            else:
                depend_on = None
        return depend_on

    def _inject_dependencies(self, name: str, type_: type, kwargs):
        signature = inspect.signature(type_.__init__)

        dependencies = []

        for param in signature.parameters.values():
            if param.name not in kwargs and isinstance(param.default, Inject):
                if param.default.type is ...:
                    depend_on_type = param.annotation
                else:
                    depend_on_type = param.default.type
                try:
                    depend_on = self._get_dependency(depend_on_type)
                except KeyError:
                    raise DependencyNotFound(name, depend_on_type)
                except ValueError as e:
                    raise AmbiguousDependency(name, depend_on_type, e.args[0])
                if depend_on:
                    kwargs[param.name] = depend_on
                    if isinstance(depend_on, list):
                        dependencies.extend(depend_on)
                    else:
                        dependencies.append(depend_on)

        return dependencies

    def _save_component_type(self, type_: type, instance: Any) -> None:
        for t in type_.mro():
            if t not in self._component_of_types:
                self._component_of_types[t] = [instance]
            else:
                self._component_of_types[t].append(instance)

    def add(
        self,
        name: str,
        type_: Type[T],
        args: Iterable[Any] = tuple(),
        kwargs: dict = None,
        properties: dict = None,
    ) -> Union[T, Component]:
        kwargs = kwargs or {}
        properties = properties or {}

        instance = type_.__new__(type_)

        instance.name = name

        if _ObjectInitializer.need_initializing(type_):
            _ObjectInitializer(
                name, instance, properties, self.dispatcher, self.event_hub
            )

        self._to_initialize.append((instance, name, args, kwargs))

        self._save_component_type(type_, instance)

        return instance

    @staticmethod
    def _initialize(args, kwargs, instance: Any) -> None:
        instance.__init__(*args, **kwargs)

    def initialize(self) -> None:
        """Initialize each components by calling their `__init__` method. The components are sorted before hand based
        on the dependency graph. If `container` is not None, each component is added after initialized"""

        definitions = {}
        has_dependencies = []
        to_initialize = []
        for instance, name, args, kwargs in self._to_initialize:
            type_ = type(instance)
            dependencies = self._inject_dependencies(name, type_, kwargs)
            if dependencies:
                has_dependencies.append(name)
                definitions[name] = (
                    list(x.name for x in dependencies if hasattr(x, "name")),
                    instance,
                    args,
                    kwargs,
                )
            else:
                to_initialize.append((instance, args, kwargs))

        visited = set()

        def visit(comp_name):
            if name in visited:
                return

            visited.add(name)
            if comp_name not in definitions:
                return

            dependencies, *values = definitions[comp_name]
            for depended in dependencies:
                visit(depended)

            to_initialize.append(values)

        for name in has_dependencies:
            visit(name)

        for instance, args, kwargs in to_initialize:
            self._initialize(args, kwargs, instance)

            if self.container is not None:
                self.container.add(instance)

        self._to_initialize.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.initialize()
