#!/bin/bash
# Despliega una versión: la imagen que la CI publicó para ese commit.
# Uso: sudo desplegar.sh <commit de 40 caracteres>
# Volver atrás es ejecutarlo con el commit anterior (docs/DESPLIEGUE.md).
set -euo pipefail

# Todo dentro de una función: el guion se lee completo antes de que `git checkout` lo cambie.
principal() {
    local version="${1:-}"
    if ! [[ "$version" =~ ^[0-9a-f]{40}$ ]]; then
        echo "Uso: desplegar.sh <commit completo, 40 caracteres hexadecimales>" >&2
        exit 1
    fi
    if [ "$(id -u)" -ne 0 ]; then
        echo "Ejecute este guion con sudo." >&2
        exit 1
    fi

    local raiz entorno anterior
    raiz="$(cd "$(dirname "$0")/../.." && pwd)"
    entorno="${WEB_SEBA_COMPOSE_ENV:-/etc/web-seba/compose.env}"
    anterior="$(sed -n 's/^WEB_SEBA_VERSION=//p' "$entorno")"

    echo "== Código de despliegue en $version =="
    git -C "$raiz" fetch --quiet origin
    git -C "$raiz" checkout --quiet --detach "$version"
    local dc="$raiz/despliegue/vm/dc"

    echo "== Imagen =="
    sed -i "s/^WEB_SEBA_VERSION=.*/WEB_SEBA_VERSION=$version/" "$entorno"
    if ! "$dc" pull --quiet web; then
        sed -i "s/^WEB_SEBA_VERSION=.*/WEB_SEBA_VERSION=$anterior/" "$entorno"
        echo "No existe la imagen de ese commit: ¿terminó la CI en verde? No se cambió nada." >&2
        exit 1
    fi

    echo "== Base de datos =="
    "$dc" up --detach --wait db
    if [ -n "$anterior" ]; then
        # Si una migración de esta versión sale mal, este es el punto al que se vuelve.
        "$raiz/despliegue/vm/respaldar.sh" --solo-local
    fi
    "$dc" run --rm --no-deps web python manage.py migrate --noinput
    "$dc" run --rm --no-deps web python manage.py createcachetable

    echo "== Aplicación y túnel =="
    "$dc" up --detach --wait --remove-orphans
    "$dc" exec -T web python docker/salud.py
    "$dc" exec -T web python manage.py check --deploy

    echo "== Tareas programadas =="
    install -m 644 "$raiz"/despliegue/systemd/* /etc/systemd/system/
    systemctl daemon-reload
    local temporizador
    for temporizador in "$raiz"/despliegue/systemd/*.timer; do
        systemctl enable --now --quiet "$(basename "$temporizador")"
    done

    docker image prune --force > /dev/null
    echo
    echo "Desplegado $version (antes: ${anterior:-ninguno})."
    "$dc" ps
}

principal "$@"
exit
