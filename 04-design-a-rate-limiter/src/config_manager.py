import logging
import threading
from time import sleep
from typing import Optional

import yaml

from src.config import Config


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
