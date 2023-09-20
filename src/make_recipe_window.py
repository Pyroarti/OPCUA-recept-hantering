import customtkinter
from tkinter import ttk
from tkinter.messagebox import showinfo
from pyodbc import Error as PyodbcError

from .sql_connection import SQLConnection
from .create_log import setup_logger
from .gui import App

logger = setup_logger(__name__)

class MakeRecipeWindow(customtkinter.CTkToplevel):
    """Class for a pop up window."""
    def __init__(self, app_instance:"App",  texts, parent_id=None, is_child=None, *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.resizable(False, False)
        self.app_instance = app_instance
        self.texts = texts
        self.parent_id = parent_id
        self.is_child = is_child
        self.title("")
        pop_up_width = 400
        pop_up_height = 700
        position_x = 600
        position_y = 400
        self.attributes('-topmost', True)

        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")
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

        self.treeview_select_structure = ttk.Treeview(self,selectmode="browse", style="Treeview")
        self.treeview_select_structure.pack(fill="none")
        self.treeview_select_structure["columns"] = ("id", "Structure name")

        self.treeview_select_structure.column("#0", width=0, stretch=False)
        self.treeview_select_structure.column("id", width=0, stretch=False)
        self.treeview_select_structure.column("Structure name", width=300, stretch=False)

        self.treeview_select_structure.heading("#0", text="", anchor="w")
        self.treeview_select_structure.heading("id", text="Structure", anchor="w")
        self.treeview_select_structure.heading("Structure name", text=self.texts["treeview_select_structure_name"], anchor="w")

        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                try:
                    cursor.execute('SELECT TOP (1000) [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
                    rows = cursor.fetchall()

                    for row in rows:
                        recipe_id, RecipeStructureName = row
                        self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

                except Exception as e:
                    logger.warning(f"Error while executing SQL queries: {e}")
                    showinfo(title="Info", message=self.texts["error_with_database"])

        except PyodbcError as e:
            logger.warning(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.warning("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.warning(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)