import mysql.connector
from mysql.connector import Error


def connect():
    # Соединяемся c mysql базой данных
    try:
        conn = mysql.connector.connect(host='localhost',
                       database='test',
                       user='newuser',
                       password='1440954')
        if conn.is_connected():
            print('Connected to MySQL database')
        else:
            print('connection failed.')

        return conn

    except Error as e:
        print(e)

if __name__ == '__main__':
    connect()
