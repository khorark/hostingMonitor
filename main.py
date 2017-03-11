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
import subprocess
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
        self.settings = ''
        self.servers = ''
        self.time_update = ''
        self.mysql_config = ''

    def getConfig(self):
        try:
            file = json.load(open(self.pathSetting))
            self.servers = file['servers']
            self.settings = file['settings']
            self.mysql_config = file['mysql_config']
            if not self.servers or not self.settings or not self.mysql_config:
                return False
            return True
        except FileNotFoundError:
            self.logError(40, 'main')
            return False
        except TypeError:
            self.logError(50, 'main')
            return False

    def getData(self):
        self.getConfig()
        try:
            conn = connect(self.mysql_config)
            cursor = conn.cursor(dictionary=True)
            # Получем из таблицы actions все незавершенные действия и id доменов
            cursor.execute('SELECT id, action, domain_id FROM actions WHERE completed = "0"')
            data = cursor.fetchall()
            print(data)
            # Идем по циклу id этих доменов и выбираем их имя из таблици domains
            for host in data:
                cursor.execute('SELECT domain FROM domains WHERE id = {}'.format(host['domain_id']))
                domain = cursor.fetchone()
                statusFinish = ''
                # Производим физическое действие, в зависимости от action над доменом
                if host['action'] == 'create':
                    self.createConfigs(domain['domain'])
                    statusFinish = 'working'
                elif host['action'] == 'close':
                    statusFinish = 'closed'
                elif host['action'] == 'delete':
                    self.removeConfigs(domain['domain'])
                    statusFinish = 'deleted'
                else:
                    self.logError(60, domain['domain'], host['action'])

                if statusFinish != '':
                    dateTS = datetime.now()
                    # Обновляем поле update_at и status в таблице domains
                    query = 'UPDATE domains SET status = %s, updated_at = %s WHERE id = %s'
                    data = (statusFinish, dateTS, host['domain_id'])
                    cursor.execute(query, data)
                    # Обновляем поле update_at и поле completed на 1 в таблице actions
                    query = 'UPDATE actions SET completed = %s, updated_at = %s WHERE id = %s'
                    data = ('1', dateTS, host['id'])
                    cursor.execute(query, data)
                    # Применяем изменения
                    conn.commit()
                else:
                    self.logError(70, domain['domain'], host['action'])

            # Если были изменения, перезагружаем apache и nginx сервера
            if data:
                subprocess.call('httpd reload', shell=True)
                subprocess.call('nginx -s reload)', shell=True)

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
        for setting in self.servers.values():
            try:
                text = open('{}/{}'.format(self.pathToWorkDir, setting['template'])).read()

                # Подставляем данные конфигурации в шаблон
                text = text.replace('$HOSTNAME$', host)
                text = text.replace('$IP_ADDRESS_SERVER$', self.settings['ip_address_server'])
                text = text.replace('$PATH_TO_FILES_SERVER$', self.settings['path_to_files_server'])
                text = text.replace('$VERSION$', self.settings['version'])

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
        for setting in self.servers.values():
            try:
                os.remove('{}/{}{}.conf'.format(self.pathToWorkDir, setting['config'], host))
            except FileNotFoundError:
                self.logError(10, host, '{}.conf'.format(host))
            except Exception:
                self.logError(99, host)

    # Обработчик ошибок и запись в лог
    def logError(self, code, domain, data=False):
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
        elif code == 60:
            text = 'Неизвестный action {}'.format(data)
        elif code == 70:
            text = 'Ошибка при обработке action'
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
            time.sleep(int(self.settings['time_update']))


if __name__ == '__main__':
    app = App()
    daemon_runner = runner.DaemonRunner(app)
    daemon_runner.do_action()
