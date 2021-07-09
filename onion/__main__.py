import asyncio
import logging
import signal
from argparse import ArgumentParser
from enum import Enum
from functools import partial
from typing import Optional

import yaml

from onion.components import Application
from onion.core.events import DefaultEventDispatcher
from onion.declarations import DeclarationSchema, DeclarationProcessor
from onion.declarations.contextual.config import ConfigContext
from onion.declarations.contextual.config.factory import ConfigProviderFactory
from onion.declarations.contextual.config.impl.yaml import YamlConfigResolver
from onion.declarations.contextual.evaluation import EvaluationContext


class LogLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"


log_level_value = {
    LogLevel.ERROR: logging.ERROR,
    LogLevel.WARNING: logging.WARNING,
    LogLevel.INFO: logging.INFO,
    LogLevel.DEBUG: logging.DEBUG,
}


async def main():
    parser = ArgumentParser("onion")
    parser.add_argument("filename", type=str)
    parser.add_argument("--log-level", type=LogLevel, default=LogLevel.ERROR)

    args = parser.parse_args()

    log_level = args.log_level

    logging.basicConfig(level=log_level_value[log_level])

    config_factory = ConfigProviderFactory(backends=[YamlConfigResolver()])

    with open(args.filename) as f:
        raw_schema = yaml.safe_load(f)

    schema = config_factory.schema()

    config_schema = schema.parse_obj(raw_schema)

    resolver = ConfigContext(backends=[await config_schema.build()])
    context = EvaluationContext({})

    dispatcher = DefaultEventDispatcher()

    application = Application(dispatcher)

    logger = logging.getLogger("onion")

    with resolver.context():
        with context.context():
            schema = DeclarationSchema.parse_obj(raw_schema)
            declaration = DeclarationProcessor(schema)

            with application.factory() as factory:
                declaration.create_with(factory)

            loop = asyncio.get_running_loop()
            stop_task: Optional[asyncio.Task] = None

            def callback(signum):
                nonlocal stop_task
                logger.info("Received signal %s", signum)
                stop_task = loop.create_task(application.stop())

            loop.add_signal_handler(signal.SIGINT, partial(callback, signal.SIGINT))
            loop.add_signal_handler(signal.SIGTERM, partial(callback, signal.SIGTERM))

            task = asyncio.create_task(application.run())

            logger.info("Starting")
            await task

            if stop_task is not None:
                await stop_task


if __name__ == "__main__":
    asyncio.run(main())
