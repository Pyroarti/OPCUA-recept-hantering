import sys
import asyncio
from asyncua import Client, ua
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QPushButton, QLabel, QMessageBox


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPC UA Client")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.grid_layout = QGridLayout()
        self.central_widget.setLayout(self.grid_layout)

        # Create connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_server)
        self.grid_layout.addWidget(self.connect_button, 0, 0)

        # Create label to display status
        self.status_label = QLabel("Not connected")
        self.grid_layout.addWidget(self.status_label, 0, 1)

        # Create grid to display information
        self.grid = QGridLayout()
        self.grid_layout.addLayout(self.grid, 1, 0, 1, 2)

    async def connect_to_server(self):
        url = "opc.tcp://192.168.187.10:4840"  # replace with your server URL

        try:
            client = Client(url=url, timeout=4)
            client.set_user("LMT")
            client.set_password("lmt.1201")
            await client.connect()

            self.status_label.setText("Connected")

            # node_id = ua.NodeId.from_string(string='ns=3;s="LittleDB"."ChangbleTagBool1"')
            node_id = ua.NodeId.from_string(string='ns=3;s="StepData"."RunningSteps"."Steps"')
            nodeSteps = client.get_node(node_id)
            nodes = await nodeSteps.get_children()

            row = 0
            for node in nodes:
                value = await node.get_value()
                node_name = node.get_display_name().Text
                self.grid.addWidget(QLabel(node_name), row, 0)
                self.grid.addWidget(QLabel(str(value)), row, 1)
                row += 1

            await client.disconnect()
            self.status_label.setText("Disconnected")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.status_label.setText("Error")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
