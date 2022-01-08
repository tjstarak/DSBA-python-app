from mysql.connector import connect, Error
import sqlalchemy as db

try:
    connection = connect(host="46.101.184.189",user="remote_user",password="pyth0nproj",database="pythonproj")
    print(connection)
    if connection.is_connected():
        print("Connection successful")
    else:
        print("Not connected")
    cursor = connection.cursor()

    db_query = "SHOW TABLES IN pythonproj"
    cursor.execute(db_query)
    result = cursor.fetchall()
    print(result)

except Error as e:
    print(e)

finally:
    connection.close()

engine = db.create_engine("mysql+mysqlconnector://remote_user:pyth0nproj@46.101.184.189:3306/pythonproj")
print(engine)
conn = engine.connect()
print(conn)
result = conn.execute("SHOW TABLES IN pythonproj").fetchall()
print(result)
print("Program complete")