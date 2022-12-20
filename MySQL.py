import mysql.connector

mydb = mysql.connector.connect(
  host="sda-teststation",
  user="lmt",
  password="lmt.1201",
  database="test"
)

print(mydb)

mycursor = mydb.cursor()

mycursor.execute("CALL showvalues()")

for x in mycursor:
  print(x)

mydb.disconnect()