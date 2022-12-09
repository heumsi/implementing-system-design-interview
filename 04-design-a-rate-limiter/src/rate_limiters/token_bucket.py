import socket
from typing import Tuple

from src.rate_limiters import RateLimitAlgorithm


class TokenBucketAlgorithm(RateLimitAlgorithm):
    def setup(self) -> None:
        pass

    def handle(
        self, client_socket: socket.socket, client_address: Tuple[str, str]
    ) -> None:
        pass

    def teardown(self) -> None:
        pass
