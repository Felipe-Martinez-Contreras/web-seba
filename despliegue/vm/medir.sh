#!/bin/bash
# Mide cuánto resiente la máquina un despliegue: vuelve a desplegar la versión que ya está
# en uso (no cambia de versión ni recrea la aplicación) y anota la memoria, el disco y los
# tiempos de respuesta. Siempre los mismos pasos, para comparar un antes y un después.
# Uso: sudo medir.sh        Tarda unos cinco minutos. Resultados: docs/DESPLIEGUE.md.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecute este guion con sudo." >&2
    exit 1
fi

aqui="$(cd "$(dirname "$0")" && pwd)"
version="$(sed -n 's/^WEB_SEBA_VERSION=//p' "${WEB_SEBA_COMPOSE_ENV:-/etc/web-seba/compose.env}")"
sitio="$(sed -n 's/^SITIO_URL=//p' "${WEB_SEBA_ENTORNO:-/etc/web-seba/web.env}")"
registro="/var/tmp/medir-$(date +%Y%m%d-%H%M%S)-vmstat.txt"

echo "== Antes: versión $version, $(date '+%d-%m-%Y %H:%M:%S') =="
free -m
swapon --show
sysctl vm.swappiness vm.page-cluster

# Tres minutos de vmstat, una muestra cada 2 segundos, mientras ocurre todo lo demás.
vmstat 2 90 > "$registro" &

echo "== Despliegue de la misma versión =="
inicio=$(date +%s)
"$aqui/desplegar.sh" "$version"
echo "desplegar.sh tardó $(( $(date +%s) - inicio )) segundos."

echo "== Sondeos del healthcheck de web (salida=0 es sano) =="
docker inspect --format \
    '{{.State.StartedAt}}{{range .State.Health.Log}}{{"\n"}}{{.Start}} salida={{.ExitCode}}{{end}}' \
    web-seba-web-1

echo "== Espera de 120 segundos =="
sleep 120

echo "== Tres visitas al inicio por la dirección pública (segundos) =="
for _ in 1 2 3; do
    curl --silent --output /dev/null --max-time 120 \
        --write-out '%{http_code} %{time_total}\n' "$sitio/"
done

wait
echo "== Resumen de vmstat ($registro) =="
awk '
    $1 == "r" { for (i = 1; i <= NF; i++) columna[$i] = i; next }
    !("wa" in columna) || $1 !~ /^[0-9]+$/ { next }
    {
        muestras++
        if ($columna["r"] > cola) cola = $columna["r"]
        if ($columna["wa"] > espera) espera = $columna["wa"]
        if ($columna["wa"] >= 40) lentas++
        if ($columna["us"] >= 80) ocupadas++
        if ($columna["st"] > robo) robo = $columna["st"]
        if (minimo == "" || $columna["buff"] < minimo) minimo = $columna["buff"]
        entra += $columna["si"]; sale += $columna["so"]
    }
    END {
        printf "muestras %d | cola r máx %d | wa máx %d %% | muestras con wa >= 40 %%: %d | ", \
            muestras, cola, espera, lentas
        printf "muestras con us >= 80 %%: %d | st máx %d | buff mín %d | suma si %d | suma so %d\n", \
            ocupadas, robo, minimo, entra, sale
    }
' "$registro"
echo "== Después =="
free -m
