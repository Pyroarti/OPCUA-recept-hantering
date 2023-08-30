import json
import threading
import asyncio
from flask import Flask, request, render_template
from flask_cors import CORS
from waitress import serve
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text
import time

from .create_log import setup_logger
from .opcua_client import data_to_webserver
from .data_encrypt import DataEncrypt

produced_global = 0
to_do_global = 0

logger = setup_logger('webserver')

with open ("configs/webserver_config.json", encoding="UTF8") as host_info:
    json_data = json.load(host_info)

    host_adress = json_data["host"]
    host_port = json_data["port"]

app = Flask(__name__, template_folder='../templates', static_folder="../static")

CORS(app, origins=[host_adress + ":" + host_port])
logger.info(f"Server initialized at {host_adress}:{host_port}")

data_encrypt = DataEncrypt()
sql_config = data_encrypt.encrypt_credentials("sql_config.json", "SQL_KEY")
database_config = sql_config["database"]

username = database_config["username"]
password = database_config["password"]
server = database_config["server"]
database_name = database_config["database_name"]
driver = 'ODBC Driver 17 for SQL Server'  # Ändra till vilken vi kör

database_uri = f'mssql+pyodbc://{username}:{password}@{server}/{database_name}?driver={driver}'

app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600

db = SQLAlchemy(app)


@app.route('/', methods=['GET'])
def main_page():
    client_ip = request.remote_addr
    logger.info(f'Request received from {client_ip}')

    return render_template('index.html')


@app.route('/get_data', methods=['GET'])
def get_data():

    """
    Get Data Route
    Fetches data from the database and runs an asynchronous task to retrieve additional data.
    Returns the response as JSON.
    """
    global produced_global, to_do_global

    produced = None
    to_do = None
    response = None
    headers = None

    try:
        query = text('SELECT * FROM tblActiveRecipeList')
        active_recipe_name = db.session.execute(query).fetchall()[0][0]

    except Exception as exeption:
        db.session.rollback()
        logger.warning("Database error occurred", exeption)
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
            produced_global = produced
            to_do_global = to_do
            response = json.dumps({"produced": produced, "to_do": to_do, "name": active_recipe_name})
            headers = {"Content-Type": "application/json"}
        except TypeError as exeption:
            logger.warning("Error occurred", exeption)
            return "Server error", 500
    else:
        logger.warning("No data received from the opcua server")
        return "Server error", 500

    return response or "", 200, headers or {}


def calculate_time_to_produce():
    global produced_global, to_do_global

    timestamps = []
    counts = []

    while True: 
        produced = produced_global
        to_do = to_do_global

        current_time = time.time()
        timestamps.append(current_time)
        counts.append(produced)

        if len(timestamps) > 10 and max(counts) > 1:
            time_diff = timestamps[-1] - timestamps[0]
            count_diff = counts[-1] - counts[0]

            avg_time_per_item = time_diff / count_diff
            remaining_items = to_do - produced
            estimated_time_remaining = avg_time_per_item * remaining_items

            estimated_time_remaining = int(estimated_time_remaining)

            estimated_time_remaining = int(estimated_time_remaining / 60)

            print(f"Uppskattad tid kvar: {estimated_time_remaining} minuter")

            timestamps.pop(0)
            counts.pop(0)

        time.sleep(5) 


def run_server():
    serve(app, host=host_adress, port=host_port)


def main_webserver():
    url = f'http://{host_adress}:{host_port}'

    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    time_calc_thread = threading.Thread(target=calculate_time_to_produce)
    time_calc_thread.daemon = True
    time_calc_thread.start()


if __name__ == "__main__":
    main_webserver()
