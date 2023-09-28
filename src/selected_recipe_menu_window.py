import customtkinter
from tkinter.messagebox import showinfo

from .create_log import setup_logger
from .gui import App

logger = setup_logger(__name__)


class Selected_recipe_menu(customtkinter.CTkToplevel):
    """Class for a pop up window to settings for a recipe"""
    def __init__(self, app_instance:"App", texts,  parent_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resizable(False, False)
        self.parent_id = parent_id
        self.texts = texts
        self.title("")
        pop_up_width = 800
        pop_up_height = 900
        position_x = 900
        position_y = 400
        self.geometry(f"{pop_up_width}x{pop_up_height}+{position_x}+{position_y}")
        self.app_instance = app_instance

        self.place_buttons()


    def place_buttons(self):

        self.make_recipe_button = customtkinter.CTkButton(
            self,
            text=self.texts['make_a_child_recipe'],
            command=self.combined_command(
                lambda: self.app_instance.open_make_recipe_window(is_child=True, parent_id=self.parent_id),
                self.close_window
            ),
            width=350,
            height=60,
            font=("Helvetica", 18)
        )

        self.make_recipe_button.pack(pady=10)

        self.update_recipe_info_button = customtkinter.CTkButton(self, text=self.texts['update_recipe'],
                                                            command= self.combined_command(self.app_instance.open_update_recipe_window,self.close_window),
                                                            width=350,
                                                            height=60,
                                                            font=("Helvetica", 18))
        self.update_recipe_info_button.pack(pady=10)

        self.delete_selected_row_button = customtkinter.CTkButton(self, text=self.texts["delete_the_selected_recipe_button"],
                                                                  command= self.combined_command(self.app_instance.delete_recipe,self.close_window),
                                                                  width=350,
                                                                  height=45,
                                                                  font=("Helvetica", 18))
        self.delete_selected_row_button.pack(pady=(15,0))


        self.load_data_in_selected_recipe_button = customtkinter.CTkButton(self,
                                                                           text=self.texts['load_servo_steps_into_selected_recipe_button'],
                                                                           command= self.combined_command(self.app_instance.load_data_in_selected_recipe,self.close_window),
                                                                           width=350,
                                                                           height=45,
                                                                           font=("Helvetica", 18))

        self.load_data_in_selected_recipe_button.pack(pady=(60,0))

        self.use_selected_recipe_button = customtkinter.CTkButton(self, text=self.texts["use_the_selected_recipe_button"],
                                                                   command=self.combined_command(self.app_instance.use_selected_recipe, self.close_window),
                                                                   width=350,
                                                                   height=45,
                                                                   font=("Helvetica", 18))
        self.use_selected_recipe_button.pack(pady=(20,0))

        self.edit_selected_recipe_button = customtkinter.CTkButton(self, text=self.texts["edit_the_selected_recipe_button"],
                                                                  command= self.combined_command(self.app_instance.edit_recipe,self.close_window),
                                                                  width=350,
                                                                  height=45,
                                                                  font=("Helvetica", 18))
        self.edit_selected_recipe_button.pack(pady=(20,0))


    def close_window(self):
        self.destroy()


    def combined_command(self, func1, func2):
        """Its to make sure the pop up window closes after the user has pressed a button"""
        def combined():
            func1()
            func2()
        return combined

