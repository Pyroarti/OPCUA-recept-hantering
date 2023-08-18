from cryptography.fernet import Fernet
import os
from pathlib import Path
key = Fernet.generate_key()
print(key)


