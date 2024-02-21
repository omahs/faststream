from typing import Any, Callable, Union

from aio_pika import IncomingMessage

from faststream.broker.core.call_wrapper import HandlerCallWrapper
from faststream.broker.fastapi.router import StreamRouter
from faststream.broker.types import (
    P_HandlerParams,
    T_HandlerReturn,
)
from faststream.rabbit.broker import RabbitBroker as RB
from faststream.rabbit.schemas.schemas import RabbitQueue


class RabbitRouter(StreamRouter[IncomingMessage]):
    """A class to represent a RabbitMQ router for incoming messages.

    Attributes:
        broker_class : the class representing the RabbitMQ broker

    Methods:
        _setup_log_context : sets up the log context for the main broker and the including broker
    """

    broker_class = RB

    def subscriber(  # type: ignore[override]
        self,
        queue: Union[str, RabbitQueue],
        *args: Any,
        **__service_kwargs: Any,
    ) -> Callable[
        [Callable[P_HandlerParams, T_HandlerReturn]],
        HandlerCallWrapper[IncomingMessage, P_HandlerParams, T_HandlerReturn],
    ]:
        queue = RabbitQueue.validate(queue)
        return super().subscriber(
            queue.name,
            queue,
            *args,
            **__service_kwargs,
        )

    @staticmethod
    def _setup_log_context(
        main_broker: RB,
        including_broker: RB,
    ) -> None:
        """Sets up the log context for a main broker and an including broker.

        Args:
            main_broker: The main broker object.
            including_broker: The including broker object.

        Returns:
            None
        """
        for h in including_broker.handlers.values():
            main_broker._setup_log_context(h.queue, h.exchange)
