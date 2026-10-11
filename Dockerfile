# syntax=docker/dockerfile:1

# Dos imágenes: `dev` (desarrollo y pruebas, la que usa compose.yaml) y `prod` (la que
# publica la CI y corre en el servidor, docs/DESPLIEGUE.md).
FROM python:3.13.16-slim-trixie AS dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH \
    ESTATICOS_COMPILADOS_DIR=/opt/estaticos \
    # Cachés y cobertura fuera del código montado desde el equipo.
    COVERAGE_FILE=/tmp/.coverage \
    RUFF_CACHE_DIR=/tmp/ruff \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/pytest"

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

# Tailwind CLI standalone 4.3.3, verificado contra el sha256sums.txt de su release.
ADD --checksum=sha256:dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a \
    --chmod=755 \
    https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64 \
    /usr/local/bin/tailwindcss

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-cache

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /opt/estaticos/css /var/app/media \
    && chown -R app:app /opt/estaticos /var/app/media

COPY --chown=app:app . .

USER app

RUN tailwindcss --input static_src/css/app.css --output /opt/estaticos/css/app.css --minify

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# Construcción de producción: dependencias sin las de desarrollo, CSS y estáticos recolectados.
FROM python:3.13.16-slim-trixie AS construccion

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH=/opt/venv/bin:$PATH

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

ADD --checksum=sha256:dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a \
    --chmod=755 \
    https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64 \
    /usr/local/bin/tailwindcss

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-cache

COPY . .

RUN tailwindcss --input static_src/css/app.css --output /opt/estaticos/css/app.css --minify

# `collectstatic` carga la configuración de producción, que exige estas variables. Valen solo
# para esta instrucción: no quedan en la imagen y ninguna es un secreto real.
RUN SECRET_KEY=solo-para-recolectar-estaticos-durante-la-construccion-de-la-imagen \
    ALLOWED_HOSTS=construccion.invalid \
    DATABASE_URL=postgres://sin:uso@construccion.invalid:5432/sin-uso \
    SITIO_URL=https://construccion.invalid \
    PROXY_CONFIANZA_REDES= \
    DOCUMENTOS_ALMACENAMIENTO=local \
    ESTATICOS_COMPILADOS_DIR=/opt/estaticos \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    python manage.py collectstatic --noinput \
    && python -m compileall -q -x '/tests/' .


FROM python:3.13.16-slim-trixie AS prod

LABEL org.opencontainers.image.source="https://github.com/Felipe-Martinez-Contreras/web-seba" \
      org.opencontainers.image.description="web-seba: sitio público y portal de documentos"

# La configuración queda fija: un comando lanzado a mano o por el cron nunca usa la de
# desarrollo (docs/SEGURIDAD.md, H-06).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=config.settings.prod

RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=construccion /opt/venv /opt/venv
COPY --from=construccion /app /app

# El código es de root y la aplicación corre sin privilegios: no puede modificarse a sí misma.
USER app

EXPOSE 8000
CMD ["gunicorn", "--config", "config/gunicorn.py", "config.wsgi:application"]
