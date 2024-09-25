#!/bin/sh

python manage.py makemigrations
python manage.py migrate --noinput
python manage.py collectstatic --noinput
cp -r /app/collected_static/. /backend_static/static/

gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000