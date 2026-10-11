#!/bin/bash
# Restaura la base de datos desde un respaldo. BORRA la base actual y la reemplaza.
# Uso: sudo restaurar.sh <archivo.dump | gs://bucket/archivo.dump>
# Procedimiento completo y simulacro: docs/DESPLIEGUE.md.
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
dc="$aqui/dc"

# shellcheck disable=SC1090
. "${WEB_SEBA_COMPOSE_ENV:-/etc/web-seba/compose.env}"

origen="${1:-}"
if [ -z "$origen" ]; then
    echo "Uso: restaurar.sh <archivo.dump | gs://bucket/archivo.dump>" >&2
    exit 1
fi

temporal=""
trap '[ -z "$temporal" ] || rm -f "$temporal"' EXIT
if [[ "$origen" == gs://* ]]; then
    umask 077
    temporal="$(mktemp /var/backups/web-seba/restaurar-XXXXXX.dump)"
    gcloud storage cp --no-user-output-enabled "$origen" "$temporal"
    archivo="$temporal"
else
    archivo="$origen"
fi
[ -s "$archivo" ] || { echo "No existe o está vacío: $archivo" >&2; exit 1; }

"$dc" up --detach --wait db
"$dc" exec -T db pg_restore --list < "$archivo" > /dev/null \
    || { echo "El archivo no es un respaldo legible." >&2; exit 1; }

echo "Se va a BORRAR la base \"$POSTGRES_DB\" y a reemplazarla por: $origen"
read -r -p "Para continuar escriba el nombre de la base: " respuesta
[ "$respuesta" = "$POSTGRES_DB" ] || { echo "Cancelado: no se cambió nada."; exit 1; }

inicio=$(date +%s)
# Nadie escribe mientras se restaura: se detienen el túnel y la aplicación.
"$dc" stop cloudflared web
"$dc" exec -T db dropdb --username "$POSTGRES_USER" --force --if-exists "$POSTGRES_DB"
"$dc" exec -T db createdb --username "$POSTGRES_USER" "$POSTGRES_DB"
"$dc" exec -T db pg_restore --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --no-owner --exit-on-error < "$archivo"

"$dc" up --detach --wait
# Si el respaldo es de una versión anterior del código, aquí se sabe: faltarían migraciones.
"$dc" exec -T web python manage.py migrate --check \
    || echo "AVISO: hay migraciones sin aplicar. Ejecute: dc exec web python manage.py migrate" >&2
"$dc" exec -T web python docker/salud.py
echo "Restauración terminada en $(( $(date +%s) - inicio )) segundos."
