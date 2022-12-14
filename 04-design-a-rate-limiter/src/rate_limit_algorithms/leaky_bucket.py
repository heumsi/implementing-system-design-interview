import logging
import queue
import socket
import threading
import time
from typing import Dict, Tuple

from src.core import Request
from src.rate_limit_algorithms import RateLimitAlgorithm


class _RequestProcessor(threading.Thread):
    def __init__(
        self,
        client_ip: str,
        periodic_second: int,
        n_request_to_be_processed_per_periodic_second: int,
        request_queue: queue.Queue,
        socket_buf_size: int,
        forward_host: str,
        forward_port: str,
    ) -> None:
        super().__init__()
        self.has_been_started = False
        self.is_stop = False

        self._client_ip = client_ip
        self._periodic_second = periodic_second
        self._n_request_to_be_processed_per_periodic_second = (
            n_request_to_be_processed_per_periodic_second
        )
        self._request_queue = request_queue
        self._socket_buf_size = socket_buf_size
        self._forward_host = forward_host
        self._forward_port = forward_port
        self._last_ts = int(time.time())
        self._idle_threshold_second = 60
        self._logger = logging.getLogger(
            f"{self.__class__.__name__} ({self._client_ip})"
        )

    @property
    def current_n_requests(self) -> int:
        return self._request_queue.qsize()

    def run(self) -> None:
        self.has_been_started = True
        while not self.is_stop:
            count = min(
                self._n_request_to_be_processed_per_periodic_second,
                self._request_queue.qsize(),
            )
            if count == 0:
                current_ts = int(time.time())
                if current_ts - self._last_ts >= self._idle_threshold_second:
                    self._logger.debug(
                        f"queue is empty during {current_ts - self._last_ts}s. stop the loop"
                    )
                    self.is_stop = True
            else:
                self._logger.info(
                    f"process requests in queue. current [# of requests / queue size] in queue is [{count}/{self._request_queue.maxsize}]"
                )
                for i in range(1, count + 1):
                    request: Request = self._request_queue.get_nowait()
                    self._logger.info(
                        f"process request of {request.client_address} in queue [{i}/{count}]"
                    )
                    self._forward_request(request)
                self._last_ts = int(time.time())
            time.sleep(self._periodic_second)
        self._logger.debug("will be terminated.")

    def stop(self) -> None:
        self.is_stop = True

    def _forward_request(self, request: Request) -> None:
        try:
            with socket.socket() as forward_socket:
                data = request.client_socket.recv(self._socket_buf_size)
                self._logger.debug(
                    f"start to connect forward server {self._forward_host}:{self._forward_port}"
                )
                forward_socket.connect((self._forward_host, self._forward_port))
                self._logger.debug(
                    f"send data to forward server {self._forward_host}:{self._forward_port}"
                )
                forward_socket.send(data)
                data = forward_socket.recv(self._socket_buf_size)
                decoded_data = data.decode()
                self._logger.debug(
                    f"got data from forward server {self._forward_host}:{self._forward_port}"
                )
            decoded_data_blocks = decoded_data.split("\r\n\r\n")
            decoded_data_blocks[0] = (
                decoded_data_blocks[0]
                + "\r\n"
                + "\r\n".join(
                    f"{k}: {v}"
                    for k, v in {
                        "X-Ratelimit-Remaining": self._request_queue.maxsize
                        - self._request_queue.qsize(),
                        "X-Ratelimit-Limit": self._request_queue.maxsize,
                        "X-Ratelimit-Retry-After": self._periodic_second,
                    }.items()
                )
            )
            decoded_data = "\r\n\r\n".join(decoded_data_blocks)
            data = decoded_data.encode("utf-8")
            self._logger.debug(f"send data to client {request.client_address}")
            request.client_socket.send(data)
        except ConnectionRefusedError:
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
                            "X-Ratelimit-Remaining": 0,
                            "X-Ratelimit-Limit": self._request_queue.qsize(),
                            "X-Ratelimit-Retry-After": self._periodic_second,
                        }.items()
                    ),
                ]
            )
            data = "\n\n".join([header, content])
            self._logger.debug(
                f"send failure response to client {request.client_address}"
            )
            request.client_socket.send(data.encode("utf-8"))
        finally:
            request.client_socket.close()


class LeakyBucketAlgorithm(RateLimitAlgorithm):
    def __init__(
        self,
        periodic_second: int,
        n_request_to_be_processed_per_periodic_second: int,
        request_queue_size: int,
        socket_buf_size: int,
        forward_host: str,
        forward_port: str,
    ) -> None:
        self._periodic_second = periodic_second
        self._n_request_to_be_processed_per_periodic_second = (
            n_request_to_be_processed_per_periodic_second
        )
        self._request_queue_size = request_queue_size
        self._socket_buf_size = socket_buf_size
        self._forward_host = forward_host
        self._forward_port = forward_port
        self._client_ip_to_request_processor_and_request_queue: Dict[
            str, Tuple[_RequestProcessor, queue.Queue]
        ] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def setup(self) -> None:
        pass

    def teardown(self) -> None:
        for i, (client_ip, (request_processor, request_queue)) in enumerate(
            self._client_ip_to_request_processor_and_request_queue.items(), 1
        ):
            self._logger.debug(
                f"wait for _RequestProcessor and Queue of {client_ip} to be terminated [{i}/{len(self._client_ip_to_request_processor_and_request_queue)}]"
            )
            request_processor.stop()
            request_processor.join()
            del request_queue

    def handle(self, request: Request) -> None:
        self._logger.debug(f"handle request of {request.client_address}")
        request_processor_and_request_queue = (
            self._client_ip_to_request_processor_and_request_queue.get(
                request.client_ip, None
            )
        )
        if not request_processor_and_request_queue:
            self._logger.debug(
                f"_RequestProcessor for {request.client_ip} has not been created yet. create thread"
            )
            request_queue = queue.Queue(self._request_queue_size)
            request_processor = _RequestProcessor(
                client_ip=request.client_ip,
                periodic_second=self._periodic_second,
                n_request_to_be_processed_per_periodic_second=self._n_request_to_be_processed_per_periodic_second,
                request_queue=request_queue,
                socket_buf_size=self._socket_buf_size,
                forward_host=self._forward_host,
                forward_port=self._forward_port,
            )
            self._client_ip_to_request_processor_and_request_queue[
                request.client_ip
            ] = (request_processor, request_queue)
        else:
            request_processor, request_queue = request_processor_and_request_queue
        if not request_processor.has_been_started:
            self._logger.debug(
                f"_RequestProcessor for {request.client_ip} has not been started yet. start the thread"
            )
            request_processor.start()
        if request_processor.is_stop:
            self._logger.debug(
                f"_RequestProcessor for {request.client_ip} has been stop. create and start new thread"
            )
            request_processor = _RequestProcessor(
                client_ip=request.client_ip,
                periodic_second=self._periodic_second,
                n_request_to_be_processed_per_periodic_second=self._n_request_to_be_processed_per_periodic_second,
                request_queue=request_queue,
                socket_buf_size=self._socket_buf_size,
                forward_host=self._forward_host,
                forward_port=self._forward_port,
            )
            request_queue = queue.Queue(self._request_queue_size)
            self._client_ip_to_request_processor_and_request_queue[
                request.client_ip
            ] = (request_processor, request_queue)
            request_processor.start()
        try:
            request_queue.put_nowait(request)
            self._logger.info(
                f"request from {request.client_address} has been added to queue. current [# of requests / queue_size] in queue is [{request_queue.qsize()}/{request_queue.maxsize}]"
            )
        except queue.Full:
            self._logger.info(
                f"reqeust queue is full. request from {request.client_address} has not been added to queue"
            )
            self._respond_with_failure(request, request_processor.current_n_requests)

    def _respond_with_failure(self, request: Request, request_queue_size: int) -> None:
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
                            "X-Ratelimit-Remaining": self._request_queue_size
                            - request_queue_size,
                            "X-Ratelimit-Limit": self._request_queue_size,
                            "X-Ratelimit-Retry-After": self._periodic_second,
                        }.items()
                    ),
                ]
            )
            data = "\n\n".join([header, content])
            self._logger.info(
                f"send failure response to client {request.client_address}"
            )
            request.client_socket.send(data.encode("utf-8"))
        finally:
            request.client_socket.close()
