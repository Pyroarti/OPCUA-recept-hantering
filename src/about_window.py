import customtkinter
from tkinter import ttk
from tkinter.messagebox import showinfo
from pyodbc import Error as PyodbcError
import os
import webbrowser
import markdown

from .sql_connection import SQLConnection
from .create_log import setup_logger
from .gui import App

logger = setup_logger(__name__)

class AboutWindow(customtkinter.CTkToplevel):
    """Class for a pop up window."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resizable(False, False)
        self.title("About")
        pop_up_width = 700
        pop_up_height = 350
        position_x = 900
        position_y = 400
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")

        with open("Note.txt", "r", encoding="utf-8") as text_file:
            about_text = text_file.read()

        self.label = customtkinter.CTkLabel(self, text=about_text, justify="left", anchor="w")
        self.label.pack(padx=5, pady=10)

        self.change_log_button = customtkinter.CTkButton(self, text="Changelogs",
                                                     command=self.show_changelog)
        self.change_log_button.pack(pady=1)


    def show_changelog(self):
        """Open a webpage and shows the changelog"""
        md_file_path = 'CHANGE_LOG.md'
        html_file_path = 'CHANGE_LOG.html'

        if os.path.isfile(md_file_path):
            try:
                with open(md_file_path, 'r', encoding='utf-8') as md_file:
                    md_content = md_file.read()
                    html_content = markdown.markdown(md_content)

                with open(html_file_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(html_content)

                webbrowser.open(html_file_path)

            except Exception as exeption:
                logger.warning(f"Error opening file: {exeption}")