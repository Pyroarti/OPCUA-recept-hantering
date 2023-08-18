import asyncio
from asyncua import ua, Server, Client
import asyncua.common.subscription
from .create_log import setup_logger
from .opcua_client import connect_opcua
import traceback


logger_alarm = setup_logger('opcua_prog_alarm')
logger_opcua_alarm = setup_logger("opcua_alarms")


async def subscribe_to_server(adresses, encrypted_username, encrypted_password):
    """
    This function handles the process of connecting and subscribing to the OPCUA server.
    Args:
        adresses (str): Address of the OPCUA server.
        encrypted_username (str): Encrypted username for the OPCUA server.
        encrypted_password (str): Encrypted password for the OPCUA server.
        add_opcua_alarm_to_datagrid_function (function): Callback function that handles adding alarm to data grid.
    """

    client = None

    while True:
        try:
            if client is None:
                client = await connect_opcua(adresses, encrypted_username, encrypted_password)

            else:

                try:
                    handler = SubHandler(adresses)
                    sub = await client.create_subscription(1000, handler)
                    alarmConditionType = client.get_node("ns=0;i=2915")

                    server_node = client.get_node(ua.NodeId(Identifier=2253,
                                                            NodeIdType=ua.NodeIdType.Numeric,
                                                            NamespaceIndex=0))

                    await sub.subscribe_alarms_and_conditions(server_node, alarmConditionType)
                    break
                except Exception as e:
                    logger_alarm.error(f"Error subscribing to server {adresses}: {e}")
                    await asyncio.sleep(10)
                    continue

        except Exception as e:
            logger_alarm.error(f"Error connecting to server {adresses}: {e}")
            await asyncio.sleep(10) 
            continue


class SubHandler(object):
    """
    Subscription Handler class that receives the events from the OPC UA server.
    Attributes:
        add_opcua_alarm_to_datagrid_function (function): Callback function that handles adding alarm to data grid.
        address (str): Address of the OPCUA server.
    """

    def __init__(self, address):
        self.address = address

    def event_notification(self, event):
        from .gui import get_database_connection

        try:
            message = str(event.Message.Text)
            date = event.Time
            active_state_id = None
            severity = event.Severity
            enabled_state_id = None
            suppresed_or_shelved = event.SuppressedOrShelved
            acked_state_text = str(event.AckedState.Text)
            acked_state_id = None
            condition_class_id = str(event.ConditionClassId)
            identifier = str(event.NodeId.Identifier)
            quality = str(event.Quality)
            retain = event.Retain

            if hasattr(event, "ActiveState/Id"):
                active_state_id = getattr(event, "ActiveState/Id")

            if hasattr(event, "EnabledState/Id"):
                enabled_state_id = getattr(event, "EnabledState/Id")

            if hasattr(event, "AckedState/Id"):
                acked_state_id = getattr(event, "AckedState/Id")

            # Prepare SQL insert statement
            #insert_statement = """
            #INSERT INTO dbo.tblAlarm (Message, Time, State, Severity, EnableStateId, SuppresedOrShelved, 
            #AcknowledgedStateText, AcknowledgedState, ConditionClassId, Quality, Retain)
            #VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            #"""

            #data = (message, date, active_state_id, severity, enabled_state_id, suppresed_or_shelved, 
            #        acked_state_text, acked_state_id, condition_class_id, quality, retain)

            #cursor, cnxn = get_database_connection()
            #cursor.execute(insert_statement, data)
            #cnxn.commit()

            logger_opcua_alarm.error(
                                    f"New event received from {self.address}:"
                                    f"Message: {message}"
                                    f"Date: {date}"
                                    f"State: {active_state_id}"
                                    f"Severity: {severity}"
                                    f"Enable state id: {enabled_state_id}"
                                    f"suppresed_or_shelved: {suppresed_or_shelved}"
                                    f"acknowledged state text: {acked_state_text}"
                                    f"acknowledged state: {acked_state_id}"
                                    f"condition class id: {condition_class_id}"
                                    f"Quality: {quality}"
                                    f"Retain: {retain}"
                                    f"identifier: {identifier}"
                                    )

        except Exception as e:
            logger_alarm.error(f"Error while processing event notification from {self.address} - Error: {e}")
            logger_alarm.error(traceback.format_exc())
            raise e


async def monitor_alarms():
    """
    This function monitors alarms by creating a subscription for each unit in the database.
    Args:
        add_opcua_alarm_to_datagrid_function (function): Callback function that handles adding alarm to data grid.
    """

    from .data_encrypt import DataEncrypt
    from .ms_sql import get_units
    data_encrypt = DataEncrypt()
    opcua_config = data_encrypt.encrypt_credentials("opcua_config.json", "OPCUA_KEY")

    encrypted_username = opcua_config["username"]
    encrypted_password = opcua_config["password"]

    ip_address = []
    unit_id = []
    tasks = []

    units =  await get_units()

    ip_address = [address[1] for address in units]
    unit_id = [unit[0] for unit in units]

    for adresses, unit_id in zip(ip_address, unit_id):
        tasks.append(asyncio.create_task(subscribe_to_server(adresses, 
                                                             encrypted_username, encrypted_password)))

    await asyncio.gather(*tasks)