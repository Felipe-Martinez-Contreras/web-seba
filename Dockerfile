# syntax=docker/dockerfile:1

# Imagen de desarrollo y pruebas. La imagen de producción se agrega en la Etapa 8.
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
