import argparse
import logging
import signal
import socket
import threading
from time import sleep
from typing import Optional

import yaml

from src.config import Config
from src.rate_limiters import RateLimiterAlgorithm
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
    help=" : algorithm for rate limiter. you can choose one among 'token bucket', 'leak_bucket'",
    default="leaky bucket",
)
parser.add_argument(
    "-f",
    "--log-format",
    help=" : log format",
    default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
parser.add_argument("-v", "--verbose", help=" : for verbose log", default=False)
args = parser.parse_args()

setup_logger(args.log_format, args.verbose)
logger = logging.getLogger()


def _graceful_exit_handler(*args):
    global graceful_exit
    graceful_exit = True
    # raise GracefulExit()


def _is_socket_connected(s: socket.socket) -> bool:
    return s.fileno() != -1


graceful_exit = False


class ConfigManager(threading.Thread):
    def __init__(self, config_path: Optional[str]) -> None:
        super().__init__()
        self.config_path = config_path
        self._config = Config()

    def run(self) -> None:
        while self.config_path and not graceful_exit:
            self._config = self._get_config_from_path()
            sleep(1)

    def get_config(self) -> Config:
        return self._config

    def _get_config_from_path(self) -> Config:
        with open(self.config_path) as f:
            config_as_dict = yaml.load(f, Loader=yaml.FullLoader)
            config = Config(**config_as_dict)
            return config


def _register_gracefully_exit_handler() -> None:
    signal.signal(signal.SIGINT, _graceful_exit_handler)
    signal.signal(signal.SIGTERM, _graceful_exit_handler)


def _run_server(
    listen_host: str, listen_port: int, rate_limiter_algo: RateLimiterAlgorithm
) -> None:
    with socket.socket() as server_socket:
        server_socket.bind((listen_host, listen_port))
        server_socket.listen()
        logger.info(f"start listening on {listen_host}:{listen_port}")
        while not graceful_exit:
            try:
                client_socket, client_address = server_socket.accept()
                rate_limiter_algo.handle(client_socket, client_address)
            except Exception as e:
                raise e
            finally:
                client_socket.close()


if __name__ == "__main__":
    _register_gracefully_exit_handler()
    config_manager = ConfigManager(args.config)
    try:
        config_manager.start()
        config = config_manager.get_config()
        if args.algorithm == "token bucket":
            algorithm = TokenBucketAlgorithm()
        elif args.algorithm == "leaky bucket":
            algorithm = LeakyBucketAlgorithm(**config.leaky_bucket.dict())
        else:
            raise NotImplemented()
        _run_server(args.hostname, int(args.port), algorithm)
    except Exception as e:
        raise e
    finally:
        config_manager.join()
