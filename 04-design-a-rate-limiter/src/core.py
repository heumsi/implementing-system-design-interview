import abc
import socket
from dataclasses import dataclass


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass
class Request:
    client_socket: socket.socket
    client_ip: str
    client_port: str

    @property
    def client_address(self) -> str:
        return f"{self.client_ip}:{self.client_port}"


class RateLimitAlgorithm(abc.ABC):
    @abc.abstractmethod
    def setup(self) -> None:
        pass

    @abc.abstractmethod
    def handle(self, request: Request) -> None:
        pass

    @abc.abstractmethod
    def teardown(self) -> None:
        pass


class GracefulExit(Exception):
    pass
