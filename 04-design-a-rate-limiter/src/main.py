import argparse
import logging
import signal

from src.config_manager import ConfigManager
from src.core import GracefulExit
from src.server import Server
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


def _register_gracefully_exit_handler() -> None:
    def raise_graceful_exit(*args):
        logger.debug("got shutdown signal")
        raise GracefulExit()

    signal.signal(signal.SIGINT, raise_graceful_exit)
    signal.signal(signal.SIGTERM, raise_graceful_exit)


if __name__ == "__main__":
    _register_gracefully_exit_handler()
    config_manager = ConfigManager(args.config)
    config_manager.start()
    server = Server(args.hostname, args.port, config_manager)
    try:
        server.run()
    finally:
        config_manager.stop()
    logger.info("good bye!")
