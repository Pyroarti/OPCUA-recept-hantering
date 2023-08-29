import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

class SuppressSpecificLogs(logging.Filter):
    def __init__(self, suppress_list):
        self.suppress_list = suppress_list

    def filter(self, record):
        for msg in self.suppress_list:
            if msg in record.getMessage():
                return 0
        return 1

def setup_logger(logger_name, suppress_list=None):

    """
    Creates and configures a logging instance for the specified module.

    This function creates a logger with the provided logger_name, sets its level to DEBUG,
    and associates it with a file handler that writes to a log file. The log file is stored
    in a 'logs' directory or 'alarms' directory depending on the logger_name.

    Parameters:
    logger_name (str): The name of the logger. This will be the name of the module where the
    logger is used.

    Usage:
    ```
    logger = setup_logger('module_name')
    ```

    This will create a logger that writes messages to the 'module_name.log' file in the 'logs'
    directory. If the logger_name is 'alarms', it will write to the 'alarms' directory instead.
    """

    # Get or create logger instance with the specified name
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    # Determine the path to the application
    if getattr(sys, 'frozen', False):
        app_path = sys._MEIPASS
    else:
        app_path = os.path.dirname(os.path.abspath(__file__))

    # Determine log directory based on logger name
    log_folder = "alarms" if logger_name == "alarms" else "logs"
    log_dir = os.path.abspath(os.path.join(app_path, os.pardir, log_folder))
    os.makedirs(log_dir, exist_ok=True)  # Create logs directory if it doesn't exist

    log_file = os.path.join(log_dir, f"{logger_name}.log")
    formatter = logging.Formatter('%(asctime)s|%(levelname)s|%(name)s|%(message)s',
                                  datefmt='%Y:%m:%d %H:%M:%S')

    handler = RotatingFileHandler(log_file, maxBytes=100*1024*1024, backupCount=3) # 100 MB max size per file, 3 files max
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    
    if suppress_list:
        handler.addFilter(SuppressSpecificLogs(suppress_list))

    logger.addHandler(handler)

    return logger


def delete_old_logs(log_dir, days_old):
    """
    Delete log files in the specified directory that are older than the specified number of days.

    Parameters:
    log_dir (str): The directory containing the log files.
    days_old (int): The age (in days) after which log files should be deleted.
    """
    current_time = time.time()

    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)

        # Check if it's a file (not a sub-directory)
        if os.path.isfile(file_path):
            file_creation_time = os.path.getctime(file_path)

            if (current_time - file_creation_time) > days_old * 86400:  # 86400 seconds in a day
                os.remove(file_path)
                print(f"Deleted old log file: {file_path}")

if __name__ == "__main__":
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(base_path)
    delete_old_logs(os.path.join(base_path, "logs"), 30)

