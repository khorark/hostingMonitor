#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  main.py
#
#  Copyright 2017 Khoroshikh Arkadiy
# MIT Licence
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

from mysql_config import connect


class App:
    def __init__(self):
        self.pathDb = 'db.json'
        self.setting = {
            'nginx': {
                'template': 'templateConfigs/nginx.template',
                'config': 'confMy/nginx/'
            },
            'apache': {
                'template': 'templateConfigs/apache.template',
                'config': 'confMy/httpd/'
            }
        }

    def getData(self):
        try:
            conn = connect()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM hosts WHERE STATUS != 2')
            data = cursor.fetchall()
            for rec in data:
                print(rec)

        except Error as e:
            print('Error:', e)

        finally:
            cursor.close()
            conn.close()

    def readJsonFile(self):
        data = json.load(open(self.pathDb))
        for host in data:
            if host['status'] == 1:
                self.createConfigs(host['host'])
            elif host['status'] == 3:
                self.removeConfigs(host['host'])
            elif host['status'] != 2:
                self.logError(30, host)

    # Создание конфигов
    def createConfigs(self, host):
        for setting in self.setting.values():
            text = open(setting['template']).read()
            text = text.replace('$HOSTNAME$', host)
            file = open('{}{}.conf'.format(setting['config'], host), 'w')
            file.write(text)
            file.close()

    #Удаление конфигов
    def removeConfigs(self, host):
        for setting in self.setting.values():
            try:
                os.remove('{}{}.conf'.format(setting['config'], host))
            except FileNotFoundError:
                self.logError(10, '{}.conf'.format(host))
            except Exception:
                self.logError()

    #Обработчик ошибок и запись в лог
    def logError(self, code, data=False):
        if code == 10:
            text = 'Файл {} не был найден'.format(data)
        elif code == 20:
            text = 'Ошибка открытия файла'
        elif code == 30:
            text = 'Неизвестный статус хоста {}'.format(data)
        else:
            text = 'Неизвестная ошибка'

        path = 'logs/{}.log'.format(datetime.now().date())
        file = open(path, 'a')
        file.write("""
            -------------------------
            {} - {}
            -------------------------

        """.format(datetime.now(), text))
        file.close()
        print('Посмотрите log ошибок')

    def connect22(self):
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

        finally:
            conn.close()


if __name__ == '__main__':
    app = App()
    app.getData()
