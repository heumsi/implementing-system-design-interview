import argparse
import logging
import signal
import socket
import threading
from dataclasses import dataclass
from time import sleep
from typing import Dict, List, Tuple

import yaml

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", help=" : config file path")
args = parser.parse_args()


@dataclass
class Config:
    listen_host: str = "0.0.0.0"
    listen_port: int = 8000
    forward_host: str = "127.0.0.1"
    forward_port: int = 8080
    buf_size: int = 1024
    log_level: str = "DEBUG"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    periodic_second: int = 1
    max_requests_per_periodic_second: int = 2

    @classmethod
    def from_dict(cls, config_as_dict: Dict[str, str]):
        return cls(**config_as_dict)


def get_config() -> Tuple[Config, bool]:
    if args.config:
        with open(args.config) as f:
            config_as_dict = yaml.load(f, Loader=yaml.FullLoader)
            config = Config.from_dict(config_as_dict)
            return config, False
    return Config(), True


def set_config_periodically():
    logger.debug("start to set config periodically...")
    while not graceful_exit:
        global config
        config, _ = get_config()
        logger.debug(f"got config from {args.config}")
        sleep(1)


def get_logger() -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(config.log_level)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(config.log_format))
    logger.addHandler(stream_handler)
    return logger


def process(client_socket, client_address):
    try:
        with socket.socket() as forward_socket:
            data = client_socket.recv(config.buf_size)
            decoded_data = data.decode()
            logger.debug(
                f"got data from client {client_address[0]}:{client_address[1]}: {decoded_data}"
            )
            logger.debug(
                f"start to connect forward server {config.forward_host}:{config.forward_port}"
            )
            forward_socket.connect((config.forward_host, config.forward_port))
            logger.debug(
                f"send data to forward server {config.forward_host}:{config.forward_port}"
            )
            forward_socket.send(data)
            data = forward_socket.recv(config.buf_size)
            decoded_data = data.decode()
            logger.debug(
                f"got data from forward server {config.forward_host}:{config.forward_port}: {decoded_data}"
            )
        logger.debug(f"send data to client {client_address[0]}{client_address[1]}")
        sleep(10)
        client_socket.send(data)

    finally:
        client_socket.close()
        thread_id = threading.get_native_id()
        process_threads.pop(thread_id)


def set_available():
    while not graceful_exit:
        global available
        available = config.max_requests_per_periodic_second
        sleep(config.periodic_second)


class GracefulExit(Exception):
    pass


def raise_gracefully(*args):
    # raise GracefulExit
    global graceful_exit
    graceful_exit = True
    raise GracefulExit


config, is_default_config = get_config()
logger = get_logger()
if is_default_config:
    logger.debug(f"config argument is not proivded. default config will be used")
else:
    logger.debug(f"got config from {args.config}")
# this will be reset periodically in set_available()
available = config.max_requests_per_periodic_second
graceful_exit = False
core_threads: List[threading.Thread] = []
process_threads: Dict[int, threading.Thread] = {}


if __name__ == "__main__":
    signal.signal(signal.SIGINT, raise_gracefully)
    signal.signal(signal.SIGTERM, raise_gracefully)

    if not is_default_config:
        set_config_periodically_thread = threading.Thread(
            target=set_config_periodically
        )
        set_config_periodically_thread.start()
        core_threads.append(set_config_periodically_thread)
    with socket.socket() as server_socket:
        set_available_thread = threading.Thread(target=set_available)
        set_available_thread.start()
        core_threads.append(set_available_thread)

        server_socket.bind((config.listen_host, config.listen_port))
        server_socket.listen()
        logger.info(f"start listening on {config.listen_host}:{config.listen_port}")
        while not graceful_exit:
            try:
                client_socket, client_address = server_socket.accept()
                if available > 0:
                    available -= 1
                    process_thread = threading.Thread(
                        target=process, args=(client_socket, client_address)
                    )
                    process_thread.start()
                    process_threads[process_thread.native_id] = process_thread
                else:
                    try:
                        content = "Please retry after minutes"
                        header = "\n".join(
                            [
                                "HTTP/1.1 429 Too many requests",
                                "\n".join(
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
                        client_socket.send(data.encode("utf-8"))
                    finally:
                        client_socket.close()
            except GracefulExit:
                continue
        logger.info("exit gracefully...")
        for thread_id, thread in list(process_threads.items()):
            logger.debug(f"wait process thread {thread_id}...")
            thread.join()
        for thread in core_threads:
            logger.debug(f"core thread {thread.native_id}...")
            thread.join()
    logger.info("good bye!")
