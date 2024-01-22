from typing import Dict, Union, cast

import aio_pika

from faststream._compat import model_to_dict
from faststream.rabbit.shared.schemas import RabbitExchange, RabbitQueue
from faststream.utils.classes import Singleton


class RabbitDeclarer(Singleton):
    """A class to declare RabbitMQ queues and exchanges.

    Attributes:
        channel : aio_pika.RobustChannel
            The RabbitMQ channel to use for declaration.
        queues : Dict[Union[RabbitQueue, str], aio_pika.RobustQueue]
            A dictionary to store the declared queues.
        exchanges : Dict[Union[RabbitExchange, str], aio_pika.RobustExchange]
            A dictionary to store the declared exchanges.

    Methods:
        __init__(channel: aio_pika.RobustChannel) -> None
            Initializes the RabbitDeclarer with a channel.

        declare_queue(queue: RabbitQueue) -> aio_pika.RobustQueue
            Declares a queue and returns the declared queue object.

        declare_exchange(exchange: RabbitExchange) -> aio_pika.RobustExchange
            Declares an exchange and returns the declared exchange object.
    """

    channel: aio_pika.RobustChannel
    queues: Dict[Union[RabbitQueue, str], aio_pika.RobustQueue]
    exchanges: Dict[Union[RabbitExchange, str], aio_pika.RobustExchange]

    def __init__(self, channel: aio_pika.RobustChannel) -> None:
        """Initialize the class.

        Args:
            channel: Aio_pika RobustChannel object

        Attributes:
            channel: Aio_pika RobustChannel object
            queues: A dictionary to store queues
            exchanges: A dictionary to store exchanges
        """
        self.channel = channel
        self.queues = {}
        self.exchanges = {}

    async def declare_queue(
        self,
        queue: RabbitQueue,
    ) -> aio_pika.RobustQueue:
        """Declare a queue.

        Args:
            queue: RabbitQueue object representing the queue to be declared.

        Returns:
            aio_pika.RobustQueue: The declared queue.
        """
        q = self.queues.get(queue)
        if q is None:
            q = cast(
                aio_pika.RobustQueue,
                await self.channel.declare_queue(
                    **model_to_dict(
                        queue,
                        exclude={
                            "routing_key",
                            "path_regex",
                            "bind_arguments",
                        },
                    )
                ),
            )
            self.queues[queue] = q
        return q

    async def declare_exchange(
        self,
        exchange: RabbitExchange,
    ) -> aio_pika.RobustExchange:
        """Declare an exchange.

        Args:
            exchange: RabbitExchange object representing the exchange to be declared.

        Returns:
            aio_pika.RobustExchange: The declared exchange.

        Raises:
            NotImplementedError: If silent animals are not supported.
        """
        exch = self.exchanges.get(exchange)

        if exch is None:
            exch = cast(
                aio_pika.RobustExchange,
                await self.channel.declare_exchange(
                    **model_to_dict(
                        exchange,
                        exclude={
                            "routing_key",
                            "bind_arguments",
                            "bind_to",
                        },
                    )
                ),
            )
            self.exchanges[exchange] = exch

        if exchange.bind_to is not None:
            parent = await self.declare_exchange(exchange.bind_to)
            await exch.bind(
                exchange=parent,
                routing_key=exchange.routing_key,
                arguments=exchange.arguments,
            )

        return exch
