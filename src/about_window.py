"""
Opens a pop up window with information about the program and to see the changelog.
version: 1.0.0 Inital commit by Roberts balulis
"""
__version__ = "1.0.0"

import customtkinter
import os
import webbrowser
import markdown

from .create_log import setup_logger
from .config_handler import ConfigHandler

md_file_path = 'CHANGE_LOG.md'
html_file_path = 'CHANGE_LOG.html'
about_text_path = "Note.txt"


class AboutWindow(customtkinter.CTkToplevel):
    """Class for a pop up window. And shows the changelog"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.logger = setup_logger(__name__)
        self.resizable(False, False)
        self.title("Om")
        pop_up_width = 700
        pop_up_height = 350
        position_x = 900
        position_y = 400
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")

        with open(about_text_path, "r", encoding="utf-8") as text_file:
            about_text = text_file.read()

        self.label = customtkinter.CTkLabel(self, text=about_text, justify="left", anchor="w")
        self.label.pack(padx=5, pady=10)

        self.change_log_button = customtkinter.CTkButton(self, text="Changelogs",
                                                     command=self.show_changelog)
        self.change_log_button.pack(pady=1)


    def show_changelog(self):
        """Open a webpage and shows the changelog"""

        if os.path.isfile(md_file_path):
            try:
                with open(md_file_path, 'r', encoding='utf-8') as md_file:
                    md_content = md_file.read()
                    html_content = markdown.markdown(md_content)

                with open(html_file_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(html_content)

                webbrowser.open(html_file_path)

            except Exception as exeption:
                self.logger.warning(f"Error opening file: {exeption}")