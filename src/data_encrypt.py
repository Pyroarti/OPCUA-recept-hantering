"""
This file contains class to encrypt and decrypt json files that can contain sensetive data by encrypting it with Fernet and keeping
the key in the operating system's environment variables.
version: 1.0.0 Inital commit by Roberts balulis
"""
__version__ = "1.0.0"


from pathlib import Path
import json
import os
from cryptography.fernet import Fernet, InvalidToken

try:
    from .create_log import setup_logger
except ImportError:
    print("The create_logger module was not found. Please make sure it is in the same directory as this script.")

logger = setup_logger(__name__)


class DataEncryptor():
    """
    Class for handling encryption and decryption of sensitive data.

    This class provides methods to handle encryption and decryption of
    sensitive data files using Fernet encryption. The encryption key is
    retrieved from the operating system's environment variables.
    """

    def __init__(self):
        self.output_path = Path(__file__).parent.parent


    def encrypt_credentials(self, config_filename:str, env_key_name:str) -> dict:
        """
        Checks if the given configuration file is encrypted. If not
        it encrypts it using the key retrieved from the environment variables.

        This function checks if the given configuration file is encrypted. If not,
        it encrypts it using the key retrieved from the environment variables.
        Then, it decrypts the file and returns its content as a dictionary.

        Parameters
        ----------
        config_filename - The name of the configuration file to be encrypted/decrypted.
        env_key_name - The name of the environment variable where the encryption key is stored.

        Returns
        -------
        dict
            The decrypted contents of the configuration file.
        """

        config_path = self.output_path / "configs" / config_filename

        key = os.environ.get(env_key_name)

        if key is None:
            logger.error(f"{env_key_name} is not set in the environment")
            raise ValueError(f"{env_key_name} is not set in the environment")

        key = key.encode()

        if not self.is_encrypted(config_path):
            self.encrypt_file(config_path, key)

        decrypted_data = self.decrypt_file(config_path, key)
        config = json.loads(decrypted_data)

        return config


    @staticmethod
    def encrypt_file(file_path: str, key: str):
        """
        Encrypts a file using the given key.

        Parameters
        ----------
        file_path: - The path to the file to be encrypted.
        key: - The encryption key.
        """

        try:
            with open(file_path, 'rb') as file:
                data = file.read()
        except FileNotFoundError:
            logger.error(f"File {file_path} not found")
            raise FileNotFoundError(f"File {file_path} not found")

        except PermissionError:
            logger.error(f"Permission denied for file {file_path}")
            raise PermissionError(f"Permission denied for file {file_path}")

        fernet_key = Fernet(key)

        try:
            encrypted_data = fernet_key.encrypt(data)
        except InvalidToken:
            logger.error("Invalid encryption token or corrupted data.")
            raise ValueError("Invalid encryption token or corrupted data.")

        with open(file_path, 'wb') as file:
            file.write(encrypted_data)


    @staticmethod
    def decrypt_file(file_path:str, key:str) -> bytes:
        """
        Decrypts a file using the given key and returns its contents.

        Parameters
        ----------
        file_path: str - The path to the file to be encrypted.
        key: str - The encryption key.
        """

        try:
            with open(file_path, 'rb') as file:
                encrypted_data = file.read()
        except FileNotFoundError:
            logger.error(f"File {file_path} not found")
            raise FileNotFoundError(f"File {file_path} not found")

        except PermissionError:
            logger.error(f"Permission denied for file {file_path}")
            raise PermissionError(f"Permission denied for file {file_path}")

        fernet_key = Fernet(key)

        try:
            decrypted_data = fernet_key.decrypt(encrypted_data)
        except InvalidToken:
            logger.error("Invalid encryption token or corrupted data.")
            raise ValueError("Invalid encryption token or corrupted data.")

        return decrypted_data


    def is_encrypted(self, file_path:str) -> bool:
        """
        Checks if a file is encrypted by trying to load it as a JSON file.

        Parameters
        ----------
        file_path: str - The path to the file to be encrypted.
        """

        try:
            with open(file_path, 'rb') as file:
                data = file.read()

        except FileNotFoundError:
            logger.error(f"File {file_path} not found")
            raise FileNotFoundError(f"File {file_path} not found")

        except PermissionError:
            logger.error(f"Permission denied for file {file_path}")
            raise PermissionError(f"Permission denied for file {file_path}")

        try:
            json.loads(data)
            return False
        except json.JSONDecodeError:
            return True


    def decrypt_file_to_edit(self, config_filename: str, env_key_name: str):
        """
        Decrypts the given configuration file for manual editing and saves it in decrypted format.

        Parameters
        ----------
        config_filename : str
            The name of the configuration file to be decrypted.
        env_key_name : str
            The name of the environment variable where the encryption key is stored.
        """

        config_path = self.output_path / "configs" / config_filename

        key = os.environ.get(env_key_name)

        if key is None:
            logger.error(f"{env_key_name} is not set in the environment")
            raise ValueError(f"{env_key_name} is not set in the environment")

        key = key.encode()

        if self.is_encrypted(config_path):
            decrypted_data = self.decrypt_file(config_path, key)
            with open(config_path, 'wb') as file:
                file.write(decrypted_data)
        else:
            logger.info(f"File {config_filename} is already decrypted.")

