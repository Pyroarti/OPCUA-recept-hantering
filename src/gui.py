# Python package
from pathlib import Path
from tkinter import ttk
from datetime import datetime
import asyncio
from threading import Thread
from queue import Queue
from tkinter.messagebox import showinfo
import os
import webbrowser
import markdown
from asyncua import ua
import json

# Third party package
import customtkinter
from customtkinter import CTkImage
from PIL import Image
import pyodbc

# Own package
from .ms_sql import from_units_to_sql_stepdata, from_sql_to_units_stepdata, check_recipe_data
from .data_encrypt import DataEncrypt
from .create_log import setup_logger
from .ip_checker import check_ip
from .opcua_alarm import monitor_alarms
from .webserver import main_webserver

# Setup logger for gui.py
logger = setup_logger('gui')


def get_database_connection(timeout_duration=10):

    """
    Establish a connection to a SQL server and return a cursor object and the connection.

    This function attempts to establish a connection to a SQL server using encrypted
    credentials retrieved from a JSON file. It also initializes a cursor object for
    executing SQL commands.

    Returns:
    tuple: A tuple containing two elements - the cursor object and the connection to
    the SQL server.

    Raises:
    pyodbc.Error: If there's an error establishing the database connection.
    Exception: For any other unexpected issues that may arise during the connection process.

    """

    try:
        data_encrypt = DataEncrypt()
        sql_config = data_encrypt.encrypt_credentials("sql_config.json", "SQL_KEY")
        database_config = sql_config["database"]
        server = database_config["server"]
        database = database_config["database_name"]
        username = database_config["username"]
        password = database_config["password"]

        cnxn = pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={server};\
                    DATABASE={database};UID={username};PWD={password}',
                    timeout=timeout_duration)
        cursor = cnxn.cursor()
        logger.info('Succesfully establishing database connection')

        return cursor, cnxn

    except pyodbc.Error as exeption:
        error = exeption.args[1]
        logger.error(f'Error establishing database connection: {error}')
    except Exception as exeption:
        logger.error(f'Unexpected error: {exeption}')

    return None, None


def run_monitor_alarms_loop():
    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        monitor_task = loop.create_task(monitor_alarms())

        loop.run_forever()
    finally:
        loop.stop()
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def run_asyncio_loop(queue):
    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        while True:
            coro = queue.get()
            if coro is None:
                break
            task = loop.create_task(coro)
            loop.run_until_complete(task)

    finally:
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


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
                logger.error(f"Error opening file: {exeption}")


class MakeRecipeWindow(customtkinter.CTkToplevel):
    """Class for a pop up window."""
    def __init__(self, app_instance,  texts, *args, **kwargs):
        super().__init__( *args, **kwargs)
        self.resizable(False, False)
        self.app_instance = app_instance
        self.texts = texts
        self.title("Recipe maker")
        pop_up_width = 400
        pop_up_height = 450
        position_x = 900
        position_y = 400

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

        cursor, cnxn = get_database_connection()
        try:
            cursor.execute('SELECT TOP (1000) [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
        except Exception as exeption:
            logger.error(f"Error while executing SELECT TOP: {exeption}")
            return

        rows = cursor.fetchall()

        cursor.close()
        cnxn.close()

        for row in rows:
            recipe_id, RecipeStructureName = row
            self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))

        # Binds a event where user selects something on the datagrid
        self.treeview_select_structure.bind('<<TreeviewSelect>>')

    def check_struct(self):
        try:
            selected_structure_item = self.treeview_select_structure.selection()[0]
            selected_structure_id = self.treeview_select_structure.item(selected_structure_item, "values")[0]

            self.app_instance.submit_new_recipe(self.name_entry.get(), self.comment_entry.get(),selected_structure_id)
        except IndexError:
            showinfo(title='Information', message=self.texts["select_unit_to_download_header"])
            self.focus_force()
            return

class Edit_recipe_window(customtkinter.CTkToplevel):
    """Class for a pop up window."""
    def __init__(self, app_instance:"App",  texts, selected_id, recipeName, recipeComment, recipe_struct, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resizable(False, False)
        self.app_instance = app_instance
        self.texts = texts
        self.title("Recipe editor")
        pop_up_width = 400
        pop_up_height = 450
        position_x = 900
        position_y = 400

        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")
        self.name_label = customtkinter.CTkLabel(self, text=self.texts['recipe_name'],
                                                 font=("Helvetica", 16))
        self.name_label.pack()
        self.name_entry = customtkinter.CTkEntry(self,
                                                 width=200,
                                                 placeholder_text=recipeName)
        self.name_entry.pack()

        self.comment_label = customtkinter.CTkLabel(self, text=self.texts['recipe_comment'],
                                                    font=("Helvetica", 16))
        self.comment_label.pack()
        self.comment_entry = customtkinter.CTkEntry(self,
                                                    width=200,
                                                    placeholder_text=recipeComment)
        self.comment_entry.pack()

        self.submit_button = customtkinter.CTkButton(self,
                                                     text=self.texts['update_recipe_submit'],
                                                     command=self.check_struct,
                                                     width=200,
                                                     height=40,
                                                     font=("Helvetica", 18))
        self.submit_button.pack(pady=10)

        self.select_unit_to_download_header = customtkinter.CTkLabel(self, text=self.texts['select_unit_to_download_header'],
                                                    font=("Helvetica", 25))
        self.select_unit_to_download_header.pack(pady=10)

        recipe_struct_mapping = {2: "Master & SMC1 & SMC2", 4: "Master & SMC1", 5: "Master & SMC2"}
        id_mapping = {}

        self.treeview_select_structure = ttk.Treeview(self,selectmode="browse", style="Treeview")
        self.treeview_select_structure.pack()
        self.treeview_select_structure["columns"] = ("id", "Structure name")

        self.treeview_select_structure.column("#0", width=0, stretch=False)
        self.treeview_select_structure.column("id", width=0, stretch=False)
        self.treeview_select_structure.column("Structure name", width=300, stretch=False)

        self.treeview_select_structure.heading("#0", text="", anchor="w")
        self.treeview_select_structure.heading("id", text="Structure", anchor="w")
        self.treeview_select_structure.heading("Structure name", text=self.texts["treeview_select_structure_name"], anchor="w")

        cursor, cnxn = get_database_connection()
        try:
            cursor.execute('SELECT TOP (1000) [id], [RecipeStructureName] FROM [RecipeDB].[dbo].[viewRecipeStructures]')
        except Exception as exeption:
            logger.error(f"Error while executing SELECT TOP: {exeption}")
            return

        rows = cursor.fetchall()

        cursor.close()
        cnxn.close()

        for row in rows:
            recipe_id, RecipeStructureName = row
            item_id = self.treeview_select_structure.insert("", "end", values=(recipe_id, RecipeStructureName))
            if RecipeStructureName in recipe_struct_mapping.values():
                # If the name of this items structure is in the mapping, store the recipe_struct -> item id pair
                recipe_struct_for_this_item = next(key for key, value in recipe_struct_mapping.items() if value == RecipeStructureName)
                id_mapping[recipe_struct_for_this_item] = item_id

        try:
            mapped_id = id_mapping[recipe_struct]
            self.treeview_select_structure.selection_set(mapped_id)
        except KeyError:
            logger.info(f"Error: No mapping for recipe_struct value {recipe_struct}")

        # Binds a event where user selects something on the datagrid
        self.treeview_select_structure.bind('<<TreeviewSelect>>')


    def check_struct(self):
        """
        Checks the structure of the modified step and submits the new recipe to the database.
        """
        try:
            selected_structure_item = self.treeview_select_structure.selection()[0]
            selected_structure_id = self.treeview_select_structure.item(selected_structure_item, "values")[0]
            logger.info(f'Selected structure ID: {selected_structure_id}')

            self.app_instance.update_recipe(self.name_entry.get(), self.comment_entry.get(),selected_structure_id)

            self.destroy()
        except IndexError:
            showinfo(title='Information', message=self.texts["select_unit_to_download_header"])
            logger.warning('No structure selected by user')
            self.focus_force()
            return


class Edit_steps_window(customtkinter.CTkToplevel):
    """Class for a pop up window to edit servo steps."""
    def __init__(self, master, rows, selected_id, texts, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.resizable(False, False)
        self.selected_id = selected_id
        self.rows = rows
        self.texts = texts
        self.title("Data editor")
        pop_up_width = 800
        pop_up_height = 900
        position_x = 900
        position_y = 400
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")

        self.search_var = customtkinter.StringVar()
        self.search_bar = customtkinter.CTkEntry(self, textvariable=self.search_var)
        self.search_bar.pack(anchor="nw", pady=10, padx=10)
        self.search_var.trace('w', self.update_treeview)


        self.edit_recipe_grid(selected_id)

    def edit_recipe_grid(self,selected_id):
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
            #tag_value = round(float(tag_value), 3) # Sometimes the float point is very long
            self.edit_recipe_treeview.insert("", "end", values=(unit_name, tag_name, tag_value, unit_id))

        #self.edit_recipe_treeview.bind("<Double-1>", lambda event: self.on_double_click(event, unit_id, selected_id))
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

        edit_dialog = customtkinter.CTkToplevel(self)
        edit_dialog.title("Edit TagValue")
        edit_dialog.geometry("200x100")

        label = customtkinter.CTkLabel(edit_dialog, text="Tag värde:")
        label.pack()

        entry = customtkinter.CTkEntry(edit_dialog)
        entry.pack()
        entry.insert(0, tag_value)


        def save_changes():
            edited_tag_value = entry.get()
            self.edit_recipe_treeview.item(selected_item, values=(self.edit_recipe_treeview.item(selected_item)['values'][0],
                                                                  tag_name, edited_tag_value,unit_id))
            edit_dialog.destroy()

            stored_procedure_name = 'update_value'
            recipe_id_param_name = "RecipeID"
            unit_id_param_name = "UnitID"
            tag_name_param_name = 'TagName'
            tag_value_param_name = 'TagValue'

            cursor, cnxn = get_database_connection()

            try:
                cursor.execute(f"EXEC {stored_procedure_name} \
                        @{tag_name_param_name}='{tag_name}', \
                        @{tag_value_param_name}={edited_tag_value}, \
                        @{recipe_id_param_name}={self.selected_id},\
                        @{unit_id_param_name}={unit_id};")
            except Exception as exeption:
                logger.error(exeption)

            cnxn.commit()

            cursor.close()
            cnxn.close()

        save_button = customtkinter.CTkButton(edit_dialog, text="Spara", command=save_changes)
        save_button.pack()


class App(customtkinter.CTk):
    """Class for the main app"""

    def __init__(self, async_queue: Queue, *args, **kwargs):
        """
        Initializes an instance of the App class. It sets up the application's appearance,
        title, geometry, and default pages.
        """

        super().__init__(*args, **kwargs)

        customtkinter.set_appearance_mode("light")

        self.opcua_alarms = False
        self.selected_recipe_row_values = None
        self.units = None
        self.about_window = None
        self.edit_steps_window = None
        self.make_recipe_window = None
        self.edit_recipe_window = None
        self.language_button = None
        self.check_if_units_alive = None
        self.ip_adresses_treeview = None
        self.treeview = None
        self.make_recipe_button = None
        self.update_submit_button = None
        self.load_data_in_selected_recipe_button = None
        self.use_selected_recipe_button = None
        self.edit_selected_recipe_button = None
        self.delete_selected_row_button = None
        self.achnowledge_alarm_button = None
        self.opcua_error_treeview = None
        self.logs_treeview = None
        self.add_error = None
        self.refresh_log_screen = None
        self.opcua_treeview = None

        self.pages = {}

        self.language = 'swedish'
        self.texts = self.load_language_file(self.language)

        # Assets for the GUI
        root_path = Path(__file__).parent.parent
        self.assets_path = root_path / "static/Assets"

        self.geometry("2560x1440")

        self.async_queue: Queue = async_queue

        #self.attributes("-fullscreen", True)

        self.title("LMT recept hantering")

        self.container = customtkinter.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Treeview", font=("Helvetica", 12))

        self.focus_force()

        self.recipe_page_command()

    def create_header(self, parent, page_name, opcua_alarms):
        """
        Creates and returns a header frame for a given page.

        Parameters:
        parent (CTkFrame): Parent frame where the header frame is to be placed.
        page_name (str): The name of the page to be displayed in the header.
        opcua_alarms (bool): Flag indicating if there are any OPCUA alarms.
        """

        logo_image_path = (self.assets_path / "LMT-logo.png")
        logo_image = Image.open(logo_image_path)
        bg_frame = customtkinter.CTkFrame(parent, fg_color="lightgray", height=70)
        bg_frame.pack(side="top", fill="x")
        bg_frame.pack_propagate(False)

        logo_frame = customtkinter.CTkFrame(bg_frame, width=160, height=40, fg_color="lightgray")
        logo_frame.place(x=1, y=10)
        logo_image = CTkImage(logo_image, size=(200, 40))
        logo_label = customtkinter.CTkLabel(logo_frame, image=logo_image, text="")
        logo_label.pack(side="top", anchor="nw", padx=10, pady=10)

        page_head_label = customtkinter.CTkLabel(bg_frame, text=page_name, font=("Helvetica", 50))
        page_head_label.pack(side="top", pady=5)

        self.language_button = customtkinter.CTkButton(self, text=f"Change language ({self.language})", command=self.change_language,
                                                       width=170,
                                                       height=40)
        self.language_button.place(x=2370, y=15)

        return bg_frame


    def check_alive_units(self):
        """
        Pings the nearby units and updates the Treeview widget with the status.
        """

        for item in self.ip_adresses_treeview.get_children():
            self.ip_adresses_treeview.delete(item)

        ip_status_list = check_ip()
        for name, ip_address, status in ip_status_list:
            self.ip_adresses_treeview.insert('', 'end', values=(name, ip_address, status))


    def main_page(self):
        """Main page where the user can check if units nearby is alive"""

        main_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["main_page"] = main_page
        main_page.grid(row=0, column=0, sticky="nsew")
        self.check_if_units_alive = customtkinter.CTkButton(main_page,
                                                            text=self.texts['check_alive'],
                                                            command=self.check_alive_units,
                                                            width=200,height=50)

        self.check_if_units_alive.place(x=10, y=180)

        self.ip_adresses_treeview = ttk.Treeview(main_page, columns=("Name", "Ip adress", "Alive"),
                                      show="headings", height=10,style="Treeview", selectmode="none")

        self.ip_adresses_treeview.heading("Name", text=self.texts['ip_datagrid_name'])
        self.ip_adresses_treeview.heading("Ip adress", text=self.texts['ip_datagrid_ip'])
        self.ip_adresses_treeview.heading("Alive", text=self.texts['ip_datagrid_alive'])

        self.ip_adresses_treeview.column("Name", width=100)
        self.ip_adresses_treeview.column("Ip adress", width=200)
        self.ip_adresses_treeview.column("Alive", width=120)

        self.ip_adresses_treeview.place(x=220, y=100)

        self.create_header(main_page, self.texts['header_main_menu'], self.opcua_alarms)
        self.create_meny_buttons(main_page)


    def recipes_page(self):
        """
        Creates and displays the recipes page.
        This page allows the user to create, update, and use recipes.
        """

        recipes_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["recipes_page"] = recipes_page
        recipes_page.grid(row=0, column=0, sticky="nsew")

        self.create_header(recipes_page, self.texts['header_recipe'], self.opcua_alarms)
        self.create_meny_buttons(recipes_page)

        self.treeview = ttk.Treeview(recipes_page,selectmode="browse", style="Treeview")
        self.treeview.pack(expand=True, fill='both', side="left")
        self.treeview["columns"] = ("id", "RecipeName", "RecipeComment",
                                    "RecipeCreated", "RecipeUpdated", "RecipeStatus")

        self.treeview.column("#0", width=0, stretch=False)
        self.treeview.column("id", width=0, stretch=False)
        self.treeview.column("RecipeName", width=700, stretch=False)
        self.treeview.column("RecipeComment", width=700, stretch=False)
        self.treeview.column("RecipeCreated", width=300, stretch=False)
        self.treeview.column("RecipeUpdated", width=200, stretch=False)
        self.treeview.column("RecipeStatus", width=90, stretch=False)

        self.treeview.heading("#0", text="", anchor="w")
        self.treeview.heading("id", text="id", anchor="w")
        self.treeview.heading("RecipeName", text=self.texts['recipe_datagrid_name'], anchor="w")
        self.treeview.heading("RecipeComment", text=self.texts['recipe_datagrid_comment'], anchor="w")
        self.treeview.heading("RecipeCreated", text=self.texts['recipe_datagrid_created'], anchor="w")
        self.treeview.heading("RecipeUpdated", text=self.texts['recipe_datagrid_modified'], anchor="w")
        self.treeview.heading("RecipeStatus", text=self.texts['recipe_datagrid_status'], anchor="w")

        right_frame = customtkinter.CTkFrame(recipes_page, fg_color="white")
        right_frame.pack(side='right', fill='y', expand=True)

        self.make_recipe_button = customtkinter.CTkButton(right_frame,
                                                    text=self.texts['make_a_recipe'],
                                                    command=self.open_make_recipe_window,
                                                    width=350,
                                                    height=60,
                                                    font=("Helvetica", 18))
        self.make_recipe_button.pack(pady=10)


        self.update_submit_button = customtkinter.CTkButton(right_frame, text=self.texts['update_recipe_submit'],
                                                            command=self.open_update_recipe_window,
                                                            width=350,
                                                            height=60,
                                                            font=("Helvetica", 18))
        self.update_submit_button.pack(pady=10)


        self.load_data_in_selected_recipe_button = customtkinter.CTkButton(right_frame,
                                                                           text=self.texts['load_servo_steps_into_selected_recipe_button'],
                                                                           command=self.load_data_in_selected_recipe,
                                                                           width=350,
                                                                           height=45,
                                                                           font=("Helvetica", 18))

        self.load_data_in_selected_recipe_button.pack(pady=(60,0))

        self.use_selected_recipe_button = customtkinter.CTkButton(right_frame, text=self.texts["use_the_selected_recipe_button"],
                                                                   command=self.use_selected_recipe,
                                                                   width=350,
                                                                   height=45,
                                                                   font=("Helvetica", 18))
        self.use_selected_recipe_button.pack(pady=(15,0))

        self.edit_selected_recipe_button = customtkinter.CTkButton(right_frame, text=self.texts["edit_the_selected_recipe_button"],
                                                                  command=self.edit_recipe,
                                                                  width=350,
                                                                  height=45,
                                                                  font=("Helvetica", 18))
        self.edit_selected_recipe_button.pack(pady=(15,0))

        self.delete_selected_row_button = customtkinter.CTkButton(right_frame, text=self.texts["delete_the_selected_recipe_button"],
                                                                  command=self.delete_recipe,
                                                                  width=350,
                                                                  height=45,
                                                                  font=("Helvetica", 18))
        self.delete_selected_row_button.pack(pady=(15,0))

        #self.edit_selected_recipe_button = customtkinter.CTkButton(right_frame, text=self.texts["archive_the_selected_recipe_button"],
        #                                                          command=self.archive_selected_recipe,
        #                                                          width=350,
        #                                                          height=45,
        #                                                          font=("Helvetica", 18))
        #self.edit_selected_recipe_button.pack(pady=(15,0))

        # Getting the data from SQL and putting it in the datagrid
        cursor, cnxn = get_database_connection()

        if cursor and cnxn:
            logger.info("Database connection established")
        else:
            logger.error("Failed to establish a database connection")
            showinfo(title="Info", message=self.texts["error_with_database"])
            return
        try:
            cursor.execute('SELECT TOP (1000) [id], [RecipeName], [RecipeComment], [RecipeCreated], \
                            [RecipeUpdated] FROM [RecipeDB].[dbo].[viewRecipesActive]')
        except Exception as exeption:
            logger.error(f"Error while executing SELECT TOP: {exeption}")
            return

        rows = cursor.fetchall()

        cursor.close()
        cnxn.close()

        for row in rows:
            recipe_id, RecipeName, RecipeComment, RecipeCreated, RecipeUpdated = row
            has_recipe_data = (check_recipe_data(recipe_id))
            status_text = 'Ja' if has_recipe_data else 'Nej'
            self.treeview.insert("", "end", values=(recipe_id, RecipeName, RecipeComment,
                                                    RecipeCreated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    RecipeUpdated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    status_text))

        # Binds a event where user selects something on the datagrid
        self.treeview.bind('<<TreeviewSelect>>')


    def alarm_page(self):
        """Alarm page where the user can see alarms from opcua servers"""

        alarms_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["alarms_page"] = alarms_page
        alarms_page.grid(row=0, column=0, sticky="nsew")
        self.create_meny_buttons(alarms_page)
        self.create_header(alarms_page, self.texts['header_alarms'], self.opcua_alarms)
        self.achnowledge_alarm_button = customtkinter.CTkButton(alarms_page,
                                                          text=self.texts["acknowledge_the_selected_alarm_button"],
                                                          command=self.achnowledge_alarm,
                                                          width=200,height=50)

        self.achnowledge_alarm_button.place(x=1850, y=100)
        self.opcua_error_treeview = self.create_opcua_error_treeview(alarms_page)


    def logs_page(self):
        """Logs page where the user can see different info/error logs"""

        logs_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["logs_page"] = logs_page
        logs_page.grid(row=0, column=0, sticky="nsew")
        self.create_meny_buttons(logs_page)
        self.create_header(logs_page, self.texts['header_logs'], self.opcua_alarms)
        self.logs_treeview, self.add_error = self.create_logs_treeview(logs_page)
        self.refresh_log_screen = customtkinter.CTkButton(logs_page,
                                                          text=self.texts["refresh_the_logs_button"],
                                                          command=self.add_error,
                                                          width=200,height=50)

        self.refresh_log_screen.place(x=2200, y=100)


    def load_language_file(self, language):
        with open(f'language/{language}.json', 'r', encoding='utf-8') as file:
            return json.load(file)


    def change_language(self):
        self.language = 'swedish' if self.language == 'english' else 'english'
        self.texts = self.load_language_file(self.language)
        self.language_button.configure(text=f"Change language ({self.language})")
        self.main_page()
        self.show_page("main_page")


    def create_opcua_error_treeview(self,parent):
        """Makes a datagid to see the errors from the units"""

        self.opcua_treeview = ttk.Treeview(parent, columns=("date", "severity", "message", "acknowledged state", "identifier"),
                                      show="headings", height=10, style="Treeview")

        self.opcua_treeview.heading("#0", text="", anchor="w")
        self.opcua_treeview.heading("date", text=self.texts["alarm_datagrid_date"],anchor="w")
        self.opcua_treeview.heading("severity", text=self.texts["alarm_datagrid_Severity"],anchor="w")
        self.opcua_treeview.heading("message", text=self.texts["alarm_datagrid_message"],anchor="w")
        self.opcua_treeview.heading("acknowledged state", text=self.texts["alarm_datagrid_ack_state"],anchor="w")
        self.opcua_treeview.heading("identifier", text=self.texts["alarm_datagrid_identifier"],anchor="w")

        self.opcua_treeview.column("#0", width=0, stretch=False)
        self.opcua_treeview.column("date", width=200, stretch=False)
        self.opcua_treeview.column("severity", width=150, stretch=False)
        self.opcua_treeview.column("message", width=1100, stretch=False)
        self.opcua_treeview.column("acknowledged state", width=150, stretch=False)
        self.opcua_treeview.column("identifier", width=150, stretch=False)

        self.opcua_treeview.pack(padx=10, pady=10, expand=True, fill="y",anchor="w")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.opcua_treeview.yview)
        vsb.place(x=30+1750+2, y=95, height=1240+20)

        self.opcua_treeview.configure(yscrollcommand=vsb.set)


        def add_opcua_alarm_to_datagrid(log_folder="alarms"):
            """Adds alarms to the opcua datagrid"""

            for item in self.opcua_treeview.get_children():
                self.opcua_treeview.delete(item)

            log_files = [file for file in os.listdir(log_folder) if file.endswith(".log")]

            for log_file in log_files:
                with open(os.path.join(log_folder, log_file), "r") as file:
                    state = None
                    message = None
                    time_str = None
                    for line in file:
                        line = line.strip()
                        if line:
                            if "Message:" in line:
                                message_start = line.find("Message:")
                                message_full = line[message_start:].split("Message:", 1)[1].strip()
                                # Extract the content after 'Text='
                                message = message_full.split("Text=", 1)[1].strip()
                            elif "Time:" in line:
                                time_start = line.find("Time:")
                                time_str_full = line[time_start:].split("Time:", 1)[1].strip()
                                # Convert time string to datetime object and remove microseconds
                                time_obj = datetime.fromisoformat(time_str_full)
                                time_str = time_obj.strftime("%Y-%m-%d %H:%M:%S")
                            elif "State:" in line:
                                state_start = line.find("State:")
                                state = line[state_start:].split("State:", 1)[1].strip()

                        if message and time_str and state:
                            if state.lower() == "true":
                                self.opcua_treeview.insert("", "end", values=(time_str, message))
                            # Reset values for the next set of message, time, and state
                            state = None
                            message = None
                            time_str = None


        return self.opcua_treeview, add_opcua_alarm_to_datagrid


    def create_logs_treeview(self, parent):
        """Makes a datagrid to see the errors from example
        OPCUA, SQL or programming errors"""

        logs_treeview = ttk.Treeview(parent, columns=("Date", "Severity", "File", "Message"),
                                    show="headings", height=10, style="Treeview")

        logs_treeview.heading("#0", text="", anchor="w")
        logs_treeview.heading("Date", text=self.texts["log_datagrid_date"],anchor="w")
        logs_treeview.heading("Severity", text=self.texts["log_datagrid_Severity"],anchor="w")
        logs_treeview.heading("File", text=self.texts["log_datagrid_file"],anchor="w")
        logs_treeview.heading("Message", text=self.texts["log_datagrid_message"],anchor="w")

        logs_treeview.column("#0", width=0, stretch=False)
        logs_treeview.column("Date", width=200, stretch=False)
        logs_treeview.column("Severity", width=100, stretch=False)
        logs_treeview.column("File", width=120, stretch=False)
        logs_treeview.column("Message", width=1700, stretch=False)

        logs_treeview.pack(padx=10, pady=10, expand=True, fill="y",anchor="w")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=logs_treeview.yview)
        vsb.place(x=30+2110+2, y=95, height=1170+20)

        logs_treeview.configure(yscrollcommand=vsb.set)


        def add_logs_to_datagrid(log_folder="logs"):
            """Adds the info/errors from the logs to the log datagrid"""

            for item in self.logs_treeview.get_children():
                self.logs_treeview.delete(item)

            log_files = [file for file in os.listdir(log_folder) if file.endswith(".log")]

            for log_file in log_files:
                with open(os.path.join(log_folder, log_file), "r") as file:
                    for line in file:
                        line = line.strip()
                        if line:
                            error = line.split("|", 3)
                            logs_treeview.insert("", "end", values=error)

        return logs_treeview, add_logs_to_datagrid

    async def achnowledge_alarm(self):
        from .opcua_client import connect_opcua

        selected_item = self.opcua_treeview.selection()[0]
        selected_id = self.treeview.item(selected_item, 'values')[0]

        client = await connect_opcua(url=url)

        event_obj = client.get_node(selected_id)

        ack_result = await event_obj.call_method(ua.NodeId.from_string('i=9111'), ua.Variant(selected_id), ua.Variant("Acknowledged by operator"))

        print(f"Acknowledge result: {ack_result}")


    def load_data_in_selected_recipe(self):
        """Called with a button takes the servo steps from OPCUA server and
        puts them into the selected recipe in the SQL"""

        try:

            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]

        except IndexError:
            showinfo(title="Information", message=self.texts["no_recipe_to_load_data_into"])

        cursor, cnxn = get_database_connection()
        try:
            query = "SELECT RecipeStructID FROM tblRecipe WHERE id = ?"
            cursor.execute(query, (selected_id,))
            rows = cursor.fetchall()
            for row in rows:
                recipe_structure_id = row[0]

        except Exception as exeption:
            logger.error(f"Error while executing SELECT TOP: {exeption}")
            return

        if selected_id:

            self.units = self.async_queue.put(from_units_to_sql_stepdata(selected_id, self.texts,recipe_structure_id))
            recipe_checked = self.async_queue.put(check_recipe_data(selected_id))

            if recipe_checked:
                current_values = list(self.treeview.item(selected_item, 'values'))
                current_values[5] = "Ja"
                self.treeview.item(selected_item, values=current_values)
                logger.info(f"Data loaded successfully for selected recipe ID: {selected_id}")

            else:
                logger.error(f"Error while loading data for selected recipe ID: {selected_id}")
        else:
            showinfo(title="Information", message=self.texts["no_recipe_to_load_data_into"])
            return

    def archive_selected_recipe(self):
        """archive the seleected recipe"""
        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_archive_selected_recipe_error"])
            return

        cursor, cnxn = get_database_connection()

        try:
            cursor.execute("EXEC [RecipeDB].[dbo].[archive_recipe] @RecipeID=?", selected_id)
            cnxn.commit()
            cursor.execute('SELECT TOP (1000) [id], [RecipeName], [RecipeComment], \
                [RecipeCreated], [RecipeUpdated] \
                FROM [RecipeDB].[dbo].[viewRecipesActive]')

            rows = cursor.fetchall()

            for item in self.treeview.get_children():
                self.treeview.delete(item)

            for row in rows:
                recipe_id, RecipeName, RecipeComment, RecipeCreated, RecipeUpdated = row
                self.treeview.insert("", "end", values=(recipe_id, RecipeName, RecipeComment,
                                                        RecipeCreated.strftime("%Y-%m-%d %H:%M:%S"),
                                                        RecipeUpdated.strftime("%Y-%m-%d %H:%M:%S")))
        except Exception as exeption:
            logger.error(f"Error while executing update_recipe: {exeption}")
            return

        finally:
            cursor.close()
            cnxn.close()


    def use_selected_recipe(self):
        """Puts the selected recipe in the units stepdata"""

        selected_item = self.treeview.selection()[0]
        selected_id = self.treeview.item(selected_item, 'values')[0]
        selected_name = self.treeview.item(selected_item, 'values')[1]

        cursor, cnxn = get_database_connection()
        step_query = "SELECT * FROM ViewValues WHERE RecipeID = ?"
        cursor.execute(step_query, (selected_id,))
        step_data = cursor.fetchall()

        query = "UPDATE tblActiveRecipeList SET ActiveRecipeName = ?"
        cursor.execute(query, (selected_name,))
        cnxn.commit()

        if step_data:
            self.units = self.async_queue.put(from_sql_to_units_stepdata(step_data,self.texts, selected_name))
            logger.info(f"Successfully updated the active recipe to: {selected_name}")

        else:
            showinfo(title='Information', message=self.texts["show_info_use_selected_recipe_error"])
            return

        cnxn.commit()
        cnxn.close()


    def delete_recipe(self):
        """Called with a button delete a recipe from the datagrid and the SQL"""

        selected_item = self.treeview.selection()[0]
        selected_id = self.treeview.item(selected_item, 'values')[0]
        cursor, cnxn = get_database_connection()

        try:
            cursor.execute("DELETE FROM [RecipeDB].[dbo].[tblRecipe] WHERE id = ?", (selected_id,))
            cnxn.commit()
            self.treeview.delete(selected_item)

        except pyodbc.Error as exeption:
            logger.error(f"Error while deleting recipe: {exeption}")
            return

        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_submit_new_recipe_error"])

    def submit_new_recipe(self, name, comment, selected_structure_id):
        """Called with a button adds a new recipe to the datagrid and SQL"""

        logger.info(f"Submitting new recipe: Name: {name}, Comment: {comment}, Structure ID: {selected_structure_id}")

        if not name or not selected_structure_id:
            showinfo(title='Information', message=self.texts["show_info_submit_new_recipe_error"])
            return
        cursor, cnxn = get_database_connection()

        try:
            cursor.execute("""
                SELECT [RecipeName]
                FROM [RecipeDB].[dbo].[viewRecipesActive]
                WHERE [RecipeName] = ?
                """, (name,))
            result = cursor.fetchone()
            if result:
                showinfo(title='Information', message=self.texts['This_recipe_name_already_exists.'])
                return

            cursor.execute("""
                EXEC [RecipeDB].[dbo].[new_recipe]
                @RecipeName=?,
                @RecipeComment=?,
                @RecipeStructID=?
            """, name, comment, selected_structure_id)
            cnxn.commit()
            cursor.execute("""
                SELECT TOP (1000) [id], [RecipeName], [RecipeComment],
                [RecipeCreated], [RecipeUpdated]
                FROM [RecipeDB].[dbo].[viewRecipesActive]""")

        except Exception as exeption:
            logger.error(f"Error while executing update_recipe: {exeption}")
            return

        rows = cursor.fetchall()

        for row in self.treeview.get_children():
            self.treeview.delete(row)

        for row in rows:
            recipe_id, RecipeName, RecipeComment, RecipeCreated, RecipeUpdated = row
            has_recipe_data = (check_recipe_data(recipe_id))
            status_text = 'Ja' if has_recipe_data else 'Nej'
            self.treeview.insert("", "end", values=(recipe_id, RecipeName, RecipeComment,
                                                    RecipeCreated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    RecipeUpdated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    status_text))

        logger.info("Successfully submitted the new recipe and refreshed the view.")


    def update_recipe(self, name, comment, selected_structure_id):
        """Called with a button to update servo steps or name of a recipe"""


        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
            logger.info(f"Updating recipe: ID: {selected_id}, Name: {name}, Comment: {comment}, Structure ID: {selected_structure_id}")

        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_update_recipe_error"])
            return

        if not name:
            showinfo(title='Information', message=self.texts["show_info_update_recipe_name_empty"])
            return
        cursor, cnxn = get_database_connection()
        try:
            cursor.execute("EXEC [RecipeDB].[dbo].[update_recipe] @RecipeID=?, @RecipeName=?, @RecipeComment=?, @RecipeStructID=?",
                           selected_id, name, comment, selected_structure_id)
            cnxn.commit()

            cursor.execute('SELECT TOP (1000) [id], [RecipeName], [RecipeComment], \
                [RecipeCreated], [RecipeUpdated] \
                FROM [RecipeDB].[dbo].[viewRecipesActive]')

        except Exception as exeption:
            logger.error(f"Error while executing update_recipe: {exeption}")

        rows = cursor.fetchall()

        if rows:
            logger.info(f"Successfully updated the recipe ID: {selected_id} and refreshed the view.")
        else:
            logger.warning(f"Recipe update was successful, but no rows were retrieved afterward for ID: {selected_id}")
            return

        for row in self.treeview.get_children():
            self.treeview.delete(row)

        for row in rows:
            recipe_id, RecipeName, RecipeComment, RecipeCreated, RecipeUpdated = row
            has_recipe_data = (check_recipe_data(recipe_id))
            status_text = 'Ja' if has_recipe_data else 'Nej'
            self.treeview.insert("", "end", values=(recipe_id, RecipeName, RecipeComment,
                                                    RecipeCreated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    RecipeUpdated.strftime("%Y-%m-%d %H:%M:%S"),
                                                    status_text))


    def edit_recipe(self):
        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
            cursor, cnxn = get_database_connection()
        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_edit_recipe_no_selected"])

        try:

            query = """
            SELECT TOP (1000) [UnitID], [TagName], [TagValue], [TagDataType], [UnitName]
            FROM [RecipeDB].[dbo].[viewValues]
            WHERE RecipeID = ?
            ORDER BY RecipeID, UnitID,
                CASE WHEN CHARINDEX('[', TagName) > 0 AND CHARINDEX(']', TagName) > CHARINDEX('[', TagName)
                     THEN CAST(SUBSTRING(TagName, CHARINDEX('[', TagName) + 1, CHARINDEX(']', TagName) - CHARINDEX('[', TagName) - 1) AS INT)
                END,
                TagName
            """
            params = (selected_id,)
            cursor.execute(query, params)

            rows = cursor.fetchall()
            if rows:
                logger.info(f"Fetched {len(rows)} rows for editing recipe ID: {selected_id}")
                self.open_edit_steps_window(rows,selected_id)
            else:
                logger.warning(f"No data found for editing recipe ID: {selected_id}")
                showinfo(title='Information', message=self.texts["show_info_edit_recipe_no_data"])
                return

        except Exception as exeption:
            logger.error(f"Error while executing SELECT TOP: {exeption}")
            return


    def create_meny_buttons(self, parent):
        """Creates the navigation buttons at the bottom of the application window"""

        button_frame = customtkinter.CTkFrame(parent,fg_color="white")
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)

        button1 = customtkinter.CTkButton(button_frame, width=200, height=45, text=self.texts['main_button'],
                                          command=self.main_page_command)
        button1.pack(side='left', padx=5)

        button2 = customtkinter.CTkButton(button_frame, width=200, height=45, text=self.texts['recipe_button'],
                                          command=self.recipe_page_command)
        button2.pack(side='left', padx=5)

        button3 = customtkinter.CTkButton(button_frame, width=200, height=45, text=self.texts['alams_button'],
                                          command=self.alarm_page_command)
        button3.pack(side='left', padx=5)

        button4 = customtkinter.CTkButton(button_frame, width=200, height=45, text=self.texts['logs_button'],
                                          command=self.logs_page_command)
        button4.pack(side='left', padx=5)

        button5 = customtkinter.CTkButton(button_frame, width=200, height=45, text=self.texts['about_button'],
                                          command=self.about_page_command)
        button5.pack(side='left', padx=5)


    def show_page(self, page_name):
        if page_name == "recipes_page" and page_name not in self.pages:
            self.recipes_page()
        page = self.pages[page_name]
        page.tkraise()


    def main_page_command(self):
        """Shows the main page"""
        self.main_page()
        self.show_page("main_page")


    def recipe_page_command(self):
        """Shows the recipe page"""
        self.recipes_page()
        self.show_page("recipes_page")


    def alarm_page_command(self):
        """Shows the alarm page"""
        self.alarm_page()
        self.show_page("alarms_page")
        #async_queue.put(monitor_alarms(self.add_opcua_alarm_to_datagrid_function))


    def logs_page_command(self):
        """Shows the log page"""
        self.logs_page()
        self.show_page("logs_page")


    def about_page_command(self):
        """Shows the about page"""
        self.open_about_window()


    def open_about_window(self):
        """Shows the about window"""
        if self.about_window is None or not self.about_window.winfo_exists():
            self.about_window = AboutWindow(self)
            self.about_window.focus()
            self.about_window.attributes('-topmost', True)
        else:
            self.about_window.focus()
        self.about_window.lift()


    def open_edit_steps_window(self, rows,selected_id):
        """Shows the edit recipe window"""

        if self.edit_steps_window is None or not self.edit_steps_window.winfo_exists():
            self.edit_steps_window = Edit_steps_window(self, rows, selected_id, self.texts)
            self.edit_steps_window.focus()
            self.edit_steps_window.attributes('-topmost', True)
        else:
            self.edit_steps_window.focus()
        self.edit_steps_window.lift()

    def open_make_recipe_window(self):
        "Shows the make a recipe window"

        if self.make_recipe_window is None or not self.make_recipe_window.winfo_exists():
            self.make_recipe_window = MakeRecipeWindow(self, self.texts)
            self.make_recipe_window.focus()
            #self.make_recipe_window.attributes('-topmost', True)
        else:
            self.make_recipe_window.focus()
        self.make_recipe_window.lift()


    def open_update_recipe_window(self):
        "Shows the make a recipe window"

        cursor, cnxn = get_database_connection()

        try:
            selected_id_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_id_item, 'values')[0]

            cursor.execute('SELECT TOP (1000) [RecipeName], [RecipeComment], [RecipeStructID] \
                           FROM [RecipeDB].[dbo].[tblRecipe] \
                           WHERE [id] = ?', (selected_id,))

            row = cursor.fetchall()

            for insert_good_var_name in row:
                recipeName, recipeComment, recipe_struct = insert_good_var_name

        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_update_recipe_error"])
            return

        if self.edit_recipe_window is None or not self.edit_recipe_window.winfo_exists():
            self.edit_recipe_window = Edit_recipe_window(self, self.texts, selected_id, recipeName, recipeComment, recipe_struct)
            self.edit_recipe_window.focus()
            #self.edit_recipe_window.attributes('-topmost', True)
        else:
            self.edit_recipe_window.focus()
        self.edit_recipe_window.lift()


def main():
    """Main func to start the program"""

    # Start the webserver
    main_webserver()

    # Start the tkinter app
    async_queue = Queue()
    async_thread = Thread(target=run_asyncio_loop, args=(async_queue,), daemon=True)
    async_thread.start()

    app = App(async_queue)
    app.mainloop()

    async_queue.put(None)
    async_thread.join()

    # Start the alarm monitor
    monitor_alarms_thread = Thread(target=run_monitor_alarms_loop, daemon=True)
    monitor_alarms_thread.start()
