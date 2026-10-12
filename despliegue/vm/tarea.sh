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

dc="$(dirname "$0")/dc"

# Corre cada 15 minutos y casi nunca tiene trabajo: una consulta liviana lo averigua sin
# cargar la aplicación entera. Ante cualquier duda (código distinto de 3) se ejecuta completa.
if [ "$1" = reintentar_notificaciones ]; then
    estado=0
    "$dc" exec -T web python docker/pendientes.py || estado=$?
    [ "$estado" -ne 3 ] || exit 0
fi

exec "$dc" exec -T web python manage.py "$1"
