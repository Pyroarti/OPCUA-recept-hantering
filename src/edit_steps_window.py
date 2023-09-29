"""
This module contains the class for a pop up window to edit servo steps.
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


class Edit_steps_window(customtkinter.CTkToplevel):
    """Class for a pop up window to edit servo steps."""
    def __init__(self, master, rows, selected_id, texts, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.selected_id = selected_id
        self.rows = rows
        self.texts = texts
        self.title("")
        pop_up_width = 800
        pop_up_height = 900
        position_x = 900
        position_y = 400
        self.resizable(False, False)
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")

        self.logger = setup_logger(__name__)

        # Gets all the configs for this module
        config_manager = ConfigHandler()
        edit_recipe_steps_window_config_data = config_manager.edit_steps_window
        self.SQL_CRED_NAME:str = edit_recipe_steps_window_config_data["sql_connection_file_name"]
        self.SQL_CRED_ENV_KEY_NAME:str = edit_recipe_steps_window_config_data["sql_connection_env_key_name"]

        self.search_var = customtkinter.StringVar()
        self.search_bar = customtkinter.CTkEntry(self, textvariable=self.search_var)
        self.search_bar.pack(anchor="nw", pady=10, padx=10)
        self.search_var.trace('w', self.update_treeview)

        self.edit_recipe_grid()

    def edit_recipe_grid(self):
        self.edit_recipe_treeview = ttk.Treeview(self, columns=("Unit name", "Tag name", "Tag value", "Unit id"),
                              show="headings", height=10, style="Treeview", selectmode='browse')

        self.edit_recipe_treeview.heading("#0", text="", anchor="w")
        self.edit_recipe_treeview.heading("Unit name", text=self.texts['data_editor_grid_unit'],anchor="w")
        self.edit_recipe_treeview.heading("Tag name", text=self.texts['data_editor_grid_tag_name'],anchor="w")
        self.edit_recipe_treeview.heading("Tag value", text=self.texts['data_editor_grid_tag_value'],anchor="w")
        self.edit_recipe_treeview.heading("Unit id", text='id',anchor="w")

        self.edit_recipe_treeview.column("#0", width=0, stretch=False)
        self.edit_recipe_treeview.column("Unit name", width=100, stretch=False)
        self.edit_recipe_treeview.column("Tag name", width=400, stretch=False)
        self.edit_recipe_treeview.column("Tag value", width=200, stretch=False)
        self.edit_recipe_treeview.column("Unit id", width=0, stretch=False)

        self.edit_recipe_treeview.pack(padx=10, pady=5, expand=True, fill="y",anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.edit_recipe_treeview.yview)
        vsb.place(x=30+700+2, y=50, height=825+20)
        self.edit_recipe_treeview.configure(yscrollcommand=vsb.set)

        for row in self.rows:
            unit_id, tag_name, tag_value, tag_datatype ,unit_name = row
            self.edit_recipe_treeview.insert("", "end", values=(unit_name, tag_name, tag_value, unit_id))

        self.edit_recipe_treeview.bind("<Double-1>", self.on_double_click)


    def update_treeview(self, *args):
        
        search_term = self.search_var.get()

        for i in self.edit_recipe_treeview.get_children():
            self.edit_recipe_treeview.delete(i)

        for row in self.rows:
            unit_id, tag_name, tag_value, tag_datatype, unit_name = row

            if search_term.lower() in tag_name.lower():
                self.edit_recipe_treeview.insert("", "end", values=(unit_name, tag_name, tag_value, unit_id))


    def on_double_click(self, event):

        selected_item = self.edit_recipe_treeview.selection()[0]
        selected_values = self.edit_recipe_treeview.item(selected_item)['values']
        unit_name = selected_values[0]
        tag_name = selected_values[1]
        tag_value = selected_values[2]
        unit_id = selected_values[3]

        self.edit_step_dialog = customtkinter.CTkToplevel(self)
        self.edit_step_dialog.title("Edit TagValue")
        self.edit_step_dialog.geometry("400x150")

        info_label = customtkinter.CTkLabel(self.edit_step_dialog, text=self.texts['changin_value_info'],font=("Helvetica", 18))
        info_label.pack(pady=5)

        self.new_value_entry = customtkinter.CTkEntry(self.edit_step_dialog, width = 170, height = 32, font=("Helvetica", 15))
        self.new_value_entry.pack(pady=5)
        self.new_value_entry.insert(0, tag_value)

        save_button = customtkinter.CTkButton(self.edit_step_dialog, text="Spara",width=160,height=35,
                                              command=lambda: self.save_changes(selected_item,tag_name,unit_id))
        save_button.pack()


    def save_changes(self, selected_item, tag_name,unit_id):
        cursor = None
        cnxn = None

        edited_tag_value = self.new_value_entry.get()
        self.edit_recipe_treeview.item(selected_item, values=(self.edit_recipe_treeview.item(selected_item)['values'][0],
                                                                  tag_name, edited_tag_value,unit_id))
        self.edit_step_dialog.destroy()

        stored_procedure_name = 'update_value'
        recipe_id_param_name = "RecipeID"
        unit_id_param_name = "UnitID"
        tag_name_param_name = 'TagName'
        tag_value_param_name = 'TagValue'

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials(self.SQL_CRED_NAME, self.SQL_CRED_ENV_KEY_NAME)
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                    cursor.execute(f"EXEC {stored_procedure_name} \
                        @{tag_name_param_name}='{tag_name}', \
                        @{tag_value_param_name}={edited_tag_value}, \
                        @{recipe_id_param_name}={self.selected_id},\
                        @{unit_id_param_name}={unit_id};")
                    cnxn.commit()

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

        self.destroy()