#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  main.py
#
#  Copyright 2017 Khoroshikh Arkadiy
# MIT Licence
import json
import os


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

    def outFile(self):
        print('Hi!')

    def readJsonFile(self):
        data = json.load(open(self.pathDb))
        for host in data:
            if(host['status'] == 1):
                self.createConfigs(host['host'])
            elif(host['status'] == 3):
                self.removeConfigs(host['host'])

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
            os.remove('{}{}.conf'.format(setting['config'], host))


if __name__ == '__main__':
    app = App()
    app.readJsonFile()
