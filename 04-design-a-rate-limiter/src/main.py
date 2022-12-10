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
parser.add_argument("-c", "--config", metavar="", help="config file (.yaml) path")
parser.add_argument(
    "-hn", "--hostname", metavar="", help="hostname for listening", default="0.0.0.0"
)
parser.add_argument(
    "-p", "--port", metavar="", help="port for listening", default="8000"
)
parser.add_argument(
    "-f",
    "--log-format",
    metavar="",
    help="log format",
    default="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(name)s - %(message)s",
)
parser.add_argument(
    "-v", "--verbose", action="store_true", help="print debug logs", default=False
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
        self.is_config_changed = False

        self._config = self._get_config_from_path() if config_path else Config()
        self._is_stop = False
        self._logger = logging.getLogger(self.__class__.__name__)

    def run(self) -> None:
        self._logger.debug("start to run")
        while self.config_path and not self._is_stop:
            self._watch_and_update_config()
            sleep(5)
        self._logger.debug("has been completed")

    def get_config(self) -> Config:
        self.is_config_changed = False
        return self._config

    def stop(self) -> None:
        self._is_stop = True

    def _watch_and_update_config(self) -> None:
        self._logger.debug(f"watch {self.config_path}")
        config = self._get_config_from_path()
        if config.dict() == self._config.dict():
            return
        self._logger.info(f"catch changed {self.config_path}. update config")
        self.is_config_changed = True
        self._config = config

    def _get_config_from_path(self) -> Config:
        with open(self.config_path) as f:
            config_as_dict = yaml.load(f, Loader=yaml.FullLoader)
            return Config(**config_as_dict)


def _register_gracefully_exit_handler() -> None:
    signal.signal(signal.SIGINT, _raise_graceful_exit)
    signal.signal(signal.SIGTERM, _raise_graceful_exit)


def _run_server(
    listen_host: str, listen_port: str, config_manager: ConfigManager
) -> None:
    with socket.socket() as server_socket:
        server_socket.bind((listen_host, int(listen_port)))
        server_socket.listen()
        logger.info(f"start listening on {listen_host}:{listen_port}")
        rate_limit_algo = create_rate_limit_algorithm(config_manager.get_config())
        rate_limit_algo.setup()
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                if config_manager.is_config_changed:
                    rate_limit_algo.teardown()
                    rate_limit_algo = create_rate_limit_algorithm(
                        config_manager.get_config()
                    )
                    rate_limit_algo.setup()
                rate_limit_algo.handle(client_socket, client_address)
            except Exception as e:
                if _is_socket_connected(client_socket):
                    client_socket.close()
                rate_limit_algo.teardown()
                if e.__class__ == GracefulExit:
                    break
                raise e

    logger.info("server socket has been closed")


def create_rate_limit_algorithm(config: Config) -> RateLimitAlgorithm:
    logger.debug(
        f"create a rate limit algorithm of ({config.common.rate_limit_algorithm}) instance"
    )
    if config.common.rate_limit_algorithm == "token bucket":
        return TokenBucketAlgorithm()
    elif config.common.rate_limit_algorithm == "leaky bucket":
        return LeakyBucketAlgorithm(
            periodic_second=config.leaky_bucket.periodic_second,
            n_request_to_be_processed_per_periodic_second=config.leaky_bucket.n_request_to_be_processed_per_periodic_second,
            max_request_queue_size=config.leaky_bucket.max_request_queue_size,
            socket_buf_size=config.common.socket_buf_size,
            forward_host=config.common.forward_host,
            forward_port=config.common.forward_port,
        )
    raise NotImplementedError(
        f"config.common.rate_limit_algorithm must be 'token bucket' or 'leaky bucket'. (current: {args.common.rate_limit_algorithm})"
    )


if __name__ == "__main__":
    _register_gracefully_exit_handler()
    config_manager = ConfigManager(args.config)
    config_manager.start()
    try:
        _run_server(args.hostname, args.port, config_manager)
    finally:
        config_manager.stop()
        logger.info("good bye!")
