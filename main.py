"""
Program för python att prata OPCUA
Att göra: 
Ändra all dokumentation till engelska
Få den funka
Ta reda på hur den ska köras, linux kernel? Docker? (kan en plc köra en docker? (plcnext kan, just saying))
Databas för recept? Mongodb?
Göra en API ifall man ska enkelt göra nya recept? (kanske man gör det via en hmi?)
"""
# Börja med att köra ".env\Scripts\opcua-client.exe" (se till att inte använda avast, 
# avast är som den jobbiga ungen i klassen som alltid ville göra extra för att va lärarens favorit
# "kolla fröken Britta jag kan scanna en exe jätte länge och inte låta användaren lita på denna exe") sen ge ip adress till servern
# Se till att Servern är på och att alla var är iklickade att dom kan ändras från OPCUA.
"""
Alla datatyper man kan läsa och skriva

Null:
Boolean:dsad
SByte:
Byte:
Int16:
UInt16:
Int32:
UInt32:
Int64:
UInt64:
Float:
Double:
String:
DateTime:
Guid:
ByteString:
XmlElement:
NodeId:
ExpandedNodeId:
StatusCode:
QualifiedName:
LocalizedText:
ExtensionObject:
DataValue:
Variant:
DiagnosticInfo:
"""
# Kräver 2 bibliotek opcua-client och opcua
from opcua import Client, ua
import opcua.common
from opcua.common import events
import json
from datetime import datetime


def read_input_value(node_id): # Funktion för att läsa in en variabel och convertera den till en string
    client_node = client.get_node(node_id)  # Får nod id (man ser okså vilken id den har i clienten)
    client_node_value = client_node.get_value()  # Läser in värdet på noden
    print("Value of : " + str(client_node) + ' : ' + str(client_node_value)) # Printar ut nodens plats (id) och värdet på den som en string


def write_value_int(node_id, value): # Funktion för att ändra en int, tar 2 argument här. Nod id och den nya valuen
    client_node = client.get_node(node_id) 
    client_node_value = value
    client_node_dv = ua.DataValue(ua.Variant(client_node_value, ua.VariantType.Int16)) # Sätter in den nya värdet 
    client_node.set_value(client_node_dv)
    print("Value of : " + str(client_node) + ' : ' + str(client_node_value)) # Printar ut den


def write_value_bool(node_id, value):
    client_node = client.get_node(node_id)
    client_node_value = value
    client_node_dv = ua.DataValue(ua.Variant(client_node_value, ua.VariantType.Boolean))
    client_node.set_value(client_node_dv)
    print("Value of : " + str(client_node) + ' : ' + str(client_node_value))


def read_value_extension_object(node_id):
    client_node = client.get_node(node_id)  
    client_node_value = client_node.get_value() 
    print(type(client_node_value))
    #print(client_node_value)
    print("Value of : " + str(client_node) + ' : ' + str(client_node_value))
    


if __name__ == "__main__":


    client = Client("opc.tcp://192.168.187.10:4840")  # Adressen till servern
    try:
        client.connect()

        root = client.get_root_node()
        print("Objektets root nod är: ", root) # Printar ut nod id

        objects = client.get_objects_node()
        print("Objects node is: ", objects)

        print("Children of root are: ", root.get_children())

        #obj2 = root.get_child(["0:Objects", "3:PLC_1"])
        #print(obj2)


        
        #read_input_value('ns=3;s="StepData"."RecipeSteps"[10]."Active"') # Sätt in nod id till vad du vill läsa in (i clienten högerklicka på variabeln och kopiera den)

        #write_value_int("",) # Sätt in nod id till en int var och sen den nya värdet

        #write_value_bool("",) # Sätt in nod id till en bool var och sen den nya värdet

        read_value_extension_object('ns=3;s="StepData"."RecipeSteps"[0]')
        

    finally: # Bara ett try/finally block för att testa, byt sen mot whatever men bara för att säkerhetsställa att vi alltid lyckas disconnecta
        client.disconnect()




# Kanske kan funka?
# Now getting a variable node using its browse path
        #obj = root.get_child(["0:Objects", "3:PLC_1,3:DataBlocksGlobal"])
        #obj2 = root.get_child(["0:Root,0:Objects,3:PLC_1,3:DataBlocksGlobal,3:StepData,3:RecipeSteps,3:0"])

#        print("MyObject is: ", obj)
# get a specific node knowing its node id
        #var = client.get_node(ua.NodeId(1002, 2))
        #var = client.get_node("ns=3;i=2002")
        #print(var)
        #var.get_data_value() # get value of node as a DataValue object
        #var.get_value() # get value of node as a python builtin
        #var.set_value(ua.Variant([23], ua.VariantType.Int64)) #set node value using explicit data type
        #var.set_value(3.9) # set node value using implicit data type
        #0:Root,0:Objects,3:PLC_1,3:DataBlocksGlobal,3:StepData,3:RecipeSteps,3:0