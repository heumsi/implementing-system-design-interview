import logging


def setup_logger(log_format: str, verbose: bool) -> None:
    logging.basicConfig(
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.DEBUG if verbose else logging.INFO,
    )
