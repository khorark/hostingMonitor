# hostingMonitor

[![N|Solid](http://savepic.ru/13232554.png)](http://clients.masproject.pro/)

# Описание
Программа предназначена для автоматического создания и удаления хостов. 

###### Хосты должны быть записаны:
 - json файл
 - БД mysql

# Требования
  - python 3
  - mysql-connector
  ### Установка mysql-connector
```sh
$ pip install mysql-connector
```
### Запуск
Скрипт работает в режиме демона и поддерживает следующие команды:

***Для запуска скрипта:***
```sh
$ python3 main.py start
``` 
***Для остановки скрипта:***
```sh
$ python3 main.py stop
``` 
***Для проверки состояния скрипта:***
```sh
$ python3 main.py status
``` 


License
----

MIT
