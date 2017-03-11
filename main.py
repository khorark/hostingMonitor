#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  main.py
#
#  Copyright 2017 Khoroshikh Arkadiy
# MIT Licence

import json
import os
import time
from datetime import datetime
from mysql.connector import Error

from mysql_config import connect
from daemon import runner


class App:
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/foo.pid'
        self.pidfile_timeout = 5
        self.pathDb = 'db.json'
        self.pathToWorkDir = os.getcwd()
        self.pathSetting = '{}/settings.json'.format(os.getcwd())
        self.setting = ''
        self.time_update = ''
        self.mysql_config = ''

    def getConfig(self):
        try:
            file = json.load(open(self.pathSetting))
            self.setting = file['servers']
            self.time_update = file['time_update']
            self.mysql_config = file['mysql_config']
            return True
        except FileNotFoundError:
            self.logError(40, 'main')
            return False
        except TypeError:
            self.logError(50, 'main')
            return False

    def getData(self):
        try:
            conn = connect(self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM hosts WHERE STATUS != 2')
            data = cursor.fetchall()
            # Обработка полученных данных
            for host in data:
                if host['status'] == 1:
                    self.createConfigs(host['host'])
                elif host['status'] == 3:
                    self.removeConfigs(host['host'])
                elif host['status'] != 2:
                    self.logError(30, host)

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
            try:
                text = open('{}/{}'.format(self.pathToWorkDir, setting['template'])).read()
                text = text.replace('$HOSTNAME$', host)

                # Проверяем существует ли путь до конфига
                pathToConfig = '{}/{}'.format(self.pathToWorkDir, setting['config'])
                if not os.path.isdir(pathToConfig):
                    os.makedirs(pathToConfig, 0o755)
                file = open('{}{}.conf'.format(pathToConfig, host), 'w')
                file.write(text)
                file.close()
            except FileNotFoundError:
                self.logError(10, host, '{}{}.conf'.format(pathToConfig, host))

    # Удаление конфигов
    def removeConfigs(self, host):
        for setting in self.setting.values():
            try:
                os.remove('{}/{}{}.conf'.format(self.pathToWorkDir, setting['config'], host))
            except FileNotFoundError:
                self.logError(10, host, '{}.conf'.format(host))
            except Exception:
                self.logError(99, host)

    # Обработчик ошибок и запись в лог
    def logError(self, code, domain, data = False):
        if code == 10:
            text = 'Файл {} не был найден'.format(data)
        elif code == 20:
            text = 'Ошибка открытия файла'
        elif code == 30:
            text = 'Неизвестный статус хоста {}'.format(domain)
        elif code == 40:
            text = 'Файл конфигурации не найден'
        elif code == 50:
            text = 'Неизвестный формат файла'
        else:
            text = 'Неизвестная ошибка'

        # Проверяем, существует ли директория
        pathDir = '{}/logs/{}'.format(self.pathToWorkDir, domain)
        if not os.path.isdir(pathDir):
            os.makedirs(pathDir, 0o0755)

        path = '{}/{}.log'.format(pathDir, datetime.now().date())
        file = open(path, 'a')
        file.write("""
            -------------------------
            {} - {}
            -------------------------

        """.format(datetime.now(), text))
        file.close()
        # print('Ошибка обработана')

    def run(self):
        if not self.getConfig():
            return False
        while True:
            self.getData()
            time.sleep(int(self.time_update))


if __name__ == '__main__':
    app = App()
    daemon_runner = runner.DaemonRunner(app)
    daemon_runner.do_action()
