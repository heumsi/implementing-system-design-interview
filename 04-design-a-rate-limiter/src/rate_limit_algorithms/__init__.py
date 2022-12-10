import abc

from src.core import Request


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
