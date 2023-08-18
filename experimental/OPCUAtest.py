import asyncio
import json
from asyncua import Client, Node, ua


async def get_children_values(node: Node) -> dict:
    result = {}
    nodes = await node.get_children()
    for child in nodes:
        if await child.read_node_class() == ua.NodeClass.Variable:
            value = await child.read_value()
            display_name = await child.read_display_name()
            if isinstance(value, ua.ExtensionObject):
                value = value
            result[display_name.Text] = value
        elif await child.read_node_class() == ua.NodeClass.Object:
            display_name = await child.read_display_name()
            result[display_name.Text] = await get_children_values(child)
    return result





def write_to_json(el_data, filename: str):
    with open(filename, "w", encoding="utf8") as outfile:
        json.dump(el_data, outfile, default=serialize)


def serialize(obj):
    if isinstance(obj, ua.ExtensionObject):
        if hasattr(obj.Value, "to_python"):
            return obj.Value.to_python()
        else:
            return str(obj)
    else:
        return obj



async def main():
    url = "opc.tcp://192.168.187.10:4840"
    client = Client(url=url, timeout=4)
    client.set_user("LMT")
    client.set_password("lmt.1201")
    nodestring = 'ns=3;s="StepData"."RunningSteps"."Steps"'

    await client.connect()

    #root = client.get_root_node()
    #node = await root.get_child(["0:Objects", "2:MyObject", "2:MyVariable"])
    node_id = ua.NodeId.from_string(string=nodestring)
    node = client.get_node(node_id)
    data = await get_children_values(node)
    write_to_json(data, "data.json")


if __name__ == "__main__":
    asyncio.run(main())