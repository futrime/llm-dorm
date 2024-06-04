"""Module for communication."""

import asyncio
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, List, Optional

import zmq


class Comm(ABC):
    """Abstract class for communication."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to communication."""

        raise NotImplementedError

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from communication."""

        raise NotImplementedError

    @abstractmethod
    async def send(self, channel: str, message: str) -> None:
        """Send message to channel."""

        raise NotImplementedError

    @abstractmethod
    async def register_receive_callback(
        self, callback: Callable[[str], None | Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for receiving messages from channel."""

        raise NotImplementedError


class ZmqComm(Comm):
    """Class for ZeroMQ communication."""

    def __init__(
        self,
        broker_host: str,
        broker_backend_port: int,
        broker_frontend_port: int,
        endpoint: str,
    ):
        """Initialize ZeroMQ communication.

        Args:
            broker_address: Address of broker.
            broker_backend_port: Port of broker backend.
            broker_frontend_port: Port of broker frontend.
            endpoint: Endpoint of communication.
        """

        self._broker_host = broker_host
        self._broker_backend_port = broker_backend_port
        self._broker_frontend_port = broker_frontend_port
        self._endpoint = endpoint

        self._publisher = zmq.Context().socket(zmq.PUB)

        self._subscriber = zmq.Context().socket(zmq.SUB)
        self._subscriber.setsockopt_string(zmq.SUBSCRIBE, endpoint)

        self._loop_task_thread: Optional[threading.Thread] = None
        self._loop_task_thread_should_run: bool = True
        self._receive_callback_list: List[
            Callable[[str], None | Coroutine[Any, Any, None]]
        ] = []

    async def connect(self) -> None:
        """Connect to communication."""

        self._publisher.connect(
            f"tcp://{self._broker_host}:{self._broker_backend_port}"
        )
        self._subscriber.connect(
            f"tcp://{self._broker_host}:{self._broker_frontend_port}"
        )

        self._loop_task_thread_should_run = True
        self._loop_task_thread = threading.Thread(target=self._loop_task_func)

    async def disconnect(self) -> None:
        """Disconnect from communication."""

        assert self._loop_task_thread is not None
        self._loop_task_thread_should_run = False
        self._loop_task_thread.join()

        self._publisher.disconnect(
            f"tcp://{self._broker_host}:{self._broker_backend_port}"
        )
        self._subscriber.disconnect(
            f"tcp://{self._broker_host}:{self._broker_frontend_port}"
        )

    async def send(self, channel: str, message: str) -> None:
        """Send message to channel.

        Args:
            channel: Channel to send message to.
            message: Message to send.
        """

        self._publisher.send_string(f"{channel}:{message}")

    async def register_receive_callback(
        self, callback: Callable[[str], None | Coroutine[Any, Any, None]]
    ) -> None:
        """Register callback for receiving messages from channel.

        Args:
            callback: Callback to call when message is received.
        """

        self._receive_callback_list.append(callback)

    async def _loop_task_func(self) -> None:
        while self._loop_task_thread_should_run:
            message = self._subscriber.recv_string()
            channel, message = message.split(":", 1)
            assert channel == self._endpoint

            for callback in self._receive_callback_list:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
