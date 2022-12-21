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
Boolean:
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


if __name__ == "__main__":


    client = Client("opc.tcp://192.168.0.1:4840")  # Adressen till servern
    try:
        client.connect()

        root = client.get_root_node()
        print("Objektets root nod är: ", root) # Printar ut nod id

        
        read_input_value("") # Sätt in nod id till vad du vill läsa in (i clienten högerklicka på variabeln och kopiera den)

        write_value_int("",) # Sätt in nod id till en int var och sen den nya värdet

        write_value_bool("",) # Sätt in nod id till en bool var och sen den nya värdet


    finally: # Bara ett try/finally block för att testa, byt sen mot whatever men bara för att säkerhetsställa att vi alltid lyckas disconnecta
        client.disconnect()