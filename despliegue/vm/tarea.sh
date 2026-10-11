#!/bin/sh
# Ejecuta una tarea programada dentro del contenedor de la aplicación. La llama
# webseba-tarea@<tarea>.service; a mano: sudo tarea.sh purgar_papelera
set -eu

case "${1:-}" in
    reintentar_notificaciones | purgar_papelera | clearsessions | depurar_auditoria) ;;
    *)
        echo "Tarea desconocida: ${1:-}" >&2
        exit 2
        ;;
esac

exec "$(dirname "$0")/dc" exec -T web python manage.py "$1"
