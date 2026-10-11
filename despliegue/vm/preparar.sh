#!/bin/bash
# Prepara una máquina Debian recién creada: zona horaria, swap, Docker, parches automáticos
# y los archivos de configuración vacíos. Se puede ejecutar más de una vez.
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
# El swap es para los picos (la verificación de contraseñas), no para el uso normal.
echo 'vm.swappiness=10' > /etc/sysctl.d/60-web-seba.conf
sysctl --quiet --load /etc/sysctl.d/60-web-seba.conf

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
for nombre in compose web; do
    destino="/etc/web-seba/$nombre.env"
    if [ ! -f "$destino" ]; then
        install -m 600 "$raiz/despliegue/$nombre.env.example" "$destino"
        echo "Creado $destino: falta completarlo."
    fi
done

echo "== Herramientas de Google Cloud (para subir los respaldos) =="
if ! command -v gcloud > /dev/null; then
    echo "AVISO: no está el comando gcloud. Las imágenes Debian de Google Cloud lo traen;" >&2
    echo "instálelo antes de programar los respaldos (docs/DESPLIEGUE.md)." >&2
fi

echo
echo "Listo. Memoria y swap:"
free -m
echo
echo "Siga con docs/DESPLIEGUE.md: complete /etc/web-seba/compose.env y /etc/web-seba/web.env"
echo "y ejecute despliegue/vm/desplegar.sh <commit>."
