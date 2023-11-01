# Python package
from pathlib import Path
from tkinter import ttk
from tkinter.messagebox import showinfo, askyesno
from datetime import datetime
import asyncio
from threading import Thread
from queue import Queue
import os
import webbrowser
import json
import markdown
import tkinter as tk

# Third party package
import customtkinter
from customtkinter import CTkImage
from PIL import Image
from pyodbc import Error as PyodbcError
from asyncua import ua, Client

# Own package
from .ms_sql import from_units_to_sql_stepdata, from_sql_to_units_stepdata, check_recipe_data
from .data_encrypt import DataEncryptor
from .create_log import setup_logger
from .ip_checker import check_ip
from .opcua_alarm import monitor_alarms
from .webserver import main_webserver
from .config_handler import ConfigHandler
from .sql_connection import SQLConnection

# Setup logger for gui.py
logger = setup_logger('Gui')


def run_monitor_alarms_loop():
    """Runs the monitor_alarms function in a loop."""

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        loop.create_task(monitor_alarms())

        loop.run_forever()
    finally:
        loop.stop()
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def run_asyncio_loop(queue:Queue, app_instance:"App"):
    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)
    try:
        while True:
            coro = queue.get()
            if coro is None:
                break
            task = loop.create_task(coro)
            app_instance.config(cursor="watch")
            loop.run_until_complete(task)
            app_instance.config(cursor="arrow")
            # Update the recipe page to refrtesh the data
            if "from_units_to_sql_stepdata" in str(task.get_coro()):
                app_instance.recipe_page_command()

    finally:
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()




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
        self.selected_recipe_menu = None
        self.language_button = None
        self.check_if_units_alive = None
        self.ip_adresses_treeview = None
        self.treeview = None
        self.logs_treeview = None
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

        #self.focus_force()

        self.recipe_page_command()


    def create_header(self, parent, page_name):
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


    def load_language_file(self, language):
        with open(f'language/{language}.json', 'r', encoding='utf-8') as file:
            return json.load(file)


    def change_language(self):
        if self.language_button is None:
            return

        self.language = 'swedish' if self.language == 'english' else 'english'
        self.texts = self.load_language_file(self.language)
        self.language_button.configure(text=f"Change language ({self.language})")
        self.main_page()
        self.show_page("main_page")


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

        self.create_header(main_page, self.texts['header_main_menu'])
        self.create_meny_buttons(main_page)


    def check_alive_units(self):
        """
        Pings the nearby units and updates the Treeview widget with the status.
        """
        if self.ip_adresses_treeview:
            for item in self.ip_adresses_treeview.get_children():
                self.ip_adresses_treeview.delete(item)

            ip_status_list = check_ip()
            for name, ip_address, status in ip_status_list:
                self.ip_adresses_treeview.insert('', 'end', values=(name, ip_address, status))
        else:
            logger.error("Error: No ip_adresses_treeview object")


    def recipes_page(self):
        """
        Creates and displays the recipes page.
        This page allows the user to create, update, and use recipes.
        """
        self.detached_items = []
        self.sorting_order = {}

        self.original_headings = {}

        recipes_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["recipes_page"] = recipes_page
        recipes_page.grid(row=0, column=0, sticky="nsew")

        self.create_header(recipes_page, self.texts['header_recipe'])
        self.create_meny_buttons(recipes_page)

        self.treeview = ttk.Treeview(recipes_page,selectmode="browse", style="Treeview")
        self.treeview.pack(expand=True, fill='both', side="left")
        self.treeview["columns"] = ("id", "RecipeName", "RecipeComment",
                                    "RecipeCreated", "RecipeUpdated","RecipeLastSaved", "RecipeStatus")

        self.treeview.column("#0", width=0, stretch=False)
        self.treeview.column("id", width=0, stretch=False)
        self.treeview.column("RecipeName", width=500, stretch=False)
        self.treeview.column("RecipeComment", width=600, stretch=False)
        self.treeview.column("RecipeCreated", width=200, stretch=False)
        self.treeview.column("RecipeUpdated", width=200, stretch=False)
        self.treeview.column("RecipeLastSaved", width=220, stretch=False)
        self.treeview.column("RecipeStatus", width=130, stretch=False)

        self.treeview.heading("#0", text="", anchor="w")
        self.treeview.heading("id", text="id", anchor="w")
        self.treeview.heading("RecipeName", text=self.texts['recipe_datagrid_name'], anchor="w")
        self.treeview.heading("RecipeComment", text=self.texts['recipe_datagrid_comment'], anchor="w")
        self.treeview.heading("RecipeCreated", text=self.texts['recipe_datagrid_created'], anchor="w")
        self.treeview.heading("RecipeUpdated", text=self.texts['recipe_datagrid_modified'], anchor="w")
        self.treeview.heading("RecipeLastSaved", text=self.texts['recipe_datagrid_last_saved'], anchor="w")
        self.treeview.heading("RecipeStatus", text=self.texts['recipe_datagrid_status'], anchor="w")

        for col in self.treeview["columns"]:
            self.original_headings[col] = self.treeview.heading(col, "text")


        for col in self.treeview["columns"]:
            self.treeview.heading(col, text=self.treeview.heading(col, "text").split()[0], command=lambda _col=col: self.sort_column(_col))

        self.treeview.tag_configure('hasChildren', background='lightgray')
        self.treeview.tag_configure('isChild', background='lightgray')

        # Treeview bindings
        self.treeview.bind('<ButtonRelease-1>', self.item_selected)
        self.treeview.bind("<Double-1>", self.open_selected_recipe_menu)

        vsb = ttk.Scrollbar(recipes_page, orient="vertical", command=self.treeview.yview)
        vsb.place(x=30+2000+2, y=80, height=1200+20)
        self.treeview.configure(yscrollcommand=vsb.set)

        #Style for the treeview
        style = ttk.Style()
        style.configure('Treeview', rowheight=30)
        style.configure("Treeview.Heading", font=('Helvetica', 14))

        right_frame = customtkinter.CTkFrame(recipes_page, fg_color="white")
        right_frame.pack(side='right', fill='y', expand=True)

        self.make_recipe_button = customtkinter.CTkButton(right_frame,
                                                    text=self.texts['make_a_recipe'],
                                                    command=self.open_make_recipe_window,
                                                    width=350,
                                                    height=60,
                                                    font=("Helvetica", 22))
        self.make_recipe_button.pack(pady=20)

        self.search_label = customtkinter.CTkLabel(right_frame, text=self.texts['search_recipe'], font=("Helvetica", 20))
        self.search_label.pack(pady=5)

        self.search_var = customtkinter.StringVar()
        self.search_bar = customtkinter.CTkEntry(right_frame, textvariable=self.search_var, width=250, height=40)
        self.search_bar.pack(pady=1)
        self.search_var.trace('w', self.update_treeview)

        cursor = None
        cnxn = None
        rows = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:

                cursor.execute('SELECT [id], [RecipeName], [RecipeComment], [RecipeCreated], \
                                    [RecipeUpdated], [RecipeLastDataSaved],[ParentID] FROM [RecipeDB].[dbo].[viewRecipesActive]')

                rows = cursor.fetchall()

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)


        #  Gets the max depth of the recipe structure from the config file
        try:
            recipes_page_config = ConfigHandler()
            recipe_config_data = recipes_page_config.get_config_data("gui_config.json")
            self.max_child_depth = int(recipe_config_data["max_child_struct_recipe_grid"])
        except FileNotFoundError:
            logger.error("Config file not found.")
        except KeyError:
            logger.error("Key not found in config.")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

        parent_items = {}

        # Start inserting into Treeview from root (None)
        self.insert_into_treeview(None, rows, parent_items)


    def update_treeview(self, *args):
        search_term = self.search_var.get().lower()

        # Combine all items: attached and detached
        all_items = self.treeview.get_children("") + tuple(self.detached_items)

        if not search_term:
            # If the search bar is cleared, reattach all items
            for item in self.detached_items:
                self.treeview.move(item, '', 'end')
            self.detached_items.clear()
            return

        # Iterate through all items
        for item in all_items:
            RecipeName = self.treeview.item(item, "values")[1]

            # Check if the search term is in the RecipeName
            if search_term in RecipeName.lower():
                # If the item is detached, reattach it
                if item in self.detached_items:
                    self.treeview.move(item, '', 'end')
                    self.detached_items.remove(item)
            else:
                # If the item is attached, detach it
                if item not in self.detached_items:
                    self.treeview.detach(item)
                    self.detached_items.append(item)


    def sort_column(self, col):
        """
        Sort tree contents when a column heading is clicked.
        """
        # Toggle between ascending and descending
        order = "asc" if self.sorting_order.get(col, "desc") == "desc" else "desc"
        self.sorting_order[col] = order

        # Get all items in the tree
        items = self.treeview.get_children("")

        # Sort items based on the selected column and order
        sorted_items = sorted(items, key=lambda item: self.treeview.set(item, col), reverse=(order == "desc"))

        # Rearrange items in the treeview
        for index, item in enumerate(sorted_items):
            self.treeview.move(item, "", index)

        # Reset all column headings to their original state
        for _col in self.treeview["columns"]:
            self.treeview.heading(_col, text=self.original_headings[_col])

        # Update the sorted column heading to include the sorting arrow
        arrow = '↑' if order == "asc" else '↓'
        self.treeview.heading(col, text=f"{self.original_headings[col]} {arrow}")


    def insert_into_treeview(self,parent_item, rows, parent_items, depth=0):
        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        if depth >= self.max_child_depth:
            return

        if rows:
            for row in rows:
                recipe_id, RecipeName, RecipeComment, RecipeCreated, RecipeUpdated, recipe_last_saved, parent_id = row
                if parent_id == parent_item:
                    RecipeName = "          " * depth + RecipeName  # Indentation to reflect nesting
                    has_children = self.check_has_children(recipe_id, cursor, cnxn)
                    has_recipe_data = check_recipe_data(recipe_id)
                    status_text = '✓' if has_recipe_data else 'Tomt'

                    if recipe_last_saved is None:
                        recipe_last_saved = ""
                    else:
                        recipe_last_saved = recipe_last_saved.strftime("%Y-%m-%d %H:%M")

                    item = self.treeview.insert(parent_items.get(parent_id, ""), "end", iid=recipe_id, values=(recipe_id, RecipeName, RecipeComment,
                                                          RecipeCreated.strftime("%Y-%m-%d %H:%M"),
                                                          RecipeUpdated.strftime("%Y-%m-%d %H:%M"),
                                                          recipe_last_saved,
                                                          status_text))

                    # If the recipe has children, change its background color
                    if has_children:
                        self.treeview.item(item, tags=('hasChildren',))

                    # If the recipe is a child, change its background color
                    if parent_item is not None:
                        self.treeview.item(item, tags=('isChild',))

                    parent_items[recipe_id] = item

                    self.insert_into_treeview(recipe_id, rows, parent_items, depth + 1)

        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)


    def check_has_children(self, recipe_id, cursor, cnxn):
        """
        Checks if a recipe has any children.
        """
        if not cursor or not cnxn:
            showinfo(title="Info", message=self.texts["error_with_database"])
            return False

        try:
            cursor.execute('SELECT COUNT(*) FROM tblRecipe WHERE ParentID = ?', (recipe_id,))
            result = cursor.fetchone()
            return result and result[0] > 0

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])
            return False


    def item_selected(self,event):
        try:
            selected_item = self.treeview.selection()[0]
            if self.treeview.item(selected_item, "open"):
                self.treeview.item(selected_item, open=False)
            else:
                self.treeview.item(selected_item, open=True)
        except IndexError:
            pass


    def alarm_page(self):
        """Alarm page where the user can see alarms from opcua servers"""

        alarms_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["alarms_page"] = alarms_page
        alarms_page.grid(row=0, column=0, sticky="nsew")
        self.create_meny_buttons(alarms_page)
        self.create_header(alarms_page, self.texts['header_alarms'])
        self.achnowledge_alarm_button = customtkinter.CTkButton(alarms_page,
                                                          text=self.texts["acknowledge_the_selected_alarm_button"],
                                                          command=self.sync_acknowledge_alarm,
                                                          width=250,height=60,
                                                          font=("Helvetica", 18))

        self.achnowledge_alarm_button.place(x=2200, y=100)

        self.create_opcua_error_treeview(alarms_page)


    def create_opcua_error_treeview(self,parent):
        """Makes a datagid to see the errors from the units"""

        self.opcua_treeview = ttk.Treeview(parent, columns=("date", "message", "identifier", "url"),
                                      show="headings", height=10, style="Treeview")

        self.opcua_treeview.heading("#0", text="", anchor="w")
        self.opcua_treeview.heading("date", text=self.texts["alarm_datagrid_date"],anchor="w")
        self.opcua_treeview.heading("message", text=self.texts["alarm_datagrid_message"],anchor="w")
        self.opcua_treeview.heading("identifier", text=self.texts["alarm_datagrid_identifier"],anchor="w")
        self.opcua_treeview.heading("url", text=self.texts["alarm_datagrid_identifier"],anchor="w")

        self.opcua_treeview.column("#0", width=0, stretch=False)
        self.opcua_treeview.column("date", width=200, stretch=False)
        self.opcua_treeview.column("message", width=1720, stretch=False)
        self.opcua_treeview.column("identifier", width=0, stretch=False)
        self.opcua_treeview.column("url", width=0, stretch=False)

        self.opcua_treeview.pack(padx=10, pady=10, expand=True, fill="y",anchor="w")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.opcua_treeview.yview)
        vsb.place(x=30+2120+2, y=95, height=1165+20)

        self.opcua_treeview.configure(yscrollcommand=vsb.set)
        self.add_alarms_to_datagrid()


    def add_alarms_to_datagrid(self):
        """Adds the alarms from the OPCUA servers to the datagrid"""

        if self.opcua_treeview is None:
            logger.error("Error: No logs_treeview object")
            return

        log_folder = "logs"

        # Clear existing items in the treeview
        for item in self.opcua_treeview.get_children():
            self.opcua_treeview.delete(item)

        log_entries = []
        # Look for a log named opcua_alarms.log
        log_files = [file for file in os.listdir(log_folder) if os.path.basename(file) == "opcua_alarms.log"]

        for log_file in log_files:
            with open(os.path.join(log_folder, log_file), "r") as file:
                lines = file.readlines()
                for line in lines:
                    line = line.strip()
                    parts = line.split("|", 3)  # Split into 4 parts
                    if len(parts) == 4:
                        date_time = parts[0]
                        full_message = parts[3]
                        url = full_message.split(",")[0].strip()
                        message_parts = full_message.rsplit(",", 1)  # Split the message from the end, once
                        if len(message_parts) == 2:
                            message = message_parts[0].strip()
                            identifier = message_parts[1].strip()
                        else:
                            message = full_message
                            identifier = ""
                        log_entries.append((date_time, message, identifier,url))

        log_entries.sort(key=lambda x: datetime.strptime(x[0], "%Y:%m:%d %H:%M:%S"))

        for entry in log_entries:
            self.opcua_treeview.insert("", "end", values=entry)



    def sync_acknowledge_alarm(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.achnowledge_alarm())

        loop.close()
        return result


    async def achnowledge_alarm(self):

        self.alarm_page_command()
        return


        # En vacker dag fixa detta
        from .opcua_client import connect_opcua

        if self.opcua_treeview is None:
            logger.error("Error: No opcua_treeview object")
            return

        selected_item = self.opcua_treeview.selection()[0]

        event_id = self.opcua_treeview.item(selected_item, 'values')[2]
        url = self.opcua_treeview.item(selected_item, 'values')[3]
        client:Client = await connect_opcua(url=url,)  # type: ignore ta bort kommentar för se error


        condition_obj = client.get_node("ns=3,b'\x87\xb9\x94q\x1d[\xf1E\xa3%\xb5\x061\xba\xdf&'")
        ack_result = await condition_obj.call_method(
            "i=9111",
            ua.Variant(event_id, ua.VariantType.ByteString),
            ua.Variant(ua.LocalizedText("Acknowledged by operator"), ua.VariantType.LocalizedText)
        )
        print(f"Acknowledgment result: {ack_result}")


        print(f"Acknowledge result: {ack_result}")
        client.disconnect()


    def logs_page(self):
        """Logs page where the user can see different info/error logs"""

        logs_page = customtkinter.CTkFrame(self.container, fg_color="white")
        self.pages["logs_page"] = logs_page
        logs_page.grid(row=0, column=0, sticky="nsew")
        self.create_meny_buttons(logs_page)
        self.create_header(logs_page, self.texts['header_logs'])
        self.create_logs_treeview(logs_page)
        self.refresh_log_screen = customtkinter.CTkButton(logs_page,
                                                          text=self.texts["refresh_the_logs_button"],
                                                          command=self.add_logs_to_datagrid,
                                                          width=250,height=60,
                                                          font=("Helvetica", 18))

        self.refresh_log_screen.place(x=2200, y=100)


    def create_logs_treeview(self, parent):
        """Makes a datagrid to see the errors from example
        OPCUA, SQL or programming errors"""

        self.logs_treeview = ttk.Treeview(parent, columns=("Date", "Severity", "File", "Message"),
                                    show="headings", height=10, style="Treeview")

        self.logs_treeview.heading("#0", text="", anchor="w")
        self.logs_treeview.heading("Date", text=self.texts["log_datagrid_date"],anchor="w")
        self.logs_treeview.heading("Severity", text=self.texts["log_datagrid_Severity"],anchor="w")
        self.logs_treeview.heading("File", text=self.texts["log_datagrid_file"],anchor="w")
        self.logs_treeview.heading("Message", text=self.texts["log_datagrid_message"],anchor="w")

        self.logs_treeview.column("#0", width=0, stretch=False)
        self.logs_treeview.column("Date", width=200, stretch=False)
        self.logs_treeview.column("Severity", width=100, stretch=False)
        self.logs_treeview.column("File", width=120, stretch=False)
        self.logs_treeview.column("Message", width=1700, stretch=False)

        self.logs_treeview.pack(padx=10, pady=10, expand=True, fill="y",anchor="w")

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.logs_treeview.yview)
        vsb.place(x=30+2120+2, y=95, height=1165+20)

        self.logs_treeview.configure(yscrollcommand=vsb.set)

        self.add_logs_to_datagrid()


    def add_logs_to_datagrid(self):
        """Adds the info/errors from the logs to the datagrid
        from the logs folder"""

        if self.logs_treeview is None:
            logger.error("Error: No logs_treeview object")
            return

        log_folder="logs"
        todays_date = datetime.now().date()
        todays_date_str = todays_date.strftime("%Y:%m:%d")

        for item in self.logs_treeview.get_children():
            self.logs_treeview.delete(item)

        log_entries = []

        log_files = [file for file in os.listdir(log_folder) if file.endswith(".log")]

        for log_file in log_files:
            with open(os.path.join(log_folder, log_file), "r") as file:
                for line in file:
                    line = line.strip()
                    if todays_date_str and "ERROR" in line:
                        error = line.split("|", 3)
                        log_entries.append(error)

        log_entries.sort(key=lambda x: datetime.strptime(x[0], "%Y:%m:%d %H:%M:%S"))

        for entry in log_entries:
            self.logs_treeview.insert("", "end", values=entry)


    def load_data_in_selected_recipe(self):
        """Called with a button takes the servo steps from OPCUA server and
        puts them into the selected recipe in the SQL"""

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        if not askyesno(message=self.texts["yes_no_mesg_box_save_data_to_recipe"]):
            return

        selected_id = None

        try:

            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]

        except IndexError:
            showinfo(title="Information", message=self.texts["no_recipe_to_load_data_into"])

        recipe_structure_id = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                query = "SELECT RecipeStructID FROM tblRecipe WHERE id = ?"
                cursor.execute(query, (selected_id,))
                rows = cursor.fetchall()
                for row in rows:
                    recipe_structure_id = row[0]

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

        if selected_id:
            loading_ok = self.async_queue.put((from_units_to_sql_stepdata(selected_id, self.texts, recipe_structure_id)))
        else:
            showinfo(title="Information", message=self.texts["no_recipe_to_load_data_into"])
            logger.error(f"Error while loading data for selected recipe ID: {selected_id}")
            return


    def archive_selected_recipe(self):
        """Archive the selected recipe"""

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_archive_selected_recipe_error"])
            return

        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

        if cursor and cnxn:

            try:
                cursor.execute("EXEC [RecipeDB].[dbo].[archive_recipe] @RecipeID=?", selected_id)
                cnxn.commit()

            except PyodbcError as e:
                logger.error(f"Error in database connection: {e}")
                showinfo(title="Info", message=self.texts["error_with_database"])

            except IndexError:
                logger.error("Database credentials seem to be incomplete.")
                showinfo(title="Info", message=self.texts["error_with_database"])

            except Exception as e:
                logger.error(f"An unexpected error occurred: {e}")
                showinfo(title="Info", message=self.texts["error_with_database"])

            finally:
                cursor.close()
                cnxn.close()

        self.recipe_page_command()


    def use_selected_recipe(self):
        """Puts the selected recipe in the units stepdata"""

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        if not askyesno(message=self.texts["yes_no_mesg_box_load_data_to_robot_cell"]):
            return

        selected_id = None
        selected_name = None

        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
            selected_name = self.treeview.item(selected_item, 'values')[1]

        except IndexError as e:
            showinfo(title="Information", message=self.texts["show_info_error_loading_recipe"])
            logger.error(e)

        cursor = None
        cnxn = None
        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                step_query = "SELECT * FROM ViewValues WHERE RecipeID = ?"
                cursor.execute(step_query, (selected_id,))
                step_data = cursor.fetchall()

                query = "UPDATE tblActiveRecipeList SET ActiveRecipeName = ?"
                cursor.execute(query, (selected_name,))
                cnxn.commit()

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

        if step_data:
            self.units = self.async_queue.put(from_sql_to_units_stepdata(step_data,self.texts, selected_name))
            logger.info(f"Successfully updated the active recipe to: {selected_name}")

        else:
            showinfo(title='Information', message=self.texts["show_info_use_selected_recipe_error"])
            return


    def delete_recipe(self, recipe_name):
        """Called with a button delete a recipe from the datagrid and the SQL"""

        if not askyesno(message=self.texts["yes_no_mesg_box_delete_recipe"] + recipe_name + "?"):
            return

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:
                selected_item = self.treeview.selection()[0]
                selected_id = self.treeview.item(selected_item, 'values')[0]

                cursor.execute("EXEC [RecipeDB].[dbo].[delete_recipe] @RecipeID=?", selected_id)

                cnxn.commit()
                self.recipe_page_command()

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)


    def submit_new_recipe(self, name, comment, selected_structure_id, parent_id=None):
        """Called with a button adds a new recipe to the datagrid and SQL"""

        logger.info(f"Trying to submit new recipe: Name: {name}, Comment: {comment}, Structure ID: {selected_structure_id}")

        if not name or not selected_structure_id:
            showinfo(title='Information', message=self.texts["show_info_submit_new_recipe_error"])
            return
        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:

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
                    @RecipeStructID=?,
                    @ParentID=?
                """, name, comment, selected_structure_id, parent_id)
                cnxn.commit()
                cursor.execute('SELECT [id], [RecipeName], [RecipeComment], [RecipeCreated], \
                                [RecipeUpdated], [RecipeLastDataSaved], [ParentID] FROM [RecipeDB].[dbo].[viewRecipesActive]')

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

        self.recipe_page_command()


    def update_recipe(self, name, comment, selected_structure_id, selected_id):
        """Called with a button to update servo steps or name of a recipe"""

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        try:
            logger.info(f"Updating recipe: ID: {selected_id}, Name: {name}, Comment: {comment}, Structure ID: {selected_structure_id}")

        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_update_recipe_error"])
            return

        if not name and not comment and not selected_structure_id:
            showinfo(title='Information', message=self.texts["show_info_update_recipe_name_empty"])
            return

        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            cursor.execute("EXEC [RecipeDB].[dbo].[update_recipe] @RecipeID=?, @RecipeName=?, @RecipeComment=?, @RecipeStructID=?",
                           selected_id, name, comment, selected_structure_id)
            cnxn.commit()

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

        self.recipe_page_command()


    def edit_recipe(self):
        """Edits the selected recipe servo and robot data"""

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        selected_id = None

        try:
            selected_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_item, 'values')[0]
        except IndexError:
            showinfo(title='Information', message=self.texts["show_info_edit_recipe_no_selected"])

        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            if cursor and cnxn:

                query = """
                SELECT [UnitID], [TagName], [TagValue], [TagDataType], [UnitName]
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
                    logger.error(f"No data found for editing recipe ID: {selected_id}")
                    showinfo(title='Information', message=self.texts["show_info_edit_recipe_no_data"])
                    return

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)


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


    def logs_page_command(self):
        """Shows the log page"""
        self.logs_page()
        self.show_page("logs_page")


    def about_page_command(self):
        """Shows the about page"""
        self.open_about_window()


    def open_about_window(self):
        """Shows the about window"""
        from .about_window import AboutWindow

        if not hasattr(self, 'about_window') or self.about_window is None or not self.about_window.winfo_exists():
            self.about_window = AboutWindow(self)
            self.about_window.focus()
            self.about_window.attributes('-topmost', True)

        if hasattr(self, 'about_window') and self.about_window.winfo_exists():
            self.about_window.focus()
            self.about_window.lift()


    def open_edit_steps_window(self, rows,selected_id):
        from .edit_steps_window import EditStepsWindow
        """Shows the edit recipe window"""

        if not hasattr(self, 'edit_steps_window') or self.edit_steps_window is None or not self.edit_steps_window.winfo_exists():
            self.edit_steps_window = EditStepsWindow(self, rows, selected_id, self.texts)

        if hasattr(self, 'edit_steps_window') and self.edit_steps_window.winfo_exists():
            self.edit_steps_window.focus()
            self.edit_steps_window.lift()


    def open_make_recipe_window(self, is_child=False, parent_id=None):
        """Shows the make a recipe window"""
        from .make_recipe_window import MakeRecipeWindow

        if not hasattr(self, 'make_recipe_window') or self.make_recipe_window is None or not self.make_recipe_window.winfo_exists():
            self.make_recipe_window = MakeRecipeWindow(self, self.texts, is_child=is_child, parent_id=parent_id)

        if hasattr(self, 'make_recipe_window') and self.make_recipe_window.winfo_exists():
            self.make_recipe_window.focus()
            self.make_recipe_window.lift()


    def open_update_recipe_window(self):
        """Shows the make a recipe window"""
        from .edit_recipe_window import EditRecipeWindow

        if self.treeview is None:
            logger.error("Error: No recipe treeview object")
            return

        cursor = None
        cnxn = None

        try:
            sql_connection = SQLConnection()
            sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
            cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

            selected_id_item = self.treeview.selection()[0]
            selected_id = self.treeview.item(selected_id_item, 'values')[0]

            cursor.execute('SELECT [RecipeName], [RecipeComment], [RecipeStructID] \
                           FROM [RecipeDB].[dbo].[tblRecipe] \
                           WHERE [id] = ?', (selected_id,))

            row = cursor.fetchall()

            recipeName = None
            recipeComment = None
            recipe_struct = None

            for insert_good_var_name in row:
                recipeName, recipeComment, recipe_struct = insert_good_var_name

        except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except IndexError:
            logger.error("Database credentials seem to be incomplete.")
            showinfo(title="Info", message=self.texts["error_with_database"])

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            showinfo(title="Info", message=self.texts["error_with_database"])

        finally:
            if cursor and cnxn:
                sql_connection.disconnect_from_database(cursor, cnxn)

        if not hasattr(self, 'edit_recipe_window') or self.edit_recipe_window is None or not self.edit_recipe_window.winfo_exists():
            self.edit_recipe_window = EditRecipeWindow(app_instance=self,
                                                         texts=self.texts,
                                                         selected_id=selected_id,
                                                         recipe_name=recipeName,
                                                         recipe_comment=recipeComment,
                                                         recipe_struct=recipe_struct)

        if hasattr(self, 'edit_recipe_window') and self.edit_recipe_window.winfo_exists():
            self.edit_recipe_window.focus()
            self.edit_recipe_window.lift()


    def open_selected_recipe_menu(self, selected_id):
        from .selected_recipe_menu_window import SelectedRecipeMenu

        selected_item = self.treeview.selection()[0]
        selected_id = self.treeview.item(selected_item, 'values')[0]
        recipe_name = self.treeview.item(selected_item, 'values')[1]
        if not hasattr(self, 'selected_recipe_menu') or self.selected_recipe_menu is None or not self.selected_recipe_menu.winfo_exists():
            self.selected_recipe_menu = SelectedRecipeMenu(self, self.texts, parent_id=selected_id, recipe_name=recipe_name)

        if hasattr(self, 'selected_recipe_menu') and self.selected_recipe_menu.winfo_exists():
            self.selected_recipe_menu.focus()
            self.selected_recipe_menu.lift()




def main():
    """Main func to start the program"""

    app = None

    # Start the alarm monitor
    monitor_alarms_thread = Thread(target=run_monitor_alarms_loop, daemon=True)
    monitor_alarms_thread.start()

    # Webserver to see what is producing and quanity
    main_webserver()

    async_queue = Queue()

    app = App(async_queue)

    # Start the asyncio loop in a separate thread to avoid blocking the main thread
    async_thread = Thread(target=run_asyncio_loop, args=(async_queue, app,), daemon=True)
    async_thread.start()

    app.mainloop()

    async_queue.put(None)
    async_thread.join()


