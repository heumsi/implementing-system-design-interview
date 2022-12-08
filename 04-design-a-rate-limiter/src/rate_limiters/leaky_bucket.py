import logging
import queue
import socket
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Tuple

from src.rate_limiters import RateLimitAlgorithm

logger = logging.getLogger()


@dataclass
class _Request:
    client_socket: socket.socket
    client_ip: str
    client_port: str

    @property
    def client_address(self) -> str:
        return f"{self.client_address[0]}:{self.client_port}"


class _RequestProcessor(threading.Thread):
    class RequestQueueIsFull(Exception):
        pass

    def __init__(
        self,
        periodic_second: int,
        n_request_to_be_processed_per_periodic_second: int,
        max_request_queue_size: int,
        socket_buf_size: int,
        forward_host: str,
        forward_port: str,
    ) -> None:
        super().__init__()
        self.is_running = False
        self.is_stop = False

        self._periodic_second = periodic_second
        self._n_request_to_be_processed_per_periodic_second = (
            n_request_to_be_processed_per_periodic_second
        )
        self._max_request_queue_size = max_request_queue_size
        self._socket_buf_size = socket_buf_size
        self._forward_host = forward_host
        self._forward_port = forward_port
        self._empty_count = 0
        self._empty_count_threshold_for_stop = 10
        self._request_queue = queue.Queue(self._max_request_queue_size)

    @property
    def request_queue_size(self) -> int:
        return self._request_queue.queue

    def run(self) -> None:
        self.is_running = True
        while not self.is_stop:
            try:
                count = min(
                    self._n_request_to_be_processed_per_periodic_second,
                    self._request_queue.qsize(),
                )
                while count > 0:
                    request: _Request = self._request_queue.get_nowait()
                    self._forward_request(request)
                    count -= 1
            except queue.Empty:
                self._empty_count += 1
                if self._empty_count >= self._empty_count_threshold_for_stop:
                    self.is_stop = True
            time.sleep(self._periodic_second)

    def add_request(self, request: _Request) -> None:
        try:
            self._request_queue.put_nowait(request)
        except queue.Full:
            raise self.RequestQueueIsFull()

    def stop(self) -> None:
        self.is_stop = True

    def _forward_request(self, request: _Request) -> None:
        try:
            with socket.socket() as forward_socket:
                data = request.client_socket.recv(self._socket_buf_size)
                # decoded_data = data.decode()
                # logger.debug(
                #     f"got data from client {client_address[0]}:{client_address[1]}: {decoded_data}"
                # )
                # logger.debug(
                #     f"start to connect forward server {config.forward_host}:{config.forward_port}"
                # )
                forward_socket.connect((self._forward_host, self._forward_port))
                # logger.debug(
                #     f"send data to forward server {config.forward_host}:{config.forward_port}"
                # )
                forward_socket.send(data)
                data = forward_socket.recv(self._socket_buf_size)
                decoded_data = data.decode()
                # logger.debug(
                #     f"got data from forward server {config.forward_host}:{config.forward_port}: {decoded_data}"
                # )
            decoded_data_blocks = decoded_data.split("\r\n\r\n")
            decoded_data_blocks[0] = (
                decoded_data_blocks[0]
                + "\r\n"
                + "\r\n".join(
                    f"{k}: {v}"
                    for k, v in {
                        "X-Ratelimit-Remaining": self._max_request_queue_size
                        - self._request_queue.qsize(),
                        "X-Ratelimit-Limit": self._max_request_queue_size,
                        "X-Ratelimit-Retry-After": self._periodic_second,
                    }.items()
                )
            )
            decoded_data = "\r\n\r\n".join(decoded_data_blocks)
            data = decoded_data.encode("utf-8")
            # logger.debug(f"send data to client {client_address[0]}:{client_address[1]}")
            request.client_socket.send(data)
        except ConnectionRefusedError as e:
            content = f"Connection was refused. Make sure the forward server is running on {self._forward_host}:{self._forward_port}"
            header = "\n".join(
                [
                    "HTTP/1.1 429 Too many requests",
                    "\r\n".join(
                        f"{k}: {v}"
                        for k, v in {
                            "Content-Type": "text/plan; encoding=utf8",
                            "Content-Length": len(content),
                            "Connection": "close",
                            "X-Ratelimit-Remaining": self._max_request_queue_size
                                                     - request_queue_size,
                            "X-Ratelimit-Limit": self._max_request_queue_size,
                            "X-Ratelimit-Retry-After": self._periodic_second,
                        }.items()
                    ),
                ]
            )
            data = "\n\n".join([header, content])
            logger.debug(f"send failure response to client {request.client_address}")
            request.client_socket.send(data.encode("utf-8"))
        finally:
            request.client_socket.close()


class LeakyBucketAlgorithm(RateLimitAlgorithm):
    def __init__(
        self,
        periodic_second: int,
        n_request_to_be_processed_per_periodic_second: int,
        max_request_queue_size: int,
        socket_buf_size: int,
        forward_host: str,
        forward_port: str,
    ) -> None:
        self._periodic_second = periodic_second
        self._n_request_to_be_processed_per_periodic_second = (
            n_request_to_be_processed_per_periodic_second
        )
        self._max_request_queue_size = max_request_queue_size
        self._socket_buf_size = socket_buf_size
        self._forward_host = forward_host
        self._forward_port = forward_port

        self._client_ip_to_request_processor: Dict[
            str, _RequestProcessor
        ] = defaultdict(
            lambda: _RequestProcessor(
                periodic_second=self._periodic_second,
                n_request_to_be_processed_per_periodic_second=self._n_request_to_be_processed_per_periodic_second,
                max_request_queue_size=self._max_request_queue_size,
                socket_buf_size=self._socket_buf_size,
                forward_host=self._forward_host,
                forward_port=self._forward_port,
            )
        )

    def __del__(self) -> None:
        for (
            client_ip,
            request_processor,
        ) in self._client_ip_to_request_processor.items():
            request_processor.stop()
            request_processor.join()

    def handle(
        self, client_socket: socket.socket, client_address: Tuple[str, str]
    ) -> None:
        client_ip, client_port = client_address
        request = _Request(
            client_socket=client_socket, client_ip=client_ip, client_port=client_port
        )
        request_processor = self._client_ip_to_request_processor[client_ip]
        if not request_processor.is_running:
            request_processor.start()
        if request_processor.is_stop:
            request_processor = _RequestProcessor(
                periodic_second=self._periodic_second,
                n_request_to_be_processed_per_periodic_second=self._n_request_to_be_processed_per_periodic_second,
                max_request_queue_size=self._max_request_queue_size,
                socket_buf_size=self._socket_buf_size,
                forward_host=self._forward_host,
                forward_port=self._forward_port,
            )
            self._client_ip_to_request_processor[client_ip] = request_processor
            request_processor.start()
        try:
            request_processor.add_request(request)
        except _RequestProcessor.RequestQueueIsFull:
            self._respond_with_failure(request, request_processor.request_queue_size)

    def _respond_with_failure(self, request: _Request, request_queue_size: int) -> None:
        try:
            content = "Please retry after minutes"
            header = "\n".join(
                [
                    "HTTP/1.1 429 Too many requests",
                    "\r\n".join(
                        f"{k}: {v}"
                        for k, v in {
                            "Content-Type": "text/plan; encoding=utf8",
                            "Content-Length": len(content),
                            "Connection": "close",
                            "X-Ratelimit-Remaining": self._max_request_queue_size
                            - request_queue_size,
                            "X-Ratelimit-Limit": self._max_request_queue_size,
                            "X-Ratelimit-Retry-After": self._periodic_second,
                        }.items()
                    ),
                ]
            )
            data = "\n\n".join([header, content])
            logger.debug(f"send failure response to client {request.client_address}")
            request.client_socket.send(data.encode("utf-8"))
        finally:
            request.client_socket.close()
