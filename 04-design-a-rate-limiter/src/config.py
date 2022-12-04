from dataclasses import dataclass
from typing import Dict


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
