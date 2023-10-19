"""
This module contains the class for a pop up window to make a new recipe.
version: 1.0.0 Initial commit by Roberts balulis
"""
__version__ = "1.0.0"

from tkinter import ttk
from tkinter.messagebox import showinfo

import customtkinter
from pyodbc import Error as PyodbcError

from .sql_connection import SQLConnection
from .create_log import setup_logger
from .gui import App
from .config_handler import ConfigHandler


class MakeRecipeWindow(customtkinter.CTkToplevel):
    """Class for a pop up window to make a new recipe."""
    def __init__(self, app_instance:"App",  texts, parent_id=None, is_child=None, *args, **kwargs):
        super().__init__( *args, **kwargs)

        self.app_instance = app_instance
        self.texts = texts
        self.parent_id = parent_id
        self.is_child = is_child
        self.logger = setup_logger("Make_recipe_window")

        # Gets all the configs for this module
        config_manager = ConfigHandler()
        make_recipe_window_config_data = config_manager.make_recipe_window
        self.SQL_CRED_NAME:str = make_recipe_window_config_data["sql_connection_file_name"]
        self.SQL_CRED_ENV_KEY_NAME:str = make_recipe_window_config_data["sql_connection_env_key_name"]

        self.configure_ui()
        self.title("")
        self.resizable(False, False)
        self.geometry("400x700+600+400")
        self.transient(self.app_instance)


    def configure_ui(self):
        """Configure the UI elements of the window."""

        self.name_label = customtkinter.CTkLabel(self, text=self.texts['recipe_name'],
                                                     font=("Helvetica", 16))
        self.name_label.pack()
        self.name_entry = customtkinter.CTkEntry(self,
                                                     width=200)
        self.name_entry.pack()

        self.comment_label = customtkinter.CTkLabel(self, text=self.texts['recipe_comment'],
                                                        font=("Helvetica", 16))
        self.comment_label.pack()
        self.comment_entry = customtkinter.CTkEntry(self,
                                                        width=200)
        self.comment_entry.pack()

        self.submit_button = customtkinter.CTkButton(self,
                                                         text=self.texts['recipe_submit'],
                                                         command=self.check_struct,
                                                         width=200,
                                                         height=40,
                                                         font=("Helvetica", 18))
        self.submit_button.pack(pady=10)

        self.configure_treeview()
        
    def configure_treeview(self):
        """Configure the TreeView for the recipe structures."""

        self.treeview_select_structure = ttk.Treeview(self,selectmode="browse", style="Treeview")
        self.treeview_select_structure.pack(fill="none")
        self.treeview_select_structure["columns"] = ("id", "Structure name")

        self.treeview_select_structure.column("#0", width=0, stretch=False)
        self.treeview_select_structure.column("id", width=0, stretch=False)
        self.treeview_select_structure.column("Structure name", width=300, stretch=False)

        self.treeview_select_structure.heading("#0", text="", anchor="w")
        self.treeview_select_structure.heading("id", text="Structure", anchor="w")
        self.treeview_select_structure.heading("Structure name", text=self.texts["treeview_select_structure_name"], anchor="w")

        self.populate_data()


    def populate_data(self):
        """Populate the treeview with data fetched from the database."""
        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials(self.SQL_CRED_NAME, self.SQL_CRED_ENV_KEY_NAME)
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                try:
                    cursor.execute('SELECT [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
                    rows = cursor.fetchall()

                    for row in rows:
                        recipe_id, RecipeStructureName = row
                        self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

                except Exception as e:
                    self.logger.error(f"Error while executing SQL queries: {e}")
                    showinfo(title="Info", message=self.texts["error_with_database"])

        except PyodbcError as e:
            self.logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            self.logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)


    def check_struct(self):
        """Check if a structure is selected and submit the new recipe."""
        try:
            selected_structure_item = self.treeview_select_structure.selection()[0]
            selected_structure_id = self.treeview_select_structure.item(selected_structure_item, "values")[0]

            self.app_instance.submit_new_recipe(self.name_entry.get(), self.comment_entry.get(),selected_structure_id, self.parent_id)
            self.destroy()

        except IndexError:
            showinfo(title='Information', message=self.texts["select_unit_to_download_header"])