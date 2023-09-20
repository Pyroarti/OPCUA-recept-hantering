import json
from tkinter.messagebox import showinfo
from pathlib import Path
import re
import asyncio
from pyodbc import Error as PyodbcError

from asyncua import ua, Node, Client

from .create_log import setup_logger
from .opcua_client import get_servo_steps, connect_opcua, write_tag
from .sql_connection import SQLConnection


logger = setup_logger(__name__)


async def from_units_to_sql_stepdata(selected_id, texts, recipe_structure_id):
    """
    Iterates through selected units, retrieves their step data and writes it to SQL.

    Args:
        selected_id (str): Selected recipe id from the GUI
        texts (dict): Language for the GUI
        recipe_structure_id (str): The selected recipe structure id
    """


    ip_address_list = []
    unit_ids_list = []
    data_origin_list = []

    recipe_lengths_per_unit = {}

    struct_data_rows = await get_recipe_structures_map()

    # Fetching unit information based on the structure id
    for row in struct_data_rows:
        unit_id, unit_name, structure_id ,data_origin, url = row
        if structure_id == recipe_structure_id:
            unit_ids_list.append(unit_id)
            ip_address_list.append(url)
            data_origin_list.append(data_origin)

    cursor = None
    cnxn = None

    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)

    except PyodbcError as e:
        logger.warning(f"Error in database connection: {e}")

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")

    if cursor and cnxn:

        # Define the stored procedure and parameter names
        stored_procedure_name = 'add_value'
        tag_name_param_name = 'TagName'
        tag_value_param_name = 'TagValue'
        tag_datatype_param_name = 'TagDataType'
        recipe_id_param_name = "RecipeID"
        unit_id_param_name = "UnitID"

        all_units_processed_successfully = True

        # Iterating through units and executing SQL stored procedure based on their step data
        for adresses, unit_id_to_get, data_place in zip(ip_address_list,
                                                        unit_ids_list,data_origin_list):
            logger.info(f"Connecting to unit id: {unit_id_to_get}")

            if data_place == 'ns=3;s="StepData"."RunningSteps"."Steps"':
                steps = await get_servo_steps(adresses, data_place)

                if steps:
                    try:
                        recipe_length = (len(steps))
                    except TypeError:
                        recipe_length = (0 + unit_id_to_get)

                    if unit_id_to_get == 1:
                        unitname = "SMC1"
                    elif unit_id_to_get == 2:
                        unitname = "SMC2"
                    elif unit_id_to_get == 3:
                        unitname = "Master"
                    else:
                        unitname = f"Unknown unit {unit_id_to_get}"

                    recipe_lengths_per_unit[unitname] = recipe_length

                    for step in steps:
                        #logger.info(step)
                        for prop in steps[step]:
                            #logger.info(prop)
                            tag_name: str = steps[step][prop]["Node"].nodeid.Identifier
                            tag_value = steps[step][prop]["Value"]
                            tag_datatype = steps[step][prop]["Datatype"].name
                            recipe_id = selected_id

                            try:
                                cursor.execute(f"EXEC {stored_procedure_name} \
                                        @{tag_name_param_name}='{tag_name}', \
                                        @{tag_value_param_name}={tag_value}, \
                                        @{tag_datatype_param_name}={tag_datatype}, \
                                        @{recipe_id_param_name}={recipe_id},\
                                        @{unit_id_param_name}={unit_id_to_get};")
                            except Exception as exception:
                                logger.warning(exception)
                                all_units_processed_successfully = False

                else:
                # Om någon ser detta, förlåt till den som måste fixa mina hårdkodade värden.
                    match unit_id:
                        case 1:
                            unitname = "SMC1"
                        case 2:
                            unitname = "SMC2"
                        case 3:
                            unitname = "Master"
                            continue
                    showinfo(title="Info",
                             message= texts["show_info_Could_not_load_data_from"] + unitname)
                    all_units_processed_successfully = False

            else:
                from .opcua_client import get_opcua_value

                all_units_processed_successfully, opcua_value, datatype = await get_opcua_value(adresses,data_place)
                logger.info(f"OPCUA value received: {opcua_value}, datatype: {datatype}, from {adresses}")

                try:
                    # Minns inte vad den är till för men snälla rör inte den :)
                    data_place = re.sub(r'^.*?"', '"', data_place)
                except Exception:
                    pass

                try:
                    cursor.execute(f"EXEC {stored_procedure_name} \
                            @{tag_name_param_name}='{data_place}', \
                            @{tag_value_param_name}={opcua_value}, \
                            @{tag_datatype_param_name}={datatype}, \
                            @{recipe_id_param_name}={selected_id},\
                            @{unit_id_param_name}={unit_id_to_get};")
                except Exception as exception:
                    logger.warning(f"Failed to execute stored procedure for unit_id: {unit_id_to_get}. Error: {str(exception)}")
                    all_units_processed_successfully = False

                finally:
                    if cursor and cnxn:
                        sql_connection.disconnect_from_database(cursor, cnxn)

    if all_units_processed_successfully:

        message_detail = (
            f"SMC1 Steg: {recipe_lengths_per_unit.get('SMC1', 'N/A')}\n"
            f"SMC2 Steg: {recipe_lengths_per_unit.get('SMC2', 'N/A')}\n"
            f"Tryck ok för att börja kontrollera alla steg i receptet."
        ) 

        showinfo(title='Information',
             message=texts["show_info_from_all_units_processed_successfully"],
             detail=message_detail)

        logger.info(f"Data loaded successfully for selected recipe ID: {selected_id}")

        recipe_checked = check_recipe_data(selected_id)

        db_opcua_not_same = await db_opcua_data_checker(selected_id, recipe_structure_id, texts)

        successfully_updated_recipe_last_saved = await update_recipe_last_saved(selected_id)
        
        if successfully_updated_recipe_last_saved:

            if db_opcua_not_same:
                showinfo(title="Info", message= db_opcua_not_same)
            else:
                showinfo(title="Info", message= texts["show_info_data_in_database_and_opcua_is_the_same"])
        
        else:
            showinfo(title="Info", message= texts["general_error"])

        return recipe_checked

    else:
        logger.warning("Problem with loading data to sql")
        showinfo(title='Information',
                 message=texts["show_info_from_all_units_processed_not_successfully"])
        return None


async def from_sql_to_units_stepdata(step_data, texts, selected_name):
    from src.data_encrypt import DataEncrypt

    """
    Iterates through the units and writes the step data from SQL to them.

    Args:
        step_data (list): List of step data from the SQL
        texts (dict): Language for the GUI
        selected_name (str): The selected name from the GUI
    """

    data_encrypt = DataEncrypt()
    opcua_config = data_encrypt.encrypt_credentials("opcua_config.json", "OPCUA_KEY")
    encrypted_username = opcua_config["username"]
    encrypted_password = opcua_config["password"]

    all_units_processed_successfully = True
    units = await get_units()

    for unit in units:
        unit_id, address = unit

        # Clearning runnin steps before putting new in
        if unit_id != 3:
            fault = await wipe_running_steps(address,encrypted_username,encrypted_password)

        if not fault or unit_id == 3:

            filtered_data = [row for row in step_data if row[2] == unit_id]
            if not filtered_data:
                continue

            logger.info(f"Connecting to unit id: {unit_id}")
            client:Client = await connect_opcua(address, encrypted_username, encrypted_password)

            if client:
                logger.info(f"Connected to OPCUA server at {address}")
            else:
                logger.warning(f"Failed to connect to OPCUA server at {address}")
                continue

            output_path = Path(__file__).parent.parent
            with open(output_path / "configs" / "name_space.json", encoding="UTF8") as namespace:
                data = json.load(namespace)
                siemens_namespace_uri = data['siemens_namespace_uri']

            if client is not None:
                namespace_index = await client.get_namespace_index(siemens_namespace_uri)
            else:
                match unit_id:
                    case 1:
                        unitname = "SMC1"
                    case 2:
                        unitname = "SMC2"
                    case 3:
                        unitname = "Master"

                showinfo(title="Info", message=texts["show_info_Could_not_load_data_to"] + unitname)
                all_units_processed_successfully = False
                continue

            logger.info("Connected and session activated")

            # Writing step data to plc
            for row in filtered_data:
                print(row)

                _, _, _, tag_name, tag_value, tag_datatype, _  = row
                tag_name = f"ns={namespace_index};s={tag_name}"
                node_id = ua.NodeId.from_string(string=tag_name)
                node: Node = client.get_node(node_id)
                result, fault = await write_tag(client, tag_name, tag_value)

                logger.info(f"{result} {row}")

            # Writing the recipe name to PLC
            #try:
            #    recipe_name_adress = 'ns=3;s="StepData"."RunningSteps"."Name"'
            #    succes_writing_name = await write_tag(client, recipe_name_adress, selected_name)
            #except Exception:
            #    continue

            await client.disconnect()

        else:
            logger.info("There was a problem while wiping the data or so is the case for unit 3 (Master)")
            await client.disconnect()

    if all_units_processed_successfully and not fault :
        
        showinfo(title='Information', message=texts["show_info_to_all_units_processed_successfully"])
        await client.disconnect()
    else:
        logger.warning("Problem with loading data to units")
        showinfo(title='Information', message=texts["show_info_to_all_units_processed_not_successfully"])
        await client.disconnect()

    await client.disconnect()
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
        logger.warning(f"Error in database connection: {e}")

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)

    if units:
        return units

    else:
        logger.warning("No units were fetched from the database")
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

        cursor.execute('SELECT Unit_Id,UnitName, RecipeStructure_Id, UnitTagName, URL  FROM viewRecipeStructuresMap')

        struct_data = cursor.fetchall()

    except PyodbcError as e:
            logger.warning(f"Error in database connection: {e}")

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)

    if struct_data:
        logger.info(f"Fetched {struct_data} recipe structure mappings from the database")
        return struct_data
    else:
        logger.warning("No recipe structure mappings were fetched from the database")
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
            logger.warning(exception)

    else:
        logger.warning("Error while trying to connect to opcua servers to clean data")


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
            SELECT TOP (1000) [UnitID], [TagName], [TagValue], [TagDataType], [UnitName]
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
                    logger.warning(f"One or more fields are None in row: {row}")
                    return False
            return True

    except PyodbcError as e:
        logger.warning(f"Error in database connection: {e}")
        return False

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")
        return False

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")
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
        True if data is the same in both places, False otherwise.
    """

    from .opcua_client import get_opcua_value

    cursor = None
    cnxn = None

    try:
        sql_connection = SQLConnection()
        sql_credentials = sql_connection.get_database_credentials("sql_config.json", "SQL_KEY")
        cursor, cnxn = sql_connection.connect_to_database(sql_credentials)


        struct_data_rows = await get_recipe_structures_map()

        data_difference = []

        opcua_results = {}

        pattern = re.compile(r'ns=\d+;s="(.+)"')

        # Fetching unit information based on the structure id
        for row in struct_data_rows:
            unit_id, unit_name, structure_id ,data_origin, url = row
            if structure_id == recipe_structure_id and unit_name != "Master":

                servo_steps = await get_servo_steps(url, data_origin)


                for key1, inner_dict in servo_steps.items():
                    for key2, info_dict in inner_dict.items():
                        node_obj = info_dict['Node']
                        node_id = node_obj.nodeid
                        identifier = node_id.Identifier 
                        value = str(info_dict['Value'])
                        opcua_results[identifier] = value


                query = """
                SELECT TOP (1000) [UnitID], [TagName], [TagValue], [TagDataType]
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
            return False

        for row in rows:

            if None in row:
                logger.warning(f"One or more fields are None in row: {row}")
                return False

            unit_id, tag_name, tag_value, tag_datatype = row
            db_results[tag_name] = tag_value

        for tag_name, tag_value in db_results.items():
            logger.info(f"Checking tag_name: {tag_name}")
            opcua_tag_value = opcua_results.get(tag_name, None)
            logger.info(f"DB value for {tag_name}: {tag_value}")
            logger.info(f"OPCUA value for {tag_name}: {opcua_tag_value}")

            if opcua_tag_value is None:
                logger.warning(f"{tag_name} exists in database but not in OPCUA")
                data_difference.append(f"{tag_name} exists in database but not in OPCUA")

            elif tag_value != opcua_tag_value:
                logger.warning(f"Tag value in database: {tag_value} is not the same as in OPCUA: {opcua_tag_value}")
                db_opcua_missmatch = (f"Tag value in database: {tag_value} is not the same as in OPCUA: {opcua_tag_value}")
                data_difference.append(db_opcua_missmatch)

            else:
                pass
                #logger.info(f"Tag value in database: {tag_value} is the same as in OPCUA: {opcua_tag_value}")

        return data_difference

    except PyodbcError as e:
            logger.warning(f"Error in database connection: {e}")
            showinfo(title="Info", message=texts["error_with_database"])

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")
        showinfo(title="Info", message=texts["error_with_database"])

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")
        showinfo(title="Info", message=e)

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
        logger.warning(f"Error in database connection: {e}")

    except IndexError:
        logger.warning("Database credentials seem to be incomplete.")

    except Exception as e:
        logger.warning(f"An unexpected error occurred: {e}")

    finally:
        if cursor and cnxn:
            sql_connection.disconnect_from_database(cursor, cnxn)
