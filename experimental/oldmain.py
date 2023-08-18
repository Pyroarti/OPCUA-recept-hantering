import sys                            
import asyncio                          
from asyncua import Client, ua
from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256          
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
import json


class OPCUA_ClientThread(QThread):
    # Signal för att skicka ett string,float,bool från tråden till GUI:et som hanterar klienten.
    value_received = pyqtSignal(str)
    data_received = pyqtSignal(float, float, ua.NodeId, bool)


    async def read_opcua_values(self, client, node_id_string):              # Asynkron metod för att läsa värden från OPC UA
        node_id = ua.NodeId.from_string(node_id_string)                     # Skapar ett node ID från en sträng
        node = client.get_node(node_id)                                     # Hämtar noden från klienten
        value = await node.get_value()                                      # Hämtar värdet från noden
        self.value_received.emit(f"Value: {value}")
        #print(value)

    # Asynkron metod för att uppdatera ett OPC UA-värde i en nod och sedan koppla från OPC UA-servern.
    async def update_and_disconnect(self, client, node_id_string, new_value):
        # Anropar metoden som uppdaterar värdet i noden
        print("made it here")
        await self.update_node_value(client, node_id_string, new_value)
        await client.disconnect()

    def update_value_and_disconnect(self, node_id, new_value):
        print("made it here 2")
        asyncio.run(self.connect_and_run(self.update_and_disconnect, node_id, new_value))
       

    async def update_node_value(self, client, node_id_string, new_value):
        # Skapar ett node ID från en sträng.
        node_id = ua.NodeId.from_string(node_id_string)
        # Hämtar noden från OPC UA-klienten.
        node = client.get_node(node_id)
        # Skapar ett Variant-objekt från det nya värdet.
        variant = ua.Variant(new_value)
        # Skapar ett DataValue-objekt från Variant-objektet.
        data_value = ua.DataValue(variant)
        # Skriver värdet till noden.
        await node.write_value(data_value)


    async def connect_and_run(self, target_function, node_id, new_value=None):
        url = "opc.tcp://192.168.187.10:4840"
        client = Client(url=url, timeout=4)

        #¤cert_path = "/path/to/client/cert.der"
        #key_path = "/path/to/client/key.pem"

        #await client.set_security(
        #SecurityPolicyBasic256Sha256,
        #certificate=cert_path,
        #private_key=key_path,
        #server_certificate="certificate-example.der")


        client.set_user("LMT")
        client.set_password("lmt.1201")
        await client.connect()

        #Skapar ett NodeId-objekt från en nod-ID-sträng
        #node_id = ua.NodeId.from_string(node_id_string)
        #Hämtar noden från klienten med hjälp av NodeId-objektet
        step_data_node = client.get_node(node_id)
        print("made it here")
        #Hämtar alla barnnoder under noden som just hämtades
        step_nodes = await step_data_node.get_children()

        pos_x_value = 0.0
        pos_y_value = 0.0



        for step_node in step_nodes:
            # Hämtar noden som visar om noden är aktiv
            active_node = await step_node.get_child('Active')
            # Hämtar värdet från noden som visar om noden är aktiv
            is_active = await active_node.get_value()
            # Sänder ut signalen data_received med positionerna, nod-ID och om noden är aktiv
            self.data_received.emit(pos_x_value, pos_y_value, step_node.nodeid, is_active)


            if is_active:
                pos_x_node = await step_node.get_child('PosX')
                pos_x_value = await pos_x_node.get_value()

                pos_y_node = await step_node.get_child('PosY')
                pos_y_value = await pos_y_node.get_value()

                print(f"PosX: {pos_x_value}, PosY: {pos_y_value}")
                # Sänder ut signalen data_received med positionerna, nod-ID och om noden är aktiv
                self.data_received.emit(pos_x_value, pos_y_value, step_node.nodeid, is_active)
                 
        
        #Om nya värdet finns, anropar funktionen som uppdaterar nodens värde med det nya värdet och kopplar från servern
        if new_value is not None:
            await target_function(client, node_id, new_value)
        else:
            # Annars anropar funktionen som läser av nodens värde och kopplar från servern
            await target_function(client, node_id)

        await client.disconnect()
    #Metod som anropar connect_and_run för att ansluta till servern och läsa av en nod med ett visst ID
    def run(self, node_id_string):
        asyncio.run(self.connect_and_run(self.read_opcua_values, node_id_string))


class OpcUaClientGUI(QMainWindow):     # Skapar en klass för gränssnittet
    def __init__(self):
        super().__init__()

        self.opcua_thread = OPCUA_ClientThread()        # Skapar en instans
        self.init_ui()                                 # Anropar metoden för att initialisera gränssnittet
        self.opcua_thread.data_received.connect(self.update_data_grid)
        self.setFixedWidth(800)                         # Anger fönstrets bredd
        self.setFixedHeight(800)                        # Anger fönstrets höjd


    def init_ui(self):                                  # Metod för att skapa gränssnittet
        self.setWindowTitle("Lmt recept hantering")
        self.data_grid = QTableWidget()


        row_count = 0  
        column_count = 3  

        self.data_grid.setRowCount(row_count)
        self.data_grid.setColumnCount(column_count)

        for row in range(row_count):
            for col in range(column_count):
                item = QTableWidgetItem()
               # item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Kanske behövs? kanske inte, något med att göra celler readable only
                self.data_grid.setItem(row, col, item)
     
        
        self.data_grid.setHorizontalHeaderLabels(['PosX', 'PosY', 'NodeId'])  # Column namn
        self.data_grid.setColumnHidden(2, True)
        self.data_grid.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) 

        self.data_grid.cellDoubleClicked.connect(self.on_data_grid_cell_double_clicked)

        data_grid_layout = QVBoxLayout()  # Create a separate layout for the data grid
        data_grid_layout.addWidget(self.data_grid)  # Add data grid to the data grid layout

        self.node_id_input = QLineEdit()                
        self.node_id_input.setPlaceholderText("Enter Node ID")

        self.value_input = QLineEdit()                  
        self.value_input.setPlaceholderText("Enter value")

        connect_button = QPushButton("Connect and Read Value") 
        connect_button.clicked.connect(self.on_connect_button_clicked)

        self.value_label = QLabel()

        update_value_button = QPushButton("Update Value")
        update_value_button.clicked.connect(self.on_update_value_button_clicked)

        quit_button = QPushButton("Quit")               
        quit_button.clicked.connect(self.close)

        control_layout = QVBoxLayout()  # Create a separate layout for the other widgets
        control_layout.addWidget(self.node_id_input)
        control_layout.addWidget(self.value_input)
        control_layout.addWidget(connect_button)
        control_layout.addWidget(self.value_label)
        control_layout.addWidget(update_value_button)
        control_layout.addWidget(quit_button)

        main_layout = QVBoxLayout()  # Create a main layout
        main_layout.addLayout(data_grid_layout)  # Add data grid layout to the main layout
        main_layout.addLayout(control_layout)  # Add control layout to the main layout

        central_widget = QWidget()                      
        central_widget.setLayout(main_layout)                
        self.setCentralWidget(central_widget)

        self.opcua_thread.value_received.connect(self.update_value_label)

    def on_connect_button_clicked(self):                # Funktion för att hantera knapptryckning för anslutning
        node_id_string = self.node_id_input.text()       # Hämtar nod-ID från textfältet
        self.opcua_thread.run(node_id_string)            # Anropar klient-tråden för att ansluta till servern

    def on_update_value_button_clicked(self):
        node_id_string = self.node_id_input.text()
        new_value = self.value_input.text().strip()
        if not new_value:
            return

        try:
            new_value = int(new_value)
        except ValueError:
            try:
                new_value = float(new_value)
            except ValueError:
                if new_value.lower() == 'true':
                    new_value = True
                elif new_value.lower() == 'false':
                    new_value = False
                else:
                    return

        self.opcua_thread.update_value_and_disconnect(node_id_string, new_value)


    def update_value_label(self, text):                 # Funktion för att uppdatera QLabel med nodvärdet
        self.value_label.setText(text)                  # Sätter texten på QLabel-objektet

   
    def update_data_grid(self, pos_x, pos_y, node_id, is_active):
        
        print(f"node_id: {node_id}")
        

        # Check if the received node_id already exists in the data grid
        for row in range(self.data_grid.rowCount()):
            existing_item_node_id = self.data_grid.item(row, 2).data(Qt.UserRole)
            if existing_item_node_id and existing_item_node_id == node_id:
                # Update the row if it already exists
                if is_active:
                    self.data_grid.setItem(row, 0, QTableWidgetItem(str(pos_x)))
                    self.data_grid.setItem(row, 1, QTableWidgetItem(str(pos_y)))
                else:
                    self.data_grid.removeRow(row)
                break
        else:
            # If the node_id is not in the data grid and is_active is True, add a new row to the data grid
            if is_active:
                row = self.data_grid.rowCount()
                self.data_grid.insertRow(row)
                self.data_grid.setItem(row, 0, QTableWidgetItem(str(pos_x)))
                self.data_grid.setItem(row, 1, QTableWidgetItem(str(pos_y)))

                # Add the NodeId object to the data grid using UserRole
                item = QTableWidgetItem(str(node_id))
                item.setData(Qt.UserRole, node_id)
                self.data_grid.setItem(row, 2, item)

                #step_data_node = self.opcua_thread.client.get_node(node_id)
                #step_nodes = step_data_node.get_children()
                #print(f"step_nodes for {node_id}: {[node.nodeid.to_string() for node in step_nodes]}")






    def on_data_grid_cell_double_clicked(self, row, column):
        # Get the current value from the selected cell
        current_value = self.data_grid.item(row, column).text()

        # Show an input dialog to get the new value from the user
        new_value, ok = QInputDialog.getText(self, "Enter new value", f"Enter new value for Pos{['X', 'Y'][column]}:", text=current_value)

        # If the user pressed OK and the new value is not empty, update the value on the OPC UA server
        if ok and new_value.strip():
            try:
                new_value = float(new_value)  # converterat värdet till en float
            except ValueError:
                return  # om något blir fel

            # Update the value in the data grid
            self.data_grid.setItem(row, column, QTableWidgetItem(str(new_value)))

            # Hämtar node id för där man trycker
            node_id = self.data_grid.item(row, 2).data(Qt.UserRole)
            print("----------------------------------------------")
            print(f"node_id: {node_id}")
            print(f"the new value is : {new_value}")
            print("----------------------------------------------")

            child_node_name = ['PosX', 'PosY'][column]
            # Update the value on the OPC UA server
            self.opcua_thread.update_value_and_disconnect(node_id, new_value)

            


   

app = QApplication(sys.argv)
main_window = OpcUaClientGUI()
main_window.show()
sys.exit(app.exec_())