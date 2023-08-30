from cryptography.fernet import Fernet
import os
from pathlib import Path
key = Fernet.generate_key()
print(key)
from tktooltip import ToolTip

import pyodbc

# List available drivers
print(pyodbc.drivers())



from tkinter import *
from tkinter.tix import *

root = Tk()
root.geometry("500x400")



my_button = Button(root, text="Click Me", font=("Helvetica", 28))
my_button.pack(pady=50)


ToolTip(my_button, msg="Hello")




root.mainloop()