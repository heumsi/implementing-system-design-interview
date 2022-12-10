import argparse
import logging
import signal
import socket
import threading
from time import sleep
from typing import Optional

import yaml

from src.config import Config
from src.rate_limiters import RateLimitAlgorithm
from src.rate_limiters.leaky_bucket import LeakyBucketAlgorithm
from src.rate_limiters.token_bucket import TokenBucketAlgorithm
from src.util import setup_logger

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help=" : config file path")
parser.add_argument(
    "-hn", "--hostname", help=" : hostname for listening", default="0.0.0.0"
)
parser.add_argument("-p", "--port", help=" : host for listening", default="8000")
parser.add_argument(
    "-a",
    "--algorithm",
    help=" : algorithm for rate limit. you can choose one among 'token bucket', 'leak bucket'",
    default="leaky bucket",
)
parser.add_argument(
    "-f",
    "--log-format",
    help=" : log format",
    default="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s - %(message)s",
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help=" : for verbose log", default=False
)
args = parser.parse_args()

setup_logger(args.log_format, args.verbose)
logger = logging.getLogger()


class GracefulExit(Exception):
    pass


def _raise_graceful_exit(*args):
    logger.debug("got shutdown signal")
    raise GracefulExit()


def _is_socket_connected(s: socket.socket) -> bool:
    return s.fileno() != -1


class ConfigManager(threading.Thread):
    def __init__(self, config_path: Optional[str]) -> None:
        super().__init__()
        self.config_path = config_path

        self._config = self._get_config_from_path() if config_path else Config()
        self._is_stop = False
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        self._logger.debug("start to run")
        while self.config_path and not self._is_stop:
            self._config = self._get_config_from_path()
            sleep(1)
        self._logger.debug("has been completed")

    def get_config(self) -> Config:
        return self._config

    def stop(self) -> None:
        self._is_stop = True

    def _get_config_from_path(self) -> Config:
        self._logger.debug(f"get config from {self.config_path}")
        with open(self.config_path) as f:
            config_as_dict = yaml.load(f, Loader=yaml.FullLoader)
            config = Config(**config_as_dict)
            return config


def _register_gracefully_exit_handler() -> None:
    signal.signal(signal.SIGINT, _raise_graceful_exit)
    signal.signal(signal.SIGTERM, _raise_graceful_exit)


def _run_server(
    listen_host: str, listen_port: int, rate_limit_algo: RateLimitAlgorithm
) -> None:
    with socket.socket() as server_socket:
        server_socket.bind((listen_host, listen_port))
        server_socket.listen()
        logger.info(f"start listening on {listen_host}:{listen_port}")
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                rate_limit_algo.handle(client_socket, client_address)
            except GracefulExit:
                if _is_socket_connected(client_socket):
                    client_socket.close()
                break
    logger.info("server socket has been closed")


if __name__ == "__main__":
    _register_gracefully_exit_handler()
    config_manager = ConfigManager(args.config)
    config_manager.start()
    try:
        config = config_manager.get_config()
        logger.info(config)
        if args.algorithm == "token bucket":
            rate_limit_algo = TokenBucketAlgorithm()
        elif args.algorithm == "leaky bucket":
            rate_limit_algo = LeakyBucketAlgorithm(
                periodic_second=config.leaky_bucket.periodic_second,
                n_request_to_be_processed_per_periodic_second=config.leaky_bucket.n_request_to_be_processed_per_periodic_second,
                max_request_queue_size=config.leaky_bucket.max_request_queue_size,
                socket_buf_size=config.common.socket_buf_size,
                forward_host=config.common.forward_host,
                forward_port=config.common.forward_port,
            )
        else:
            raise NotImplemented()
        rate_limit_algo.setup()
        _run_server(args.hostname, int(args.port), rate_limit_algo)
        rate_limit_algo.teardown()
    finally:
        config_manager.stop()
        logger.info("good bye!")
