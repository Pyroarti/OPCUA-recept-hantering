import pyodbc
from pyodbc import Error as PyodbcError
from typing import Tuple, Optional, Dict
from .data_encrypt import DataEncrypt


class SQLConnection:


    def __init__(self):
        pass


    def get_database_credentials(self, config_file_name: str, win_env_key_name: str) -> Dict[str, str]:
        """Get database credentials from config file
        :param config_file_name: config file name
        :param win_env_key_name: windows environment key name
        :return: database credentials"""

        data_encrypt = DataEncrypt()
        sql_config = data_encrypt.encrypt_credentials(config_file_name, win_env_key_name)

        if not sql_config:
            raise FileNotFoundError("Something went wrong with crypting/decrypting the config file.")

        database_config = sql_config.get("database", {})
        return {
            "server": database_config.get("server", ""),
            "database": database_config.get("database_name", ""),
            "username": database_config.get("username", ""),
            "password": database_config.get("password", "")
        }


    def connect_to_database(
        self,
        db_credentials: Dict[str, str],
        timeout_duration: int = 10
    ) -> Tuple[Optional[pyodbc.Cursor], Optional[pyodbc.Connection]]:

        """Connect to database
        :param db_credentials: database credentials
        :param timeout_duration: timeout duration in seconds (default: 10)
        :return: cursor and connection objects"""

        try:
            cnxn = pyodbc.connect(
                f'DRIVER={{SQL Server}};SERVER={db_credentials["server"]};'
                f'DATABASE={db_credentials["database"]};UID={db_credentials["username"]};'
                f'PWD={db_credentials["password"]}',
                timeout=timeout_duration
            )
            cursor = cnxn.cursor()
            return cursor, cnxn

        except pyodbc.Error as exception:
            error = exception.args[1]
            raise PyodbcError(f"Database connection failed: {error}")

        except IndexError as exception:
            raise IndexError("Database credentials seem to be incomplete.")

        except Exception as exception:
            raise Exception("An unexpected error occurred while connecting to the database.")


    def disconnect_from_database(self, cursor: pyodbc.Cursor, cnxn: pyodbc.Connection) -> None:
        """Disconnect from database"""
        cursor.close()
        cnxn.close()
