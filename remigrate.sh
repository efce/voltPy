#!/bin/bash
rm ./db.sqlite3
./remove_migrations.py
./manage.py makemigrations
./manage.py migrate
