#!/bin/bash
# Prepara una máquina Debian recién creada: zona horaria, swap, Docker, parches automáticos
# y los archivos de configuración vacíos. Se puede ejecutar más de una vez, también con el
# sitio en marcha: no toca los archivos de /etc/web-seba que ya existen, ni los contenedores,
# ni las tareas programadas, ni los datos.
# Uso: sudo /opt/web-seba/despliegue/vm/preparar.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Ejecute este guion con sudo." >&2
    exit 1
fi

raiz="$(cd "$(dirname "$0")/../.." && pwd)"
export DEBIAN_FRONTEND=noninteractive

echo "== Zona horaria de Chile (las tareas programadas usan la hora local) =="
timedatectl set-timezone America/Santiago

echo "== Swap de 2 GB =="
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
    if [ ! -f /swapfile ]; then
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
    fi
    swapon /swapfile
fi
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

echo "== Docker Engine y Compose, desde el repositorio de Docker =="
apt-get update --quiet
apt-get install --yes --quiet ca-certificates curl git unattended-upgrades
if ! command -v docker > /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl --fail --silent --show-error --location \
        https://download.docker.com/linux/debian/gpg --output /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc]" \
        "https://download.docker.com/linux/debian $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update --quiet
    apt-get install --yes --quiet docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
systemctl enable --now docker

echo "== Swap comprimida en memoria (zram), antes que la del disco =="
# El disco estándar rinde muy pocas lecturas por segundo: lo que va a parar a su swap tarda
# minutos en volver. La zram guarda esas páginas comprimidas en la propia memoria; el
# archivo del disco queda solo como rebalse, con menos prioridad.
zram_activa() {
    swapon --show=NAME --noheadings | grep -qx /dev/zram0
}
zram=no
if modinfo zram > /dev/null 2>&1; then
    # Antes de instalar el paquete, para que el dispositivo nazca con esta configuración.
    cat > /etc/systemd/zram-generator.conf << 'FIN'
[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
FIN
    apt-get install --yes --quiet systemd-zram-generator
    systemctl daemon-reload
    if ! zram_activa; then
        modprobe zram || true
        systemctl start systemd-zram-setup@zram0.service || true
    fi
    # systemd crea el dispositivo y lo activa por su cuenta, y puede tardar unos segundos:
    # decidir de inmediato dejaba los ajustes de "sin zram" con la zram ya en marcha.
    for _ in $(seq 1 30); do
        if zram_activa; then
            break
        fi
        sleep 1
    done
    if zram_activa; then
        zram=si
    else
        echo "AVISO: no se pudo activar la zram; queda solo la swap del disco." >&2
    fi
else
    echo "AVISO: este núcleo no trae el módulo zram; queda solo la swap del disco." >&2
fi

echo "== Ajustes de memoria del núcleo =="
if [ "$zram" = si ]; then
    # Con la swap en memoria, desalojar memoria de los procesos es barato: se prefiere a
    # botar el caché de archivos, que hay que volver a leer del disco. Sin lectura
    # anticipada: en la zram cada página se descomprime por separado.
    printf 'vm.swappiness=100
vm.page-cluster=0
' > /etc/sysctl.d/60-web-seba.conf
else
    # El valor del núcleo. Con 10, la máquina botaba casi todo el caché de archivos antes
    # de usar la swap, y cada proceso nuevo releía sus programas desde el disco.
    printf 'vm.swappiness=60
' > /etc/sysctl.d/60-web-seba.conf
fi
sysctl --quiet --load /etc/sysctl.d/60-web-seba.conf

echo "== Parches de seguridad automáticos, con reinicio de madrugada si hace falta =="
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'FIN'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
FIN
cat > /etc/apt/apt.conf.d/52web-seba << 'FIN'
// Además de Debian, se actualiza solo el Docker instalado desde su repositorio.
Unattended-Upgrade::Origins-Pattern:: "origin=Docker";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "05:00";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
FIN
systemctl enable --now unattended-upgrades

echo "== Carpetas y archivos de configuración =="
install -d -m 700 /etc/web-seba /var/backups/web-seba
por_completar=""
for nombre in compose web; do
    destino="/etc/web-seba/$nombre.env"
    if [ ! -f "$destino" ]; then
        install -m 600 "$raiz/despliegue/$nombre.env.example" "$destino"
        echo "Creado $destino: falta completarlo."
    fi
    # Los valores sin los que nada arranca. Solo se mira si están vacíos, no qué dicen.
    case "$nombre" in
        compose) obligatorias="POSTGRES_PASSWORD TUNNEL_TOKEN" ;;
        *) obligatorias="SECRET_KEY ALLOWED_HOSTS SITIO_URL" ;;
    esac
    for variable in $obligatorias; do
        if ! grep -q "^$variable=..*" "$destino"; then
            por_completar="$por_completar $destino"
            break
        fi
    done
done

echo "== Herramientas de Google Cloud (para subir los respaldos) =="
if ! command -v gcloud > /dev/null; then
    echo "AVISO: no está el comando gcloud. Las imágenes Debian de Google Cloud lo traen;" >&2
    echo "instálelo antes de programar los respaldos (docs/DESPLIEGUE.md)." >&2
fi

echo
echo "Listo. Memoria y swap:"
free -m
swapon --show
sysctl vm.swappiness vm.page-cluster
echo
if [ -n "$por_completar" ]; then
    echo "Siga con docs/DESPLIEGUE.md: complete$por_completar"
    echo "y ejecute despliegue/vm/desplegar.sh <commit>."
else
    echo "Los archivos de /etc/web-seba ya estaban completos: no se tocaron."
fi
