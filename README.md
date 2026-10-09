# web-seba

Plataforma web para un servicio de prevención de riesgos: sitio público y portal privado de documentos, en una sola aplicación Django.

El proyecto se construye por etapas. El estado actual está en [`docs/PLAN.md`](docs/PLAN.md); la especificación completa, en [`docs/ESPECIFICACION.md`](docs/ESPECIFICACION.md).

## Requisitos

- Docker Desktop con Docker Compose v2.
- Git.

No hace falta instalar Python ni Node: todo corre dentro de los contenedores. Los comandos de este documento funcionan en PowerShell.

## Instalación local

```powershell
git clone https://github.com/Felipe-Martinez-Contreras/web-seba.git
cd web-seba
Copy-Item .env.example .env
docker compose up -d --build --wait
```

Al arrancar, el contenedor `web` compila el CSS, aplica las migraciones y levanta el servidor. Cuando el comando termina, ambos servicios están listos:

- Comprobación de salud: <http://localhost:8000/salud/>
- Referencia de componentes (solo en desarrollo): <http://localhost:8000/_referencia/componentes/>

La dirección <http://localhost:8000/> responde 404 hasta que se construya el sitio público (Etapa 6).

El archivo `.env` no se sube al repositorio. Los valores de `.env.example` sirven solo para desarrollo.

## Comandos

| Para | Comando |
| --- | --- |
| Levantar | `docker compose up -d --wait` |
| Ver registros | `docker compose logs -f web` |
| Detener | `docker compose down` |
| Detener y borrar la base de datos local | `docker compose down -v` |
| Reconstruir tras cambiar dependencias | `docker compose up -d --build --wait` |
| Ejecutar un comando de Django | `docker compose run --rm web python manage.py <comando>` |
| Crear migraciones | `docker compose run --rm web python manage.py makemigrations` |
| Recompilar el CSS al guardar | `docker compose --profile css up -d` |

Sin el perfil `css`, el CSS se compila una vez al arrancar `web`; después de cambiar plantillas o estilos, `docker compose restart web` lo vuelve a compilar.

El PostgreSQL del contenedor no publica ningún puerto en el equipo. Para consultarlo: `docker compose exec db psql -U webseba webseba`.

## Pruebas y calidad

```powershell
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
```

Las pruebas usan PostgreSQL real (el servicio `db`) e informan la cobertura. La CI de GitHub Actions ejecuta lo mismo, audita las dependencias con `pip-audit` y comprueba que `docker compose up` levante la aplicación desde cero.

## Dependencias

Las versiones están fijadas en `pyproject.toml` y `uv.lock`. Para cambiarlas, edite `pyproject.toml` y regenere el archivo de bloqueo con la misma versión de `uv` que usa la imagen:

```powershell
docker compose run --rm --user root web uv lock
docker compose up -d --build --wait
```

Cada dependencia y archivo de terceros está justificado en [`docs/DECISIONES.md`](docs/DECISIONES.md).

## Estructura

```
config/        Configuración por entorno (base, dev, test, prod), URL y formatos es-CL
core/          RUT, validadores, logs, /salud/ y referencia de componentes
cuentas/       Modelo de usuario (RUT como identificador)
empresas/      Modelo de empresa
templates/     Plantillas base, componentes, íconos y páginas 404 y 500
static/        HTMX, fuentes y JavaScript propios (sin CDN)
static_src/    Entrada de Tailwind con los tokens de diseño
docker/        Script de arranque de desarrollo
docs/          Especificación, plan, decisiones y trazabilidad
```

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example). La configuración de producción (`config.settings.prod`) se niega a arrancar si faltan `SECRET_KEY`, `ALLOWED_HOSTS` o `DATABASE_URL`, o si `SECRET_KEY` es la clave de ejemplo.
