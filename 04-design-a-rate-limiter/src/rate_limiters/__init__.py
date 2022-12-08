import abc
import socket
from typing import Tuple


class RateLimitAlgorithm(abc.ABC):
    @abc.abstractmethod
    def handle(
        self, client_socket: socket.socket, client_address: Tuple[str, str]
    ) -> None:
        pass
