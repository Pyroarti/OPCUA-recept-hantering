import json
from tkinter.messagebox import showinfo
from pathlib import Path
import re
import asyncio
from pyodbc import Error as PyodbcError
from typing import List, Tuple, Union

from asyncua import ua, Node, Client

from .create_log import setup_logger
from .opcua_client import get_servo_steps, connect_opcua, write_tag
from .sql_connection import SQLConnection


logger = setup_logger("MS_SQL")


STEPDATA_ORIGIN = 'ns=3;s="StepData"."RunningSteps"."Steps"'


async def fetch_unit_info(struct_data_rows: List[Tuple], recipe_structure_id: int) -> Tuple[List[str], List[int], List[str]]:
    unit_ids_list = [row[0] for row in struct_data_rows if row[2] == recipe_structure_id]
    ip_address_list = [row[4] for row in struct_data_rows if row[2] == recipe_structure_id]
    data_origin_list = [row[3] for row in struct_data_rows if row[2] == recipe_structure_id]
    return ip_address_list, unit_ids_list, data_origin_list


def establish_sql_connection():
    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)
        return sql_connection, cursor, cnxn
    
    except PyodbcError as e:
        logger.error(f"Error in database connection: {e}")
        return None, None, None

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")
        return None, None, None

    except Exception as e:
        logger.error(f"Error establishing SQL connection: {e}")
        return None, None, None


def get_unit_name(unit_id):
    unit_mapping = {
        1: "SMC1",
        2: "SMC2",
        3: "Master"
    }
    return unit_mapping.get(unit_id, f"Unknown unit {unit_id}")


def insert_step_data_into_sql(cursor, steps, selected_id, unit_id_to_get):

    stored_procedure_name = 'add_value'
    tag_name_param_name = 'TagName'
    tag_value_param_name = 'TagValue'
    tag_datatype_param_name = 'TagDataType'
    recipe_id_param_name = "RecipeID"
    unit_id_param_name = "UnitID"

    recipe_lengths_per_unit = {}
    all_units_processed_successfully = True

    recipe_length = len(steps)
    unitname = get_unit_name(unit_id_to_get)
    recipe_lengths_per_unit[unitname] = recipe_length
    for step_dict in steps:
        logger.info(f"Processing step: {step_dict}")
        for prop, prop_data in step_dict.items():
            tag_name = prop_data["Node"].nodeid.Identifier
            tag_value = prop_data["Value"]
            tag_datatype = prop_data["Datatype"].name
            recipe_id = selected_id

            try:
                cursor.execute(f"EXEC {stored_procedure_name} \
                        @{tag_name_param_name}='{tag_name}', \
                        @{tag_value_param_name}={tag_value}, \
                        @{tag_datatype_param_name}={tag_datatype}, \
                        @{recipe_id_param_name}={recipe_id},\
                        @{unit_id_param_name}={unit_id_to_get};")
            except Exception as exception:
                logger.error(exception)
                all_units_processed_successfully = False
    return all_units_processed_successfully, recipe_lengths_per_unit



def insert_opcua_value_into_sql(cursor, data_place, opcua_value, datatype, selected_id, unit_id_to_get):

    stored_procedure_name = 'add_value'
    tag_name_param_name = 'TagName'
    tag_value_param_name = 'TagValue'
    tag_datatype_param_name = 'TagDataType'
    recipe_id_param_name = "RecipeID"
    unit_id_param_name = "UnitID"

    all_units_processed_successfully = True
    data_place = re.sub(r'^.*?"', '"', data_place)
    try:
        cursor.execute(f"EXEC {stored_procedure_name} \
                        @{tag_name_param_name}='{data_place}', \
                        @{tag_value_param_name}={opcua_value}, \
                        @{tag_datatype_param_name}={datatype}, \
                        @{recipe_id_param_name}={selected_id},\
                        @{unit_id_param_name}={unit_id_to_get};")
    except Exception as exception:
        logger.error(f"Failed to execute stored procedure for unit_id: {unit_id_to_get}. Error: {str(exception)}")
        all_units_processed_successfully = False
    return all_units_processed_successfully


async def from_units_to_sql_stepdata(selected_id, texts, recipe_structure_id):
    """
    Iterates through selected units, retrieves their step data, and writes it to SQL.

    Args:
        selected_id (str): Selected recipe id from the GUI
        texts (dict): Language for the GUI
        recipe_structure_id (str): The selected recipe structure id
    """
    from .opcua_client import get_opcua_value
 
    struct_data_rows = await get_recipe_structures_map()
    if struct_data_rows:
        ip_address_list, unit_ids_list, data_origin_list = await fetch_unit_info(struct_data_rows, recipe_structure_id)
    else:
        logger.error("No recipe structure mappings were fetched from the database")
        display_info(title="Info", message=texts["Show_info_general_sql_error"])
        return None

    sql_connection, cursor, cnxn = establish_sql_connection()
    if not cursor or not cnxn:
        logger.error("Database connection failed.")
        display_info(title="Info", message=texts["Show_info_general_sql_error"])
        return None

    all_units_processed_successfully = True
    recipe_lengths_per_unit = {}

    # Iterating through units and executing SQL stored procedure based on their step data
    for address, unit_id, data_origin in zip(ip_address_list, unit_ids_list, data_origin_list):
        logger.info(f"Connecting to unit id: {unit_id}")

        if data_origin == STEPDATA_ORIGIN:
            steps = await get_servo_steps(address, data_origin)

            if steps:
                success, lengths = insert_step_data_into_sql(cursor, steps, selected_id, unit_id)
                all_units_processed_successfully &= success
                recipe_lengths_per_unit.update(lengths)
            else:
                unit_name = get_unit_name(unit_id)
                display_info(title="Info", message=texts["show_info_Could_not_load_data_from"] + unit_name)
                all_units_processed_successfully = False

        else:
            success, value, datatype = await get_opcua_value(address, data_origin)
            if success == False:
                logger.error(f"Failed to get OPCUA value for unit_id: {unit_id}")
                display_info(title="Info", message=texts["show_info_Could_not_load_data_from"] + get_unit_name(unit_id))
                return None

            all_units_processed_successfully &= success

            success = insert_opcua_value_into_sql(cursor, data_origin, value, datatype, selected_id, unit_id)
            all_units_processed_successfully &= success

    cursor.commit()
    if cursor and cnxn:
        sql_connection.disconnect_from_database(cursor, cnxn)

    if all_units_processed_successfully:
        message_detail = (
            f"SMC1 Steg: {recipe_lengths_per_unit.get('SMC1', 'N/A')}\n"
            f"SMC2 Steg: {recipe_lengths_per_unit.get('SMC2', 'N/A')}\n"
            f"Tryck ok för att börja kontrollera alla steg i receptet."
        )
        display_info(title='Information',
                     message=texts["show_info_from_all_units_processed_successfully"],
                     detail=message_detail)

        logger.info(f"Data loaded successfully for selected recipe ID: {selected_id}")

        recipe_checked = check_recipe_data(selected_id)

        db_opcua_not_same, error = await db_opcua_data_checker(selected_id, recipe_structure_id, texts)

        if error:
            display_info(title="Info", message=texts["general_error"])
            return None
        
        successfully_updated_recipe_last_saved = await update_recipe_last_saved(selected_id)

        if successfully_updated_recipe_last_saved:
            if db_opcua_not_same:
                display_info(title="Info", message=db_opcua_not_same)
            else:
                display_info(title="Info", message=texts["show_info_data_in_database_and_opcua_is_the_same"])
        else:
            display_info(title="Info", message=texts["general_error"])

        return recipe_checked
    else:
        logger.error("Problem with loading data to sql")
        display_info(title='Information', message=texts["show_info_from_all_units_processed_not_successfully"])
        return None


def display_info(title, message, detail=None):
    """Displays a message box with the given title, message and detail."""
    showinfo(title=title, message=message, detail=detail)


async def write_data_to_unit(client, namespace_index, filtered_data):
    for row in filtered_data:
        _, _, _, tag_name, tag_value, tag_datatype, _  = row
        tag_name = f"ns={namespace_index};s={tag_name}"
        result, fault = await write_tag(client, tag_name, tag_value)
        if fault:
            logger.error(f"Failed to write {tag_name} with value {tag_value}")
            return False
    return True


async def connect_to_opcua_server(address, encrypted_username, encrypted_password):
    client: Client = await connect_opcua(address, encrypted_username, encrypted_password)
    if not client:
        logger.error(f"Failed to connect to OPCUA server at {address}")
        return None

    logger.info(f"Connected to OPCUA server at {address}")
    return client


async def from_sql_to_units_stepdata(step_data, texts, selected_name):
    from .data_encrypt import DataEncryptor

    data_encrypt = DataEncryptor()
    opcua_config = data_encrypt.encrypt_credentials("opcua_server_config.json", "OPCUA_KEY")

    all_units_processed_successfully = True
    units = await get_units()

    for unit in units:
        unit_id, address = unit

        if unit_id != 3:
            fault = await wipe_running_steps(address, opcua_config["username"], opcua_config["password"])
            if fault:
                logger.info("There was a problem while wiping the data")
                continue

        client = await connect_to_opcua_server(address, opcua_config["username"], opcua_config["password"])
        if not client:
            showinfo(title="Info", message=texts["show_info_Could_not_load_data_to"] + get_unit_name(unit_id))
            all_units_processed_successfully = False
            continue

        output_path = Path(__file__).parent.parent
        with open(output_path / "configs" / "name_space.json", encoding="UTF8") as namespace:
            data = json.load(namespace)
            siemens_namespace_uri = data['siemens_namespace_uri']

        namespace_index = await client.get_namespace_index(siemens_namespace_uri)
        filtered_data = [row for row in step_data if row[2] == unit_id]
        success = await write_data_to_unit(client, namespace_index, filtered_data)

        all_units_processed_successfully &= success

        await client.disconnect()

    if all_units_processed_successfully:
        showinfo(title='Information', message=texts["show_info_to_all_units_processed_successfully"])
    else:
        logger.error("Problem with loading data to units")
        showinfo(title='Information', message=texts["show_info_to_all_units_processed_not_successfully"])

    return all_units_processed_successfully


async def get_units():
    """Fetches the ids and ip addresses from units hosting OPCUA servers from a SQL database.

    Returns:
        list: List of tuples containing unit ids and ip addresses
    """

    cursor = None
    cnxn = None

    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

        cursor.execute('SELECT * FROM viewUnits')

        units = cursor.fetchall()

    except PyodbcError as e:
        logger.error(f"Error in database connection: {e}")

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)

    if units:
        return units

    else:
        logger.error("No units were fetched from the database")
        return None


async def get_recipe_structures_map():

    """
    Fetches the mapping between unit ids, recipe structure ids, tags and URLs from a SQL database.

    Returns:
        list: List of tuples containing unit ids, recipe structure ids, tags and URLs
    """

    cursor = None
    cnxn = None

    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

        cursor.execute('SELECT Unit_Id, UnitName, RecipeStructure_Id, UnitTagName, URL  FROM viewRecipeStructuresMap')

        struct_data = cursor.fetchall()

    except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)

    if struct_data:
        logger.info(f"Fetched {struct_data} recipe structure mappings from the database")
        return struct_data
    else:
        logger.error("No recipe structure mappings were fetched from the database")
        return None


async def wipe_running_steps(address,encrypted_username,encrypted_password):
    """
    Connects to the specified OPC UA servers and clears running steps.

    Args:
        address (str): The address of the OPC UA server
        encrypted_username (str): The encrypted username for the OPC UA server
        encrypted_password (str): The encrypted password for the OPC UA server

    Returns:
        bool: Fault status of the operation

    """

    client:Client = await connect_opcua(address, encrypted_username, encrypted_password)

    if client:
        try:
            logger.info(f"Connected to OPCUA server at {address} to clear running steps")
            opcua_adress = 'ns=3;s="Recipe_Handler"."External"."ClearRunningSteps"'
            succes_writing_name, fault = await write_tag(client, opcua_adress, True)

            await asyncio.sleep(2)

            await client.disconnect()

            return fault
        except Exception as exception:
            logger.error(exception)

    else:
        logger.error("Error while trying to connect to opcua servers to clean data")


def check_recipe_data(selected_id):
    """
    Checks the data of the selected recipe. To see if there is data in the database.
    """

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
            """

            params = (selected_id,)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            if not rows:
                return False

            for row in rows:
                if None in row:
                    logger.error(f"One or more fields are None in row: {row}")
                    return False
            return True

    except PyodbcError as e:
        logger.error(f"Error in database connection: {e}")
        return False

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")
        return False

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return False

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)


async def db_opcua_data_checker(recipe_id, recipe_structure_id, texts):
    """
    Checks the step data in the database and compares it with the OPCUA data.

    Parameters:
        recipe_id: The Recipe ID used for querying the SQL database.

    Returns:
        The difference between the OPCUA data and the database data if there are none returns empty list.
    """

    from .opcua_client import get_opcua_value

    cursor = None
    cnxn = None

    sql_connection, cursor, cnxn = establish_sql_connection()
    if not cursor or not cnxn:
        logger.error("Database connection failed.")
        display_info(title="Info", message=texts["Show_info_general_sql_error"])
        return [], True

    try:

        struct_data_rows = await get_recipe_structures_map()

        data_difference = []

        opcua_results = {}

        pattern = re.compile(r'ns=\d+;s="(.+)"')

        # Fetching unit information based on the structure id
        for row in struct_data_rows:
            unit_id, unit_name, structure_id ,data_origin, url = row
            if structure_id == recipe_structure_id and unit_name != "Master":

                servo_steps = await get_servo_steps(url, data_origin)

                if not servo_steps:
                    logger.error(f"Failed to fetch servo steps from {url} with data origin {data_origin}")
                    display_info(title="Info", message=texts["Show_info_general_plc_error"])
                    return [], True
                for item in servo_steps:
                    for key, info_dict in item.items():

                        node_obj = info_dict['Node']
                        node_id = node_obj.nodeid
                        identifier = node_id.Identifier
                        value = str(info_dict['Value'])
                        opcua_results[identifier] = value


                query = """
                SELECT [UnitID], [TagName], [TagValue], [TagDataType]
                FROM [RecipeDB].[dbo].[viewValues]
                WHERE RecipeID = ? AND UnitID = ?
                """
                params = (recipe_id,unit_id)
                cursor.execute(query, params,)
                rows = cursor.fetchall()

            elif structure_id == recipe_structure_id and unit_name == "Master":
                master_data = await get_opcua_value(url, data_origin)

                match = pattern.match(data_origin)
                if match:
                    clean_data_origin = match.group(1)
                    clean_data_origin = f'"{clean_data_origin}"'
                    opcua_results[clean_data_origin] = str(master_data[1])
                else:
                    opcua_results[data_origin] = str(master_data[1])  # Fallback if regex doesn't match

        db_results = {}
        if not rows:
            return [], True

        for row in rows:

            if None in row:
                logger.error(f"One or more fields are None in row: {row}")
                return [], True

            unit_id, tag_name, tag_value, tag_datatype = row
            db_results[tag_name] = tag_value

        for tag_name, tag_value in db_results.items():
            logger.info(f"Checking tag_name: {tag_name}")
            opcua_tag_value = opcua_results.get(tag_name, None)
            logger.info(f"DB value for {tag_name}: {tag_value}")
            logger.info(f"OPCUA value for {tag_name}: {opcua_tag_value}")

            if opcua_tag_value is None:
                logger.error(f"{tag_name} exists in database but not in OPCUA")
                data_difference.append(f"{tag_name} exists in database but not in OPCUA")

            elif tag_value != opcua_tag_value:
                logger.error(f"Tag value in database: {tag_value} is not the same as in OPCUA: {opcua_tag_value}")
                db_opcua_missmatch = (f"Tag value in database: {tag_value} is not the same as in OPCUA: {opcua_tag_value}")
                data_difference.append(db_opcua_missmatch)

            else:
                pass
                #logger.info(f"Tag value in database: {tag_value} is the same as in OPCUA: {opcua_tag_value}")

        return data_difference, False

    except PyodbcError as e:
            logger.error(f"Error in database connection: {e}")
            showinfo(title="Info", message=texts["error_with_database"])
            return [], True

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")
        showinfo(title="Info", message=texts["error_with_database"])
        return [], True

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        showinfo(title="Info", message=e)
        return [], True

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)


async def update_recipe_last_saved(recipe_id):
    """
    Updates the last saved date for a recipe to database.
    """

    cursor = None
    cnxn = None

    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

        if cursor and cnxn:

            query = """
            UPDATE [RecipeDB].[dbo].[tblRecipe]
            SET [RecipeLastDataSaved] = GETDATE()
            WHERE [id] = ?
            """

            params = (recipe_id,)
            cursor.execute(query, params)
            cnxn.commit()
            return True

        else:
            return False

    except PyodbcError as e:
        logger.error(f"Error in database connection: {e}")

    except IndexError:
        logger.error("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)
