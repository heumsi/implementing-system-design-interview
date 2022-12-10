import logging
import socket

from src.config import Config
from src.config_manager import ConfigManager
from src.core import GracefulExit, Request
from src.rate_limiters import RateLimitAlgorithm
from src.rate_limiters.leaky_bucket import LeakyBucketAlgorithm
from src.rate_limiters.token_bucket import TokenBucketAlgorithm


class Server:
    def __init__(
        self, listen_host: str, listen_port: str, config_manager: ConfigManager
    ) -> None:
        self._listen_host = listen_host
        self._listen_port = listen_port
        self._config_manager = config_manager
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def listen_address(self):
        return f"{self._listen_host}:{self._listen_port}"

    def run(self) -> None:
        with socket.socket() as server_socket:
            server_socket.bind((self._listen_host, int(self._listen_port)))
            server_socket.listen()
            self._logger.info(f"start listening on {self.listen_address}")
            rate_limit_algo = self._create_rate_limit_algorithm(
                self._config_manager.get_config()
            )
            rate_limit_algo.setup()
            while True:
                try:
                    client_socket, client_address = server_socket.accept()
                    if self._config_manager.is_config_changed:
                        rate_limit_algo.teardown()
                        rate_limit_algo = self._create_rate_limit_algorithm(
                            self._config_manager.get_config()
                        )
                        rate_limit_algo.setup()
                    client_ip, client_port = client_address
                    request = Request(
                        client_socket=client_socket,
                        client_ip=client_ip,
                        client_port=client_port,
                    )
                    rate_limit_algo.handle(request)
                except Exception as e:
                    if self._is_socket_connected(client_socket):
                        client_socket.close()
                    rate_limit_algo.teardown()
                    if e.__class__ == GracefulExit:
                        break
                    raise e
        self._logger.info("server socket has been closed")

    def _create_rate_limit_algorithm(self, config: Config) -> RateLimitAlgorithm:
        self._logger.debug(
            f"create a rate limit algorithm of ({config.rate_limit_algorithm}) instance"
        )
        if config.rate_limit_algorithm == "token bucket":
            return TokenBucketAlgorithm(
                periodic_second=config.token_bucket.periodic_second,
                n_tokens_to_be_added_per_periodic_second=config.token_bucket.n_tokens_to_be_added_per_periodic_second,
                token_bucket_size=config.token_bucket.token_bucket_size,
                socket_buf_size=config.common.socket_buf_size,
                forward_host=config.common.forward_host,
                forward_port=config.common.forward_port,
            )
        elif config.rate_limit_algorithm == "leaky bucket":
            return LeakyBucketAlgorithm(
                periodic_second=config.leaky_bucket.periodic_second,
                n_request_to_be_processed_per_periodic_second=config.leaky_bucket.n_request_to_be_processed_per_periodic_second,
                request_queue_size=config.leaky_bucket.request_queue_size,
                socket_buf_size=config.common.socket_buf_size,
                forward_host=config.common.forward_host,
                forward_port=config.common.forward_port,
            )
        raise NotImplementedError(
            f"config.rate_limit_algorithm must be 'token bucket' or 'leaky bucket'. (current: {config.rate_limit_algorithm})"
        )

    def _is_socket_connected(self, s: socket.socket) -> bool:
        return s.fileno() != -1
