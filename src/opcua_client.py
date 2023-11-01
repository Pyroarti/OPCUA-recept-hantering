import json
from asyncua import Client, ua, Node
import asyncua.ua.uaerrors._auto as uaerrors
import asyncua.common

from .create_log import setup_logger
from .data_encrypt import DataEncryptor


logger = setup_logger('Opcua_client')


async def get_node_children(node: Node, nodes=None):
    """
    Get recursively all children of a node
    """
    if nodes is None:
        nodes = [node]
    for child in await node.get_children():
        nodes.append(child)
        await get_node_children(child, nodes)
    return nodes


async def get_children_values(node: Node, result: dict = None) -> dict:
    if result is None:
        result = {}
    nodes = await node.get_children()

    for child in nodes:
        if await child.read_node_class() == ua.NodeClass.Variable:
            value = await child.read_value()
            display_name = await child.read_display_name()
            if display_name.Text not in result:
                result[display_name.Text] = []
            result[display_name.Text].append(value)

        elif await child.read_node_class() == ua.NodeClass.Object:
            if await child.read_display_name().Text not in result:
                result[await child.read_display_name().Text] = []
            result[await child.read_display_name().Text].append(await get_children_values(child))

    return result


async def get_stepdata(node_steps: Node) -> json:
    """
    Get data from specific steps within the given node.

    :param nodeSteps: Node containing the step data
    :return: JSON object containing the result, or None if no result found
    """

    result = []
    logger.info("Getting step data...")

    node_step = await node_steps.get_children()
    if node_step:
        for array_item in node_step:
            props_of_array_item = await array_item.get_children()
            path_array_item = await array_item.get_path()

            if any('[0]' in str(path) for path in path_array_item):
                logger.info(f"Skipping {path_array_item} as it contains '[0]'")
                continue  # Skip the rest of the loop for this item

            item_data = {}

            if props_of_array_item:
                for props in props_of_array_item:
                    if await props.read_node_class() == ua.NodeClass.Variable:
                        tag_value = await props.read_value()
                        tag_datatype = await props.read_data_type_as_variant_type()
                        display_name = await props.read_display_name()

                        if display_name.Text not in item_data:
                            item_data[display_name.Text] = {
                                "Node": props,
                                "Value": tag_value,
                                "Datatype": tag_datatype
                            }

            if item_data:  # Check if item_data has any entries
                result.append(item_data)

    if result:
        logger.info("Successfully retrieved step data.")
        return result

    logger.error("No step data found.")
    return None



async def connect_opcua(url, encrypted_username, encrypted_password):

    """
    Connect to an OPC UA server.

    :param url: Server URL
    :param encrypted_username: Encrypted username
    :param encrypted_password: Encrypted password
    :return: Client object if connected, None otherwise
    """
 
    client = Client(url=url, timeout=10, watchdog_intervall=10.0)

    try:
        logger.info(f"Connecting to OPC UA server at {url}")
        client.set_user(username=encrypted_username)
        client.set_password(pwd=encrypted_password)
        await client.connect()
        logger.info("Successfully connected to OPC UA server.")

    except ua.uaerrors.BadUserAccessDenied as exeption:
        logger.error(f"BadUserAccessDenied: {exeption}")
        return None

    except ua.uaerrors.BadSessionNotActivated as exeption:
        logger.error(f"Session activation error: {exeption}")
        return None

    except ua.uaerrors.BadIdentityTokenRejected as exeption:
        logger.error(f"Identity token rejected. Check username and password.: {exeption}")
        return None

    except ua.uaerrors.BadIdentityTokenInvalid as exeption:
        logger.error(f"Bad Identity token invalid. Check username and password.: {exeption}")
        return None

    except ConnectionError as exeption:
        logger.error(f"Connection error: Please check the server url. Or other connection properties: {exeption}")
        return None

    except ua.UaError as exeption:
        logger.error(f"General OPCUA error {exeption}")
        return None

    except Exception as exeption:
        logger.error(f"Error in connection: {exeption} Type: {type(exeption)}")
        return None

    return client

async def find_node_by_tag_name(node: Node, tag_name):
    if node is None:
        return None

    node_browse_name = await node.read_browse_name()
    if node_browse_name.Name == tag_name:
        return node

    # Search for the tag name in the children of the current node
    children = await node.get_children()
    for child in children:
        found_node = await find_node_by_tag_name(child, tag_name)
        if found_node is not None:
            return found_node

    # Tag name not found in current node or its children
    return None


async def write_tag(client: Client, tag_name, tag_value):
    """
    Write a value to a specific tag within the client.

    :param client: The client object
    :param tag_name: The tag name to write to
    :param tag_value: The value to write
    :return: A tuple containing result message and fault flag
    """
    result = "Tag not found"
    fault = False

    try:
        node_id: Node = ua.NodeId.from_string(tag_name)
        node: Node = client.get_node(node_id)
        logger.info(f"Writing value {tag_value} to tag {tag_name} from {node_id},{node}")

    except Exception as exeption:
        logger.error(exeption)
        await client.disconnect()
        fault = True
        return result, fault

    # Write the value to the node
    if node_id is not None:
        data_value = None
        try:

            # Define conversion functions
            def to_bool(value):
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    return value.lower() == "true"
                else:
                    raise ValueError("Invalid type for conversion to bool")


            def to_float(value):
                return float(value)

            def to_int(value):
                return int(value)

            # Define data type to conversion function mapping
            conversion_map = {
                ua.VariantType.Boolean: to_bool,
                ua.VariantType.Float: to_float,
                ua.VariantType.Int16: to_int,
                ua.VariantType.Int32: to_int,
                ua.VariantType.Int64: to_int,
                ua.VariantType.UInt16: to_int,
                ua.VariantType.UInt32: to_int,
                ua.VariantType.UInt64: to_int,
            }

            # Convert tag value to data value
            data_type = await node.read_data_type_as_variant_type()
            if data_type in conversion_map:
                conversion_func = conversion_map[data_type]
                if isinstance(tag_value, str) or isinstance(tag_value, int):
                    tag_value = conversion_func(tag_value)
                if isinstance(tag_value, bool) or isinstance(tag_value, float) or isinstance(tag_value, int):
                    data_value = ua.DataValue(ua.Variant(tag_value, data_type))
            elif data_type == ua.VariantType.String:
                if isinstance(tag_value, str):
                    data_value = ua.DataValue(ua.Variant(tag_value, data_type))

            result = "Tag found but no correct tag value"
        except Exception as exeption:
            await client.disconnect()
            fault = True
            logger.error(f"Error converting data type to ua.Variant: {exeption}")
            return result, fault

        if data_value is not None:

            try:
                await node.write_value(data_value)
                result = "Success finding tag and writing value"
                logger.info(f"Successfully wrote value to tag: {tag_name},{tag_value}.")
            except Exception as exeption:
                fault = True
                await client.disconnect()
                logger.error(f"Error writing value to tag: {tag_name},{tag_value}, from {node_id}. {exeption}")
                return result, fault

    return result, fault


async def get_servo_steps(ip_address, data_origin):

    """
    Retrieve servo steps from a specified address.

    :param ip_address: The IP address
    :param data_origin: The origin of the data
    :return: The children values if found
    """

    logger.info(f"Getting servo steps from {ip_address}...")

    data_encrypt = DataEncryptor()
    opcua_config = data_encrypt.encrypt_credentials("opcua_server_config.json", "OPCUA_KEY")
    for server in opcua_config["servers"]:
        encrypted_username = server["username"]
        encrypted_password = server["password"]
    url = ip_address

    client:Client = await connect_opcua(url, encrypted_username, encrypted_password)
    if client is not None:
        logger.info("Connected and session activated")

        try:

            node_id = ua.NodeId.from_string(data_origin)
            node_steps = client.get_node(node_id)

            children_values = await get_stepdata(node_steps)

            if children_values:
                logger.info("Successfully retrieved servo steps.")
                await client.disconnect()
                logger.info("Client disconnected")
               
                return children_values

            logger.error("Failed to retrieve servo steps.")
            await client.disconnect()
            logger.info("Client disconnected")
            return None

        except AttributeError as exeption:
            logger.error(f"AttributeError:{exeption}")

        except ua.uaerrors._auto.BadNoMatch as exeption:
            logger.error(f"BadNoMatch. Ingen matchande variable:{exeption}")

        except TimeoutError as exeption:
            logger.error(f"Connection timeout: {str(exeption.args)}" if exeption else "Connection timeout: (empty message)")

        except Exception as exeption:
            logger.error(f"Error getting values: {str(exeption)},{type(exeption)}")


async def get_opcua_value(adress, data_place):

    """
    Get a specific value from the OPC UA server at a given address.

    :param adress: The address of the server
    :param data_place: The place of the data within the server
    :return: Tuple containing success flag, value, and data type if found
    """

    data_encrypt = DataEncryptor()
    opcua_config = data_encrypt.encrypt_credentials("opcua_server_config.json", "OPCUA_KEY")
    for server in opcua_config["servers"]:
        encrypted_username = server["username"]
        encrypted_password = server["password"]

    client:Client = await connect_opcua(adress, encrypted_username, encrypted_password)
    if client is not None:

        try:
            node_id = ua.NodeId.from_string(data_place)

            value_node = client.get_node(node_id)

            value = await value_node.read_value()

            node: Node = client.get_node(node_id)

            data_type = await node.read_data_type_as_variant_type()

            if data_type == ua.VariantType.Boolean:
                data_type = "Boolean"

            if data_type == ua.VariantType.Float:
                data_type = "Float"

            if data_type == ua.VariantType.UInt16:
                data_type = "UInt16"

            if data_type == ua.VariantType.UInt32:
                data_type = "Int32"

            if data_type == ua.VariantType.UInt64:
                data_type = "Int64"

            if data_type == ua.VariantType.String:
                data_type = "String"

            await client.disconnect()

            return True, value, data_type

        except Exception as exeption:
            logger.error(exeption)
            await client.disconnect()
            return False, None, None

    return False, None, None


async def data_to_webserver():

    """
    Retrieve specific data and send it to a webserver.

    :return: Produced value and to-do value if found
    """

    from .ms_sql import get_units
    units = await get_units()
    ip_address = units[2][1]

    data_encrypt = DataEncryptor()
    opcua_config = data_encrypt.encrypt_credentials("opcua_server_config.json", "OPCUA_KEY")
    for server in opcua_config["servers"]:
        encrypted_username = server["username"]
        encrypted_password = server["password"]

    client:Client = await connect_opcua(ip_address, encrypted_username, encrypted_password)

    if client is not None:

        try:
            produced_node_id = ua.NodeId.from_string('ns=3;s="E_Flex"."Info"."QuantityPartsMade"')
            to_do_node_id = ua.NodeId.from_string('ns=3;s="E_Flex"."Info"."QuantityOfPartsToMake"')

            produced_node = client.get_node(produced_node_id)
            to_do_node =  client.get_node(to_do_node_id)

            produced_value = await produced_node.get_value()
            to_do_value = await to_do_node.get_value()

            await client.disconnect()
            logger.info("Client disconnected")

            return produced_value, to_do_value

        except AttributeError as exeption:
            logger.warning(f"AttributeError:{exeption}")

        except ua.uaerrors._auto.BadNoMatch as exeption:
            logger.warning(f"BadNoMatch. Ingen matchande variable:{exeption}")

        except TimeoutError as exeption:
            logger.warning(f"Connection timeout: {str(exeption.args)}" if exeption else "Connection timeout: (empty message)")

        except Exception as exeption:
            logger.warning(f"Error getting values: {str(exeption)},{type(exeption)}")
            return