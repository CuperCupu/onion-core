from typing import Union, TypeVar

from .base import Evaluable
from .evaluation import EvaluatedProperty
from .config.base import ConfigProperty

T = TypeVar("T")

EvaluableType = Union[ConfigProperty[T], EvaluatedProperty[T]]
