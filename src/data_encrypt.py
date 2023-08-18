from pathlib import Path
import json
import os
from cryptography.fernet import Fernet

from .create_log import setup_logger

logger = setup_logger('data_encrypt')

class DataEncrypt():
    """
    Class for handling encryption and decryption of sensitive data.

    This class provides methods to handle encryption and decryption of
    sensitive data files using Fernet encryption. The encryption key is
    retrieved from the operating system's environment variables.

    """

    def __init__(self):
        self.output_path = Path(__file__).parent.parent


    def encrypt_credentials(self, config_filename, env_key_name):
        """
        Encrypts and decrypts configuration files.

        This function checks if the given configuration file is encrypted. If not,
        it encrypts it using the key retrieved from the environment variables.
        Then, it decrypts the file and returns its content as a dictionary.

        Parameters
        ----------
        config_filename : str
            The name of the configuration file to be encrypted/decrypted.
        env_key_name : str
            The name of the environment variable where the encryption key is stored.

        Returns
        -------
        dict
            The decrypted contents of the configuration file.
        """

        config_path = self.output_path / "configs" / config_filename
        key = os.environ.get(env_key_name)
        if key is None:
            logger.error(f"{env_key_name} is not set in the environment")
            return None
        key = key.encode()
        if not self.is_encrypted(config_path):
            self.encrypt_file(config_path, key)
        decrypted_data = self.decrypt_file(config_path, key)
        config = json.loads(decrypted_data)
        return config


    @staticmethod
    def encrypt_file(file_path, key):
        """
        Encrypts a file using the given key.
        """
        with open(file_path, 'rb') as file:
            data = file.read()

        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data)

        with open(file_path, 'wb') as file:
            file.write(encrypted_data)


    @staticmethod
    def decrypt_file(file_path, key):
        """
        Decrypts a file using the given key and returns its contents.
        """
        with open(file_path, 'rb') as file:
            encrypted_data = file.read()

        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data)

        return decrypted_data


    def is_encrypted(self, file_path):
        """
        Checks if a file is encrypted by trying to load it as a JSON file.
        """
        with open(file_path, 'rb') as file:
            data = file.read()
        try:
            json.loads(data)
            return False
        except json.JSONDecodeError:
            return True
