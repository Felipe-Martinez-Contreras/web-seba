#!/bin/sh
# Ejecuta una tarea programada dentro del contenedor de la aplicación. La llama
# webseba-tarea@<tarea>.service; a mano: sudo tarea.sh purgar_papelera
set -eu

case "${1:-}" in
    reintentar_notificaciones | purgar_papelera | clearsessions | depurar_auditoria | depurar_solicitudes) ;;
    *)
        echo "Tarea desconocida: ${1:-}" >&2
        exit 2
        ;;
esac

dc="$(dirname "$0")/dc"

# Estas dos casi nunca tienen trabajo: una consulta liviana lo averigua sin cargar la
# aplicación entera. Ante cualquier duda (código distinto de 3) se ejecuta completa.
case "$1" in
    reintentar_notificaciones | depurar_solicitudes)
        estado=0
        "$dc" exec -T web python docker/pendientes.py "$1" || estado=$?
        [ "$estado" -ne 3 ] || exit 0
        ;;
esac

exec "$dc" exec -T web python manage.py "$1"
