self.checkbox_smc1_var = IntVar()
        self.checkbox_smc2_var = IntVar()

        self.checkbox_smc1 = customtkinter.CTkCheckBox(right_frame, text="SMC1",
                                                       width = 150,
                                                       height = 40,
                                                       checkbox_width = 35,
                                                       checkbox_height = 35,
                                                       font=("Helvetica", 18),
                                                       variable=self.checkbox_smc1_var,
                                                       command=self.checkbox_status)

        self.checkbox2_smc2 = customtkinter.CTkCheckBox(right_frame, text="SMC2",
                                                        variable=self.checkbox_smc2_var,
                                                        width = 150,
                                                        height = 40,
                                                        checkbox_width = 35,
                                                        checkbox_height = 35,
                                                        font=("Helvetica", 18),
                                                        command=self.checkbox_status)

        self.checkbox_smc1.pack(pady=(15,0))
        self.checkbox2_smc2.pack(pady=(15,0))


    def checkbox_status(self):
        print(f"Checkbox 1 is {'checked' if self.checkbox_smc1_var.get() else 'not checked'}")
        print(f"Checkbox 2 is {'checked' if self.checkbox_smc2_var.get() else 'not checked'}")