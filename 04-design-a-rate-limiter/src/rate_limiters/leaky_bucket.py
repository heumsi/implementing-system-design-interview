import socket
from typing import Tuple

from src.rate_limiters import RateLimiterAlgorithm


class LeakyBucketAlgorithm(RateLimiterAlgorithm):
    def __init__(
        self,
        periodic_second: int,
        n_request_to_be_processed_per_periodic_second: int,
        max_request_queue_size: int
    ) -> None:
        self.periodic_second = periodic_second
        self.n_request_to_be_processed_per_periodic_second = n_request_to_be_processed_per_periodic_second
        self.max_request_queue_size = max_request_queue_size

    def handle(self, client_socket: socket.socket, client_address: Tuple[str, str]) -> None:
        pass