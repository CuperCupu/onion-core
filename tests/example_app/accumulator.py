from asyncio import AbstractEventLoop
from typing import Union

from onion.components.component import Inject
from onion.core.events import EventDispatcher
from tests.example_app.checker import ThresholdChecker


class Accumulator:

    def __init__(self, *, checker: list[Union[ThresholdChecker, AbstractEventLoop]] = Inject(), dispatcher: EventDispatcher = Inject()):
        print(checker)
        print(dispatcher)
