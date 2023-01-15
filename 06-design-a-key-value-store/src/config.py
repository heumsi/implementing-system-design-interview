import os

import yaml
from pydantic import BaseSettings, HttpUrl, parse_obj_as


class Config(BaseSettings):
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "8080"))
    n_copy: int = int(os.getenv("N_COPY", 3))

    @property
    def http_url(self) -> HttpUrl:
        return parse_obj_as(HttpUrl, f"http://{self.host}:{self.port}")

    @classmethod
    def from_yaml(cls, yaml_path: str):
        with open(yaml_path) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            return cls(**data)
