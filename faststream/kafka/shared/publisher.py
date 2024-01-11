from abc import ABC
from dataclasses import dataclass
from typing import Dict, Optional

from faststream.broker.core.publisher import BasePublisher
from faststream.broker.types import MsgType


@dataclass
class ABCPublisher(ABC, BasePublisher[MsgType]):
    """A class representing an ABCPublisher.

    Attributes:
        topic : str
            The topic of the publisher.
        key : Optional[bytes]
            The key of the publisher.
        partition : Optional[int]
            The partition of the publisher.
        timestamp_ms : Optional[int]
            The timestamp in milliseconds of the publisher.
        headers : Optional[Dict[str, str]]
            The headers of the publisher.
        reply_to : Optional[str]
            The reply-to address of the publisher.

    """

    topic: str = ""
    key: Optional[bytes] = None
    partition: Optional[int] = None
    timestamp_ms: Optional[int] = None
    headers: Optional[Dict[str, str]] = None
    reply_to: Optional[str] = ""
