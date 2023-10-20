import json
import threading
import asyncio
from flask import Flask, request, render_template
from flask_cors import CORS
from waitress import serve
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import time
from asyncua import Client, ua

from .create_log import setup_logger
from .opcua_client import connect_opcua
from .data_encrypt import DataEncryptor

# Global variables
client: Client = None

logger = setup_logger('Webserver')

with open("configs/webserver_config.json", encoding="UTF8") as host_info:
    config = json.load(host_info)


app = Flask(__name__, template_folder='../templates', static_folder="../static")

CORS(app, origins=[f"{config['host']}:{config['port']}"])

logger.info(f"Server initialized at {config['host']}:{config['port']}")

data_encrypt = DataEncryptor()
sql_config = data_encrypt.encrypt_credentials("sql_config.json", "SQL_KEY")
database_config = sql_config["database"]

base_uri = f'mssql+pyodbc://{database_config["username"]}:{database_config["password"]}@{database_config["server"]}'
db_name = database_config["database_name"]
driver_name = '?driver=ODBC Driver 17 for SQL Server'
database_uri = f'{base_uri}/{db_name}{driver_name}'

app.config.update({
    'SQLALCHEMY_DATABASE_URI': database_uri,
    'SQLALCHEMY_POOL_SIZE': 10,
    'SQLALCHEMY_POOL_TIMEOUT': 10,
    'SQLALCHEMY_POOL_RECYCLE': 3600,
})

db = SQLAlchemy(app)

class AppState:
    def __init__(self):
        self.produced = 0
        self.to_do = 0
        self.estimated_time_remaining = "00:00"


app_state = AppState()


@app.route('/', methods=['GET'])
def main_page():
    logger.info(f'Request received from {request.remote_addr}')
    return render_template('index.html')


@app.route('/get_data', methods=['GET'])
def get_data():
    """
    Get Data Route
    Fetches data from the database and runs an asynchronous task to retrieve additional data.
    Returns the response as JSON.
    """
    produced = None
    to_do = None
    response = None
    headers = None

    try:
        query = text('SELECT * FROM tblActiveRecipeList')
        active_recipe_name = db.session.execute(query).fetchall()[0][0]
    except Exception as exception:
        db.session.rollback()
        logger.error("Database error occurred", exception)
        return "Server error", 500
    finally:
        db.session.close()
        logger.info("Database session closed")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(data_to_webserver())

    if result is not None:
        try:
            produced, to_do = result
            app_state.produced = produced
            app_state.to_do = to_do
            response = json.dumps({
                "produced": produced,
                "to_do": to_do,
                "name": active_recipe_name,
                "estimated_time": app_state.estimated_time_remaining
            })
            headers = {"Content-Type": "application/json"}
        except TypeError as exception:
            logger.error("Error occurred", exception)
            return "Server error", 500
    else:
        logger.error("No data received from the opcua server")
        return "Server error", 500

    return response or "", 200, headers or {}


async def connect_opcua_server():
    global client

    if client is None:
        from .ms_sql import get_units
        units = await get_units()
        ip_address = units[2][1]

        data_encrypt = DataEncryptor()
        opcua_config = data_encrypt.encrypt_credentials("opcua_server_config.json", "OPCUA_KEY")
        for server in opcua_config["servers"]:
            encrypted_username = server["username"]
            encrypted_password = server["password"]

            client = await connect_opcua(ip_address, encrypted_username, encrypted_password)

    return client


async def data_to_webserver():
    """
    Retrieve specific data and send it to a webserver.

    :return: Produced value and to-do value if found
    """
<<<<<<< HEAD

=======
>>>>>>> d4e3868409d914f532e85adbda6892ebffaf5d14
    client = await connect_opcua_server()

    if client:
        try:
            produced_node_id = ua.NodeId.from_string('ns=3;s="E_Flex"."Info"."QuantityPartsMade"')
            to_do_node_id = ua.NodeId.from_string('ns=3;s="E_Flex"."Info"."QuantityOfPartsToMake"')

            produced_node = client.get_node(produced_node_id)
            to_do_node = client.get_node(to_do_node_id)

            produced_value = await produced_node.get_value()
            to_do_value = await to_do_node.get_value()

            return produced_value, to_do_value

        except AttributeError as exception:
            logger.error(f"AttributeError:{exception}")

        except ua.uaerrors._auto.BadNoMatch as exception:
            logger.error(f"BadNoMatch. Ingen matchande variable:{exception}")

        except TimeoutError as exception:
            logger.error(f"Connection timeout: {str(exception.args)}" if exception else "Connection timeout: (empty message)")

        except Exception as exception:
            logger.error(f"Error getting values: {str(exception)},{type(exception)}")
            return
    else:
        logger.error("Failed to connect to OPCUA server.")
        return


def calculate_time_to_produce():
    timestamps = []
    counts = []

    while True:
        produced = app_state.produced
        to_do = app_state.to_do

        current_time = time.time()
        timestamps.append(current_time)
        counts.append(produced)

        if len(timestamps) > 2 and max(counts) > 1:
            try:
                time_diff = timestamps[-1] - timestamps[0]
                count_diff = counts[-1] - counts[0]

                avg_time_per_item = time_diff / count_diff
                remaining_items = to_do - produced
                estimated_time_remaining_seconds = avg_time_per_item * remaining_items
                hours, remainder = divmod(estimated_time_remaining_seconds, 3600)
                minutes = remainder // 60
                app_state.estimated_time_remaining = f"{str(int(hours)).zfill(2)}:{str(int(minutes)).zfill(2)}"

                if len(timestamps) > 10:
                    timestamps.pop(0)
                    counts.pop(0)

            except ZeroDivisionError:
                pass
            except Exception as exception:
                logger.error("Error occurred", exception)

        time.sleep(5)


def run_server():
    serve(app, host=config['host'], port=config['port'])


def main_webserver():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    time_calc_thread = threading.Thread(target=calculate_time_to_produce, daemon=True)
    time_calc_thread.start()


if __name__ == "__main__":
    main_webserver()
