"""
This module contains the class for the pop-up window that appears when the user wants to edit a recipe.
The purpose of this module is to provide a user interface to modify an existing recipe in the system.
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

DATABASE_ERROR_MSG = "An error occurred with the database. Check the logs for more information."

RECIPE_STRUCT_MAPPING = {2: "Master & SMC1 & SMC2", 4: "Master & SMC1", 5: "Master & SMC2"}

class EditRecipeWindow(customtkinter.CTkToplevel):
    """Class for a pop-up window to change a recipe's name, comment, and structure."""

    def __init__(self, app_instance: App, texts, recipe_name, recipe_comment, recipe_struct, selected_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        

        self.app_instance = app_instance
        self.texts = texts
        self.recipe_name = recipe_name
        self.recipe_comment = recipe_comment
        self.selected_id = selected_id
        self.recipe_struct = recipe_struct
        
        self.configure_ui()

        self.logger = setup_logger("Edit_recipe_window")
        self.populate_data()

    def configure_ui(self):
        """Configure the UI elements of the window."""
        self.resizable(False, False)
        self.title("")
        self.geometry("400x450+600+400")

        self.name_label = customtkinter.CTkLabel(self, text=self.texts['recipe_name'], font=("Helvetica", 16))
        self.name_label.pack()
        
        self.name_entry = customtkinter.CTkEntry(self, width=200)
        self.name_entry.pack()
        self.name_entry.insert(0, self.recipe_name)

        self.comment_label = customtkinter.CTkLabel(self, text=self.texts['recipe_comment'], font=("Helvetica", 16))
        self.comment_label.pack()
        
        self.comment_entry = customtkinter.CTkEntry(self, width=200)
        self.comment_entry.pack()
        self.comment_entry.insert(0, self.recipe_comment)

        self.configure_treeview()

        self.submit_button = customtkinter.CTkButton(self, text=self.texts['update_recipe_submit'], command=self.check_struct, width=200, height=40, font=("Helvetica", 18))
        self.submit_button.pack(pady=10)

    def configure_treeview(self):
        """Configure the TreeView for the recipe structures."""
        self.treeview_select_structure = ttk.Treeview(self, selectmode="browse", style="Treeview")
        self.treeview_select_structure.pack(pady=10)
        self.treeview_select_structure["columns"] = ("id", "Structure name")

        self.treeview_select_structure.column("#0", width=0, stretch=False)
        self.treeview_select_structure.column("id", width=0, stretch=False)
        self.treeview_select_structure.column("Structure name", width=300, stretch=False)

        self.treeview_select_structure.heading("#0", text="", anchor="w")
        self.treeview_select_structure.heading("id", text="Structure", anchor="w")
        self.treeview_select_structure.heading("Structure name", text=self.texts["treeview_select_structure_name"], anchor="w")

    def populate_data(self):
        """Populate the treeview with data fetched from the database."""
        try:
            sql_connection = SQLConnection()
            config_manager = ConfigHandler()
            edit_recipe_window_config_data = config_manager.edit_recipe_window

            sql_credentials = sql_connection.get_database_credentials(
                edit_recipe_window_config_data["sql_connection_file_name"], 
                edit_recipe_window_config_data["sql_connection_env_key_name"]
            )

            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)
            cursor.execute("SELECT [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]")
            rows = cursor.fetchall()
            sql_connection.disconnect_from_database(cursor, cnxn)
            inverted_recipe_mapping = {value: key for key, value in RECIPE_STRUCT_MAPPING.items()}

            id_mapping = {}
            for row in rows:
                recipe_id, RecipeStructureName = row
                item_id = self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

                if RecipeStructureName in inverted_recipe_mapping:
                    id_mapping[inverted_recipe_mapping[RecipeStructureName]] = item_id

            mapped_id = id_mapping.get(self.recipe_struct)
            if mapped_id:
                self.treeview_select_structure.selection_set(mapped_id)
            else:
                self.logger.error(f"Error: No mapping for recipe_struct value {self.recipe_struct}")

        except PyodbcError as e:
            self.logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=DATABASE_ERROR_MSG)

        except IndexError:
            self.logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=DATABASE_ERROR_MSG)

        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=DATABASE_ERROR_MSG)

    def check_struct(self):
        """Check the structure of the modified step and submit the new recipe to the database."""
        try:
            selected_structure_item = self.treeview_select_structure.selection()[0]
            selected_structure_id = self.treeview_select_structure.item(selected_structure_item, "values")[0]
            self.logger.info(f'Selected structure ID: {selected_structure_id}')

            self.app_instance.update_recipe(self.name_entry.get(), self.comment_entry.get(), selected_structure_id, self.selected_id)
            self.destroy()

        except IndexError:
            showinfo(title='Information', message=self.texts["select_unit_to_download_header"])
            self.logger.error('No structure selected by user')
