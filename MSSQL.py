import pyodbc
import pandas as pd
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

# Connect to MSSQL
server = 'SDA-TESTSTATION' # Replace <server_name> with the name of your MSSQL server
database = 'RecipeDB' # Replace <database_name> with the name of your database
username = 'sa' # Replace <username> with your username
password = 'sa' # Replace <password> with your password
cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+password)

# Query the database
query = 'SELECT * FROM tblRecipe' # Replace <table_name> with the name of your table
df = pd.read_sql(query, cnxn)

# Set the id column as the index of the DataFrame
df.set_index('id', inplace=True)

# Create the tkinter window
root = tk.Tk()
root.geometry('1200x600')

# Create the Treeview widget
treeview = ttk.Treeview(root)
treeview.pack()

# Add the columns to the Treeview
treeview['columns'] = list(df.columns)
for column in df.columns:
    treeview.heading(column, text=column, anchor='w')

# Add the data to the Treeview and auto-resize columns
for index, row in df.iterrows():
    values = list(row)
    treeview.insert('', 'end', values=values)
    for i, cell in enumerate(values):
        col_width = tkFont.Font().measure(treeview.heading(treeview['columns'][i],)['text'])
        if treeview.column(treeview['columns'][i],width=None) < col_width:
            treeview.column(treeview['columns'][i], width=col_width)

root.mainloop()