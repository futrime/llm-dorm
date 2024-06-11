import threading
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

import zmq


class Comm(ABC):
    @abstractmethod
    def connect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send(self, channel: str, message: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def register_receive_callback(self, callback: Callable[[str], None]) -> None:
        raise NotImplementedError


class ZmqComm(Comm):
    def __init__(
        self, broker_host: str, broker_backend_port: int, broker_frontend_port: int
    ):
        self._broker_host = broker_host
        self._broker_backend_port = broker_backend_port
        self._broker_frontend_port = broker_frontend_port

        self._publisher = zmq.Context().socket(zmq.PUB)

        self._subscriber = zmq.Context().socket(zmq.SUB)
        self._subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

        self._loop_task_thread: Optional[threading.Thread] = None
        self._loop_task_thread_should_run: bool = True
        self._receive_callbacks: Dict[str, Callable[[str], None]] = {}

    def connect(self) -> None:
        self._publisher.connect(
            f"tcp://{self._broker_host}:{self._broker_backend_port}"
        )
        self._subscriber.connect(
            f"tcp://{self._broker_host}:{self._broker_frontend_port}"
        )

        self._loop_task_thread_should_run = True
        self._loop_task_thread = threading.Thread(target=self._loop_task_func)

    def disconnect(self) -> None:
        assert self._loop_task_thread is not None
        self._loop_task_thread_should_run = False
        self._loop_task_thread.join()

        self._publisher.disconnect(
            f"tcp://{self._broker_host}:{self._broker_backend_port}"
        )
        self._subscriber.disconnect(
            f"tcp://{self._broker_host}:{self._broker_frontend_port}"
        )

    def send(self, channel: str, message: str) -> None:
        self._publisher.send_string(f"{channel}:{message}")

    def register_receive_callback(
        self, channel: str, callback: Callable[[str], None]
    ) -> None:
        self._receive_callbacks[channel] = callback

    def _loop_task_func(self) -> None:
        while self._loop_task_thread_should_run:
            message = self._subscriber.recv_string()
            channel, message = message.split(":", 1)

            for callback_channel, callback in self._receive_callbacks.items():
                if channel == callback_channel:
                    callback(message)
