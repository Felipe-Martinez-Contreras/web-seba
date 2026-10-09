#!/bin/sh
# Arranque de desarrollo: compila el CSS, aplica migraciones y levanta el servidor.
set -eu

tailwindcss --input static_src/css/app.css --output "$ESTATICOS_COMPILADOS_DIR/css/app.css" --minify
python manage.py migrate --noinput
python manage.py createcachetable

exec python manage.py runserver 0.0.0.0:8000
