import logging
from functools import wraps
from typing import Awaitable, Callable, Optional, Union

from faststream.broker.message import StreamMessage
from faststream.broker.push_back_watcher import (
    BaseWatcher,
    CounterWatcher,
    EndlessWatcher,
    OneTryWatcher,
)
from faststream.broker.types import MsgType, T_HandlerReturn, WrappedReturn
from faststream.utils import context


def change_logger_handlers(logger: logging.Logger, fmt: str) -> None:
    """Change the formatter of the logger handlers.

    Args:
        logger (logging.Logger): The logger object.
        fmt (str): The format string for the formatter.

    Returns:
        None

    """
    for handler in getattr(logger, "handlers", ()):
        formatter = handler.formatter
        if formatter is not None:  # pragma: no branch
            use_colors = getattr(formatter, "use_colors", None)
            kwargs = (
                {"use_colors": use_colors} if use_colors is not None else {}
            )  # pragma: no branch

            handler.setFormatter(type(formatter)(fmt, **kwargs))


def get_watcher(
    logger: Optional[logging.Logger],
    try_number: Union[bool, int] = True,
) -> BaseWatcher:
    """Get a watcher object based on the provided parameters.

    Args:
        logger: Optional logger object for logging messages.
        try_number: Optional parameter to specify the type of watcher.
            - If set to True, an EndlessWatcher object will be returned.
            - If set to False, a OneTryWatcher object will be returned.
            - If set to an integer, a CounterWatcher object with the specified maximum number of tries will be returned.

    Returns:
        A watcher object based on the provided parameters.

    """
    watcher: Optional[BaseWatcher]
    if try_number is True:
        watcher = EndlessWatcher()
    elif try_number is False:
        watcher = OneTryWatcher()
    else:
        watcher = CounterWatcher(logger=logger, max_tries=try_number)
    return watcher


def set_message_context(
    func: Callable[
        [StreamMessage[MsgType]],
        Awaitable[WrappedReturn[T_HandlerReturn]],
    ],
) -> Callable[[StreamMessage[MsgType]], Awaitable[WrappedReturn[T_HandlerReturn]]]:
    """Sets the message context for a function.

    Args:
        func: The function to set the message context for.

    Returns:
        The function with the message context set.
    """

    @wraps(func)
    async def set_message_wrapper(
        message: StreamMessage[MsgType],
    ) -> WrappedReturn[T_HandlerReturn]:
        """Wraps a function that handles a stream message.

        Args:
            message: The stream message to be handled.

        Returns:
            The wrapped return value of the handler function.
        """
        with context.scope("message", message):
            return await func(message)

    return set_message_wrapper
