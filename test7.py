import asyncio

from asyncua import Client, ua




async def main():
    try:

        url = "opc.tcp://192.168.187.10:4840" # replace with your server URL


        client = Client(url=url, timeout=4)

        client.set_user("LMT")

        client.set_password("lmt.1201")


        await client.connect()




        #node_id = ua.NodeId.from_string(string='ns=3;s="LittleDB"."ChangbleTagBool1"')

        node_id = ua.NodeId.from_string(string='ns=3;s="StepData"."RunningSteps"."Steps"')

        nodeSteps = client.get_node(node_id)

        nodes = await nodeSteps.get_children()

        #nodes = client.get_values()




        for node in nodes:

            value = node

        #get_value()

            print(type(value))

        

    except KeyboardInterrupt:
        client.disconnect()





asyncio.run(main())