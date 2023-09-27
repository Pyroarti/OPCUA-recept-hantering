"""
This file contains the ConfigHandler class, which is used to handle configs files and return the data in them.
version: 1.0.0 Inital commit by Roberts balulis
"""
__version__ = "1.0.0"


import json
from pathlib import Path
from typing import Any, Dict


class ConfigHandler:
    """
    This class is used to handle configs files and return the data in them.
    """
    def __init__(self) -> None:

        self.output_path: Path = Path(__file__).parent.parent
        self.config_path: Path = self.output_path / "configs"

        if not self.config_path.exists():
            self.config_path.mkdir(parents=True, exist_ok=True)


    def get_config_data(self, config_name: str) -> Dict[str, Any]:
        """
        Returns the data in a config file as a dictionary.

        Parameters
        ----------
        config_name: The name of the config file to get the data from.

        Returns
        ----------
        The data in the config file as a dictionary.
        """

        config_path = self.config_path / config_name
        try:
            with open(config_path, "r") as config_file:
                config_data = json.load(config_file)
        except FileNotFoundError:
            raise (f"Config file {config_path} not found.")
        except json.decoder.JSONDecodeError:
            raise (f"Config file {config_path} is not valid JSON.")
        except Exception as exception:
            raise exception

        return config_data


    @property
    def phone_book(self) -> dict:
        return self.get_config_data('phone_book.json')


    @property
    def opcua_server_config(self) -> dict:
        return self.get_config_data('opcua_server_config.json')


    @property
    def opcua_server_alarm_config(self) -> dict:
        return self.get_config_data('opcua_server_alarm_config.json')


    @property
    def sms_config(self) -> dict:
        return self.get_config_data('sms_config.json')
    

    @property
    def edit_recipe_window(self) -> dict:
        return self.get_config_data('edit_recipe_window.json')
    

    @property
    def edit_steps_window(self) -> dict:
        return self.get_config_data('edit_steps_window.json')
    

    @property
    def make_recipe_window(self) -> dict:
        return self.get_config_data('make_recipe_window.json')
