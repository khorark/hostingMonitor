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
import shutil

from mysql_config import connect
from daemon import runner


class App:
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/foo.pid'
        self.pidfile_timeout = 5
        self.pathToWorkDir = os.getcwd()
        self.pathSetting = '{}/settings.json'.format(os.getcwd())
        self.settings = ''
        self.actions = ''
        self.configs = ''
        self.time_update = ''
        self.mysql_config = ''

    def getConfig(self):
        try:
            file = json.load(open(self.pathSetting))
            self.actions = file['actions']
            self.settings = file['settings']
            self.mysql_config = file['mysql_config']
            self.configs = file['configs']
            if not self.actions or not self.settings or not self.mysql_config or not self.configs:
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
            # Идем по циклу id этих доменов и выбираем их имя из таблици domains
            for host in data:
                cursor.execute('SELECT domain FROM domains WHERE id = {}'.format(host['domain_id']))
                domain = cursor.fetchone()

                # Производим физическое действие, в зависимости от action над доменом
                if host['action'] == 'delete':
                    self.removeConfigs(domain['domain'])
                else:
                    self.createOrBlockConfigs(host['action'], domain['domain'])

                date_ts = datetime.now()
                try:
                    status_work = self.actions[host['action']]['status']
                    # Обновляем поле update_at и status в таблице domains
                    query = 'UPDATE domains SET status = %s, updated_at = %s WHERE id = %s'
                    data = (status_work, date_ts, host['domain_id'])
                    cursor.execute(query, data)
                    # Обновляем поле update_at и поле completed на 1 в таблице actions
                    query = 'UPDATE actions SET completed = %s, updated_at = %s WHERE id = %s'
                    data = ('1', date_ts, host['id'])
                    cursor.execute(query, data)
                    # Применяем изменения
                    conn.commit()
                except KeyError:
                    # Обновляем поле update_at и поле completed на 2 в таблице actions
                    query = 'UPDATE actions SET completed = %s, updated_at = %s WHERE id = %s'
                    data = ('2', date_ts, host['id'])
                    cursor.execute(query, data)
                    # Применяем изменения
                    conn.commit()
                    self.logError(60, domain['domain'], host['action'])

            # Если были изменения, перезагружаем apache и nginx сервера
            if data:
                subprocess.call('service httpd reload', shell=True)
                subprocess.call('service nginx -s reload', shell=True)

        except Error as e:
            print('Error:', e)

        finally:
            cursor.close()
            conn.close()

    # Создание конфигов
    def createOrBlockConfigs(self, mode, host):
        # Создаем папку с логом
        pathToLogs = '{}/logs/{}'.format(self.settings['path_to_files_server'], host)
        if not os.path.isdir(pathToLogs):
            os.makedirs(pathToLogs, 0o755)

        try:
            for server, template in self.actions[mode]['templates'].items():
                try:
                    text = open('{}/{}'.format(self.pathToWorkDir, template)).read()

                    # Подставляем данные конфигурации в шаблон
                    text = text.replace('$HOSTNAME$', host)
                    text = text.replace('$IP_ADDRESS_SERVER$', self.settings['ip_address_server'])
                    text = text.replace('$PATH_TO_FILES_SERVER$', self.settings['path_to_files_server'])

                    path_to_config = self.configs[server]

                    # Проверяем существует ли путь до конфига
                    if not os.path.isdir(path_to_config):
                        os.makedirs(path_to_config, 0o755)
                    file = open('{}{}.conf'.format(path_to_config, host), 'w')
                    file.write(text)
                    file.close()
                except FileNotFoundError:
                    self.logError(10, host, '{}{}.conf'.format(path_to_config, host))
                except Exception:
                    self.logError(11, host, '{}{}.conf'.format(path_to_config, host))

        except KeyError:
            self.logError(60, host, mode)

    # Удаление конфигов
    def removeConfigs(self, host):
        for config in self.configs.values():
            try:
                os.remove('{}{}.conf'.format(config, host))
            except FileNotFoundError:
                self.logError(10, host, '{}.conf'.format(host))
            except Exception:
                self.logError(99, host)

        # Удаляем папку с логом
        path_to_logs = '{}/logs/{}'.format(self.settings['path_to_files_server'], host)
        if os.path.isdir(path_to_logs):
            shutil.rmtree(path_to_logs, ignore_errors=False, onerror=None)

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
        path_dir = '{}/logs/{}'.format(self.pathToWorkDir, domain)
        if not os.path.isdir(path_dir):
            os.makedirs(path_dir, 0o0755)

        path = '{}/{}.log'.format(path_dir, datetime.now().date())
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
