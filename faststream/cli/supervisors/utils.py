import asyncio
import multiprocessing
import os
import signal
import sys
from multiprocessing.context import SpawnProcess
from types import FrameType
from typing import Any, Callable, Optional

from faststream.types import DecoratedCallableNone

multiprocessing.allow_connection_pickling()
spawn = multiprocessing.get_context("spawn")


HANDLED_SIGNALS = (
    signal.SIGINT,  # Unix signal 2. Sent by Ctrl+C.
    signal.SIGTERM,  # Unix signal 15. Sent by `kill <pid>`.
)


def set_exit(func: Callable[[int, Optional[FrameType]], Any]) -> None:
    """Set exit handler for signals.

    Args:
        func: A callable object that takes an integer and an optional frame type as arguments and returns any value.
    """
    try:
        loop = asyncio.get_event_loop()

        for sig in HANDLED_SIGNALS:
            loop.add_signal_handler(sig, func, sig, None)

    except NotImplementedError:  # pragma: no cover
        # Windows
        for sig in HANDLED_SIGNALS:
            signal.signal(sig, func)



def get_subprocess(target: DecoratedCallableNone, args: Any) -> SpawnProcess:
    """Spawn a subprocess.

    Args:
        target: The target function to be executed in the subprocess.
        args: The arguments to be passed to the target function.

    Returns:
        The spawned subprocess.

    Raises:
        OSError: If there is an error getting the file descriptor of sys.stdin.

    """
    stdin_fileno: Optional[int]
    try:
        stdin_fileno = sys.stdin.fileno()
    except OSError:
        stdin_fileno = None

    return spawn.Process(
        target=subprocess_started,
        args=args,
        kwargs={"t": target, "stdin_fileno": stdin_fileno},
    )


def subprocess_started(
    *args: Any,
    t: DecoratedCallableNone,
    stdin_fileno: Optional[int],
) -> None:
    """Start a subprocess.

    Args:
        *args: Arguments to be passed to the subprocess.
        t: The decorated callable function.
        stdin_fileno: File descriptor for the standard input of the subprocess.

    Returns:
        None

    """
    if stdin_fileno is not None:  # pragma: no cover
        sys.stdin = os.fdopen(stdin_fileno)
    t(*args)
