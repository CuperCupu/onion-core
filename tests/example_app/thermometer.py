from onion.components import Property, Input
from onion.components.base import ValueChangedEvent


class Thermometer:
    name: str
    temperature: Property[float]
