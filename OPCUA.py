import asyncio
from asyncua import Client, ua

async def main():
    url = "opc.tcp://192.168.187.10:4840" # replace with your server URL

    client = Client(url=url, timeout=4)
    client.set_user("LMT")
    client.set_password("lmt.1201")
    
    #try:
        
        #session = await client.create_session()
        #await session
        #username=username, password=password
        # Connect to the server using the authentication token
        
    await client.connect()

    #node_id = ua.NodeId.from_string(string='ns=3;s="LittleDB"."ChangbleTagBool1"')
    node_id = ua.NodeId.from_string(string='ns=3;s="StepData"."RunningSteps"."Steps"')
    nodeSteps = client.get_node(node_id)
    nodes = await nodeSteps.get_children()
    #nodes = client.get_values()

    for node in nodes:
        value = await node.get_child('Active')
        value = await value.get_value()
        if value:
            value = await node.get_child('PosX')
            value = await value.get_value()
            print(f"PosX value: {value}")
    
    
    
    #references = await nodeSteps.get_child('PosX') #get_referenced_nodes(ua.ObjectIds.Organizes, ua.BrowseDirection.Forward)

    #for ref in references:
    #    print(ref)

        # Do something with the server here...
    #finally:
        # Close the session with the server
        #await client.close_session()
    # Close the session
    await client.disconnect()

asyncio.run(main())