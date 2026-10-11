#!/bin/bash
# Respaldo de la base de datos: lo guarda en /var/backups/web-seba y lo sube al bucket de
# respaldos (SEG-11). Lo ejecuta a diario webseba-respaldo.timer.
# Uso: sudo respaldar.sh [--solo-local]
set -euo pipefail

aqui="$(cd "$(dirname "$0")" && pwd)"
dc="$aqui/dc"
carpeta=/var/backups/web-seba
conservar_locales=3

# shellcheck disable=SC1090
. "${WEB_SEBA_COMPOSE_ENV:-/etc/web-seba/compose.env}"

solo_local=no
if [ "${1:-}" = "--solo-local" ]; then
    solo_local=si
elif [ -z "${RESPALDOS_BUCKET:-}" ]; then
    echo "Falta RESPALDOS_BUCKET en /etc/web-seba/compose.env." >&2
    exit 1
fi

umask 077
mkdir -p "$carpeta"
nombre="webseba-$(date -u +%Y%m%dT%H%M%SZ).dump"
parcial="$carpeta/.$nombre.parcial"
trap 'rm -f "$parcial"' EXIT

"$dc" exec -T db pg_dump --username "$POSTGRES_USER" --format custom "$POSTGRES_DB" > "$parcial"
# Un respaldo que no se puede leer no es un respaldo: se comprueba antes de darlo por bueno.
"$dc" exec -T db pg_restore --list < "$parcial" > /dev/null
mv "$parcial" "$carpeta/$nombre"
echo "Respaldo local: $carpeta/$nombre ($(du -h "$carpeta/$nombre" | cut -f1))"

if [ "$solo_local" = no ]; then
    gcloud storage cp --no-user-output-enabled "$carpeta/$nombre" "gs://$RESPALDOS_BUCKET/$nombre"
    gcloud storage ls --long "gs://$RESPALDOS_BUCKET/$nombre"
    echo "Respaldo subido: gs://$RESPALDOS_BUCKET/$nombre"
fi

# En la máquina quedan solo los más recientes; la retención real es la del bucket.
find "$carpeta" -maxdepth 1 -name 'webseba-*.dump' -printf '%T@ %p\n' \
    | sort -rn | tail -n "+$((conservar_locales + 1))" | cut -d' ' -f2- | xargs -r rm -f
