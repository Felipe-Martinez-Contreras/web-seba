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

- Acceso: <http://localhost:8000/acceso/>
- Panel de administración: <http://localhost:8000/panel/> (requiere un administrador con 2FA; ver abajo)
- Comprobación de salud: <http://localhost:8000/salud/>
- Referencia de componentes (solo en desarrollo): <http://localhost:8000/_referencia/componentes/>

La dirección <http://localhost:8000/> responde 404 hasta que se construya el sitio público (Etapa 6).

El archivo `.env` no se sube al repositorio. Los valores de `.env.example` sirven solo para desarrollo.

### Primer administrador

No hay registro público ni contraseñas iniciales. El primer administrador se crea con un comando, que muestra un enlace de activación de un solo uso:

```powershell
docker compose run --rm web python manage.py crear_administrador
```

Al abrir el enlace, la persona define su contraseña y, en esa misma sesión, configura la verificación en dos pasos con una aplicación de autenticación. Los correos de recuperación se imprimen en la consola del contenedor (`docker compose logs -f web`) mientras no haya un servidor SMTP configurado.

### Crear un cliente y probar el flujo completo

Con el administrador ya dentro del panel:

1. **Clientes → Nuevo cliente.** Ingrese RUT y razón social, deje marcada "Crear las carpetas base" y guarde. La ficha se abre en la pestaña Usuarios.
2. **Crear usuario.** Ingrese el RUT y el nombre de la persona. La página siguiente muestra el enlace de activación: cópielo con "Copiar enlace". Se muestra una sola vez.
3. Abra el enlace en una ventana privada, defina la contraseña y verá el portal del cliente, todavía sin documentos (después de subirlos, siga con "Recorrer el portal del cliente").
4. Para probar el corte de acceso: con esa ventana abierta, pulse "Desactivar" en la ficha del cliente y recargue el portal. Vuelve a la pantalla de acceso.
5. Para probar el desbloqueo: falle la contraseña 5 veces con el RUT del usuario. En la pestaña Usuarios aparece "Bloqueado" con el botón "Desbloquear".

### Subir documentos

Con un cliente y sus carpetas ya creados:

1. En la ficha del cliente, pestaña **Documentos**, abra una carpeta.
2. Elija varios archivos y pulse **Subir documentos**: cada uno muestra su barra de progreso y su resultado. Pruebe también con un archivo inválido (por ejemplo, un `.exe` renombrado a `.pdf`) para ver el motivo del rechazo.
3. Abra un documento: descargue, use "Ver en pantalla", reemplace el archivo (también muestra su barra de progreso) y revise el historial de versiones.
4. Elimine el documento y restáurelo desde la **Papelera** del cliente.

Los archivos se guardan en el volumen `documentos_datos` de Docker (`/var/app/media` en el contenedor), fuera del código y sin ninguna URL que los sirva: solo se entregan por las vistas de ver y descargar, que exigen sesión y dejan un evento de auditoría.

### Probar el almacenamiento S3 sin un bucket real

El desarrollo diario usa el almacenamiento local. Para revisar a mano la descarga con URL firmada hay un emulador opcional de S3 (`moto`), que usa la misma imagen y unos 50 MB de memoria:

```powershell
docker compose --profile s3 up -d s3
docker compose run --rm -e DOCUMENTOS_ALMACENAMIENTO=s3 -e S3_BUCKET=documentos-dev -e S3_ENDPOINT_URL=http://s3:5000 -e S3_REGION=us-east-1 -e S3_ACCESS_KEY_ID=desarrollo -e S3_SECRET_ACCESS_KEY=desarrollo web python manage.py comprobar_almacenamiento --crear-bucket
docker compose --profile s3 down
```

El emulador guarda todo en memoria y lo pierde al detenerse. No valida firmas ni vencimientos, así que no reemplaza la comprobación contra el bucket real, que se hace antes de cargar documentos con `python manage.py comprobar_almacenamiento --firma` (tarda unos 2 minutos; ver `docs/SEGURIDAD.md`).

La guía de uso para el profesional está en [`docs/MANUAL_ADMIN.md`](docs/MANUAL_ADMIN.md).

## Comandos

| Para | Comando |
| --- | --- |
| Levantar | `docker compose up -d --wait` |
| Ver registros | `docker compose logs -f web` |
| Detener | `docker compose down` |
| Detener y borrar la base de datos y los documentos locales | `docker compose down -v` |
| Reconstruir tras cambiar dependencias | `docker compose up -d --build --wait` |
| Ejecutar un comando de Django | `docker compose run --rm web python manage.py <comando>` |
| Crear migraciones | `docker compose run --rm web python manage.py makemigrations` |
| Crear un administrador | `docker compose run --rm web python manage.py crear_administrador` |
| Crear el superusuario técnico (admin de Django) | `docker compose run --rm web python manage.py crear_administrador --tecnico` |
| Restablecer el 2FA de un administrador | `docker compose run --rm web python manage.py restablecer_2fa <rut>` |
| Desbloquear un RUT o una IP | `docker compose run --rm web python manage.py desbloquear_acceso --rut <rut>` (o `--ip <ip>`) |
| Borrar la auditoría más antigua que la retención | `docker compose run --rm web python manage.py depurar_auditoria` |
| Borrar definitivamente lo que lleva más de 30 días en la papelera | `docker compose run --rm web python manage.py purgar_papelera` |
| Comprobar el almacenamiento de documentos configurado | `docker compose run --rm web python manage.py comprobar_almacenamiento` |
| Levantar el emulador de S3 | `docker compose --profile s3 up -d s3` |
| Recompilar el CSS al guardar | `docker compose --profile css up -d` |

Sin el perfil `css`, el CSS se compila una vez al arrancar `web`; después de cambiar plantillas o estilos, `docker compose restart web` lo vuelve a compilar.

El PostgreSQL del contenedor no publica ningún puerto en el equipo. Para consultarlo: `docker compose exec db psql -U webseba webseba`.

### Recorrer el portal del cliente

Con un cliente activo y documentos subidos, entre como ese cliente en `http://localhost:8000/acceso/` (conviene una ventana privada, para no mezclar la sesión con la del administrador):

1. **Inicio:** saludo, tarjeta de la empresa, buscador, "Sus carpetas" y "Documentos recientes", con la etiqueta "Nuevo" durante 14 días.
2. Abra una carpeta: cada documento tiene **Ver** (solo PDF, JPG y PNG) y **Descargar**. Cambie el orden entre "Más recientes" y "Por nombre".
3. Busque un título sin tildes (por ejemplo, `inspeccion`): encuentra "Inspección".
4. Abra la ficha de un documento, descárguelo y use "Ver en pantalla" (se abre en una pestaña nueva).
5. En el panel, reemplace o elimine ese documento y recargue el portal: el cliente ve el archivo nuevo, o deja de verlo.

**En un teléfono real.** La revisión de la etapa se hizo con el modo móvil del navegador, no con un teléfono. Para probarlo en uno, conectado a la misma red Wi-Fi que el equipo: publique el puerto en la red cambiando en `compose.yaml` `127.0.0.1:8000:8000` por `8000:8000`, agregue la IP del equipo a `ALLOWED_HOSTS` en `.env` (por ejemplo `localhost,127.0.0.1,192.168.1.20`), ejecute `docker compose up -d` y abra `http://<IP del equipo>:8000/acceso/` en el teléfono. Use solo datos de prueba y deshaga ambos cambios al terminar.

## Pruebas y calidad

```powershell
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
```

En un equipo con poca memoria, detenga antes el servidor para no tener dos contenedores `web` a la vez: `docker compose stop web`.

Las pruebas usan PostgreSQL real (el servicio `db`) e informan la cobertura. Los archivos de prueba se generan en memoria y se guardan en una carpeta temporal; el almacenamiento S3 se prueba contra `moto`, un emulador que corre dentro del mismo proceso, sin red. La CI de GitHub Actions ejecuta lo mismo, audita las dependencias con `pip-audit` y comprueba que `docker compose up` levante la aplicación desde cero.

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
core/          RUT, validadores, IP de confianza, mixins de rol, correo, logs y /salud/
cuentas/       Usuario, acceso, bloqueo, enlaces de un solo uso, recuperación y 2FA
empresas/      Empresas (clientes) y sus carpetas
auditoria/     Registro de eventos (solo se agregan), filtros y retención
documentos/    Documentos y versiones, validación de archivos, almacenamiento (local y S3) y papelera
portal/        Vistas del cliente: inicio, carpetas, buscador, ficha del documento, ver y descargar
panel/         Vistas del administrador: inicio, clientes, usuarios, carpetas, documentos y auditoría
templates/     Plantillas base, componentes, íconos y páginas 404 y 500
static/        HTMX, fuentes y JavaScript propios (sin CDN), incluida la subida con progreso
static_src/    Entrada de Tailwind con los tokens de diseño
docker/        Script de arranque de desarrollo
docs/          Especificación, plan, arquitectura, decisiones, trazabilidad, seguridad y manual del administrador
```

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example). La configuración de producción (`config.settings.prod`) se niega a arrancar si faltan `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `SITIO_URL` (con https), `PROXY_CONFIANZA_REDES` (puede ir vacía) o `DOCUMENTOS_ALMACENAMIENTO` (`local` o `s3`), o si `SECRET_KEY` es la clave de ejemplo. `python manage.py check` falla si el almacenamiento está mal configurado: carpeta de documentos dentro de una ruta de estáticos, o `s3` sin bucket o sin credenciales.

El admin de Django solo se publica si `DJANGO_ADMIN_RUTA` está definida. Si agrega variables nuevas a `.env.example`, cópielas también a su `.env`.
