import mysql.connector
from mysql.connector import Error


def connect(config):
    # Соединяемся c mysql базой данных
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            # print('Connected to MySQL database')
            pass
        else:
            print('connection failed.')

        return conn

    except Error as e:
        print(e)

if __name__ == '__main__':
    connect()
