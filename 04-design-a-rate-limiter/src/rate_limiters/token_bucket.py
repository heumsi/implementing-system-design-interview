import logging
import socket
import time
from typing import Dict

from src.core import Request
from src.rate_limiters import RateLimitAlgorithm


class BucketIsEmpty(Exception):
    pass


class TokenBucket:
    def __init__(
        self,
        client_ip: str,
        periodic_second: int,
        n_tokens_to_be_added_per_periodic_second: int,
        token_bucket_size: int,
    ) -> None:
        self.current_n_tokens = token_bucket_size

        self._client_ip = client_ip
        self._periodic_second = periodic_second
        self._n_tokens_to_be_added_per_periodic_second = (
            n_tokens_to_be_added_per_periodic_second
        )
        self._token_bucket_size = token_bucket_size
        self._last_ts = None
        self._logger = logging.getLogger(
            f"{self.__class__.__name__} ({self._client_ip})"
        )

    def get_token(self) -> None:
        if self._last_ts:
            current_ts = int(time.time())
            n_tokens_to_be_added = self._n_tokens_to_be_added_per_periodic_second * (
                (current_ts - self._last_ts) // self._periodic_second
            )
            self.current_n_tokens = min(
                self.current_n_tokens + n_tokens_to_be_added, self._token_bucket_size
            )
            self._logger.debug(
                f"{n_tokens_to_be_added} tokens has been added. current # of tokens is {self.current_n_tokens}"
            )
        if self.current_n_tokens <= 0:
            raise BucketIsEmpty()
        self.current_n_tokens -= 1
        self._last_ts = int(time.time())


class TokenBucketAlgorithm(RateLimitAlgorithm):
    def __init__(
        self,
        periodic_second: int,
        n_tokens_to_be_added_per_periodic_second: int,
        token_bucket_size: int,
        socket_buf_size: int,
        forward_host: str,
        forward_port: str,
    ) -> None:
        self._periodic_second = periodic_second
        self._n_tokens_to_be_added_per_periodic_second = (
            n_tokens_to_be_added_per_periodic_second
        )
        self._token_bucket_size = token_bucket_size
        self._socket_buf_size = socket_buf_size
        self._forward_host = forward_host
        self._forward_port = forward_port
        self._logger = logging.getLogger(self.__class__.__name__)
        self._client_ip_to_token_bucket: Dict[str, TokenBucket] = {}

    def setup(self) -> None:
        pass

    def handle(self, request: Request) -> None:
        self._logger.debug(f"handle request of {request.client_address}")
        token_bucket = self._client_ip_to_token_bucket.get(request.client_ip, None)
        if not token_bucket:
            self._logger.debug(
                f"token bucket of {request.client_ip} has not been created yet. create token bucket"
            )
            token_bucket = TokenBucket(
                client_ip=request.client_ip,
                periodic_second=self._periodic_second,
                n_tokens_to_be_added_per_periodic_second=self._n_tokens_to_be_added_per_periodic_second,
                token_bucket_size=self._token_bucket_size,
            )
            self._client_ip_to_token_bucket[request.client_ip] = token_bucket
        try:
            token_bucket.get_token()
            self._logger.info(
                f"get token successfully. current [# of tokens / bucket size] is [{token_bucket.current_n_tokens}/{self._token_bucket_size}]"
            )
            self._forward_request(request, token_bucket)
        except BucketIsEmpty:
            self._logger.info(
                f"token bucket is emtpy. can not forward request from {request.client_address}"
            )
            self._respond_with_failure(request)

    def _forward_request(self, request: Request, token_bucket: TokenBucket) -> None:
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
                        "X-Ratelimit-Remaining": token_bucket.current_n_tokens,
                        "X-Ratelimit-Limit": self._token_bucket_size,
                        "X-Ratelimit-Retry-After": self._periodic_second,
                    }.items()
                )
            )
            decoded_data = "\r\n\r\n".join(decoded_data_blocks)
            data = decoded_data.encode("utf-8")
            self._logger.debug(f"send data to client {request.client_address}")
            request.client_socket.send(data)
        except ConnectionRefusedError as e:
            content = f"Connection was refused. Make sure the forward server is running on {self._forward_host}:{self._forward_port}"
            header = "\n".join(
                [
                    "HTTP/1.1 503 Service Unavailable",
                    "\r\n".join(
                        f"{k}: {v}"
                        for k, v in {
                            "Content-Type": "text/plan; encoding=utf8",
                            "Content-Length": len(content),
                            "Connection": "close",
                        }.items()
                    ),
                ]
            )
            data = "\n\n".join([header, content])
            self._logger.error(
                f"send failure response to client {request.client_address}"
            )
            request.client_socket.send(data.encode("utf-8"))
        finally:
            request.client_socket.close()

    def _respond_with_failure(self, request: Request) -> None:
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
                            "X-Ratelimit-Remaining": 0,
                            "X-Ratelimit-Limit": self._token_bucket_size,
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

    def teardown(self) -> None:
        pass
