"""
This file contains the ConfigHandler class, which is used to handle configs files and return the data in them.
version: 1.0.0 Inital commit by Roberts balulis
"""

import json
from pathlib import Path
from typing import Any, Dict


class ConfigHandler:
    """
    This class is used to handle configs files and return the data in them.
    """
    def __init__(self) -> None:
        self.output_path = Path(__file__).parent.parent
        self.config_path = self.output_path / "configs"


    def get_config_data(self, config_name: str) -> Dict[str, Any]:
        """
        Returns the data in a config file as a dictionary.
        param config_name: The name of the config file to get the data from.
        return: The data in the config file as a dictionary.
        """

        config_path = self.config_path / config_name
        try:
            with open(config_path, "r") as config_file:
                config_data = json.load(config_file)
        except FileNotFoundError:
            raise ConfigNotFound(f"Config file {config_path} not found.")
        except json.decoder.JSONDecodeError:
            raise InvalidConfigFormat(f"Config file {config_path} is not valid JSON.")
        except Exception as e:
            raise e 
        return config_data


class ConfigNotFound(Exception):
    """
    Raised when a config file is not found.
    """
    pass


class InvalidConfigFormat(Exception):
    """
    Raised when a config file is not valid JSON.
    """
    pass