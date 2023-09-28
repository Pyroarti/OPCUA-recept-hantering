"""
This module contains the class for the pop up window that appears when the user wants to edit a recipe.
version: 1.0.0 Inital commit by Roberts balulis
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


class Edit_recipe_window(customtkinter.CTkToplevel):
    """Class for a pop up window."""
    def __init__(self, app_instance:"App",  texts, recipeName, recipeComment, recipe_struct, selected_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.app_instance = app_instance
        self.texts = texts
        self.recipe_name = recipeName
        self.recipe_comment = recipeComment
        self.selected_id = selected_id
        cursor = None
        cnxn = None

        self.resizable(False, False)
        pop_up_width = 400
        pop_up_height = 450
        position_x = 600
        position_y = 400
        self.attributes('-topmost', True)
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")

        self.logger = setup_logger(__name__)

        # Gets all the configs for this module
        config_manager = ConfigHandler()
        edit_recipe_window_config_data = config_manager.edit_recipe_window
        SQL_CRED_NAME:str = edit_recipe_window_config_data["sql_connection_file_name"]
        SQL_CRED_ENV_KEY_NAME:str = edit_recipe_window_config_data["sql_connection_env_key_name"]

        self.name_label = customtkinter.CTkLabel(self, text=self.texts['recipe_name'],
                                                 font=("Helvetica", 16))
        self.name_label.pack()
        self.name_entry = customtkinter.CTkEntry(self,
                                                 width=200)
        self.name_entry.pack()
        self.name_entry.insert(0, self.recipe_name)

        self.comment_label = customtkinter.CTkLabel(self, text=self.texts['recipe_comment'],
                                                    font=("Helvetica", 16))
        self.comment_label.pack()
        self.comment_entry = customtkinter.CTkEntry(self,
                                                    width=200)
        self.comment_entry.pack()
        self.comment_entry.insert(0, self.recipe_comment)

        recipe_struct_mapping = {2: "Master & SMC1 & SMC2", 4: "Master & SMC1", 5: "Master & SMC2"}
        id_mapping = {}

        self.treeview_select_structure = ttk.Treeview(self,selectmode="browse", style="Treeview")
        self.treeview_select_structure.pack(pady=10)
        self.treeview_select_structure["columns"] = ("id", "Structure name")

        self.treeview_select_structure.column("#0", width=0, stretch=False)
        self.treeview_select_structure.column("id", width=0, stretch=False)
        self.treeview_select_structure.column("Structure name", width=300, stretch=False)

        self.treeview_select_structure.heading("#0", text="", anchor="w")
        self.treeview_select_structure.heading("id", text="Structure", anchor="w")
        self.treeview_select_structure.heading("Structure name", text=self.texts["treeview_select_structure_name"], anchor="w")

        self.submit_button = customtkinter.CTkButton(self,
                                                     text=self.texts['update_recipe_submit'],
                                                     command=self.check_struct,
                                                     width=200,
                                                     height=40,
                                                     font=("Helvetica", 18))
        self.submit_button.pack(pady=10)

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials(SQL_CRED_NAME, SQL_CRED_ENV_KEY_NAME)
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                cursor.execute('SELECT TOP (1000) [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
                rows = cursor.fetchall()

                for row in rows:
                    recipe_id, RecipeStructureName = row
                    item_id = self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

                if RecipeStructureName in recipe_struct_mapping.values():
                    recipe_struct_for_this_item = next((key for key, value in recipe_struct_mapping.items() if value == RecipeStructureName), None)
                    if recipe_struct_for_this_item:
                        id_mapping[recipe_struct_for_this_item] = item_id

            mapped_id = id_mapping.get(recipe_struct)
            if mapped_id:
                self.treeview_select_structure.selection_set(mapped_id)
            else:
                self.logger.warning(f"Error: No mapping for recipe_struct value {recipe_struct}")

        except PyodbcError as e:
            self.logger.warning(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            self.logger.warning("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            self.logger.warning(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)


    def check_struct(self):
        """
        Checks the structure of the modified step and submits the new recipe to the database.
        """
        try:
            selected_structure_item = self.treeview_select_structure.selection()[0]
            selected_structure_id = self.treeview_select_structure.item(selected_structure_item, "values")[0]
            self.logger.info(f'Selected structure ID: {selected_structure_id}')

            self.app_instance.update_recipe(self.name_entry.get(), self.comment_entry.get(),selected_structure_id, self.selected_id)

            self.destroy()
        except IndexError:
            showinfo(title='Information', message=self.texts["select_unit_to_download_header"])
            self.logger.warning('No structure selected by user')
            return