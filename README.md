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
| Listar el contenido del sitio que falta completar | `docker compose run --rm web python manage.py contenido_pendiente` (con `--estricto` termina con error si queda algo) |
| Cargar datos de demostración, marcados DEMO | `docker compose run --rm web python manage.py cargar_demo` |
| Sacar a un archivo el contenido del sitio (datos del negocio y servicios, sin lo DEMO) | `docker compose run --rm web python manage.py exportar_contenido contenido-sitio.json` (trae datos de contacto; ese nombre está en `.gitignore`) |
| Cargar ese archivo en una base sin contenido | `docker compose run --rm web python manage.py importar_contenido contenido-sitio.json` (repetirlo no duplica; en el servidor, `docs/DESPLIEGUE.md` §11) |
| Reintentar las notificaciones de solicitudes que fallaron | `docker compose run --rm web python manage.py reintentar_notificaciones` |
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

### Ver el sitio público y probar los formularios

Recién instalado, `http://localhost:8000/` muestra solo la navegación y el pie: los datos del negocio están vacíos y lo que falta no se muestra. Para verlo completo, con un administrador ya creado:

```powershell
docker compose run --rm web python manage.py cargar_demo
```

Carga datos marcados DEMO: contenido del sitio, cuatro servicios, una política de privacidad encabezada "TEXTO DE PRUEBA" y dos empresas con un usuario y dos PDF cada una. No pisa datos que ya existan. Solo corre con `DEMO_PERMITIDO=true` en `.env` (viene así en `.env.example`; si su `.env` es anterior, agréguela y reinicie con `docker compose up -d`). Producción nunca define esa variable.

1. Abra `http://localhost:8000/`: portada, servicios, formulario de cotización y pie.
2. En **Servicios**, pulse "Solicitar cotización" en uno: el formulario llega con ese servicio elegido.
3. Envíe el formulario (espere al menos 3 segundos tras abrirlo). Verá "Recibimos su solicitud".
4. El correo de aviso se imprime en la consola: `docker compose logs web`. Para que exista un destinatario, defina `NOTIFICACIONES_DESTINATARIOS` en `.env` y reinicie; sin ella, la solicitud queda como "Correo no configurado".
5. En el panel, **Solicitudes** muestra la solicitud con su estado y el de su notificación.
6. Para ver un fallo de correo: ponga en `.env` `CORREO_HOST=127.0.0.1`, `CORREO_PUERTO=1` y un `CORREO_REMITENTE`, reinicie y envíe otra. El visitante ve la misma confirmación; el panel la muestra "Fallida", con el botón para reintentar.
7. `docker compose run --rm web python manage.py contenido_pendiente` lista lo que falta para publicar.

El contenido real se carga en el panel, en **Configuración › Contenido del sitio**. Las fotografías y su licencia están en [`docs/FOTOS.md`](docs/FOTOS.md).

### Revisión manual pendiente: lector de pantalla y Firefox

Dos comprobaciones de la Etapa 7 necesitan a una persona. Anote el resultado en `docs/TRAZABILIDAD.md` (E8 y RNF-03).

**Con el Narrador de Windows** (unos 15 minutos, en Edge, con datos de `cargar_demo`). Se enciende y se apaga con `Ctrl + Win + Intro`:

1. Abra `http://localhost:8000/`. Con `Tab`, lo primero que debe leer es "Saltar al contenido". Pulse `Intro`.
2. Recorra los títulos con `H`: el titular, "Nuestros servicios" y el título del bloque de contacto. Las dos fotografías deben leerse con su descripción.
3. En **Servicios**, vaya con `Tab` a "Solicitar cotización" y pulse `Intro`. Cada campo debe leerse con su etiqueta, y "opcional" donde corresponde.
4. Envíe el formulario vacío. Debe leer "Revise los campos marcados e intente nuevamente" sin que usted busque el mensaje, y cada campo con error debe leer su motivo al recibir el foco.
5. Complete y envíe (espere 3 segundos). Debe leer "Recibimos su solicitud".
6. En `/acceso/`: el botón del ojo debe leerse "Mostrar contraseña" y, tras pulsarlo, "Ocultar contraseña". Ingrese como cliente.
7. En el portal: la navegación debe anunciarse con su nombre; cada carpeta, con su cantidad de documentos; en una carpeta, "Ver" y "Descargar" deben decir de qué documento son.
8. En el panel, suba un archivo en una carpeta: al terminar debe leer el resultado ("Aceptado. Publicado para …"). Abra un diálogo de confirmación: debe leer su título y su mensaje, y `Escape` debe cerrarlo.

Si algo no se lee, o se lee sin sentido, anote la pantalla y el elemento.

**En Firefox** (el visor de PDF se comprobó sin interfaz; falta mirarlo en una ventana):

1. Como cliente, abra la ficha de un PDF y pulse "Ver en pantalla": debe abrirse en una pestaña nueva, dentro del visor de Firefox, con el documento legible.
2. Lo mismo con un JPG y con un PNG: deben verse en la pestaña.
3. Con un DOCX, "Ver" no existe y "Descargar" debe guardar el archivo con su nombre, tildes incluidas.
4. En el panel, a pantalla angosta (`Ctrl + Mayús + M`), abra el menú y suba dos archivos: debe verse la barra de progreso de cada uno.

Safari y Safari en iOS no se pudieron probar en el equipo de desarrollo: repita los pasos 1 a 3 en un dispositivo Apple antes de publicar.

## Pruebas y calidad

```powershell
docker compose run --rm web pytest
docker compose run --rm web ruff check .
docker compose run --rm web ruff format --check .
```

En un equipo con poca memoria, detenga antes el servidor para no tener dos contenedores `web` a la vez: `docker compose stop web`.

Entre las pruebas va `check --deploy` con la configuración de producción (`config/tests/test_configuracion.py`). Para verlo a mano:

```powershell
docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.prod -e SECRET_KEY=<clave de 50 caracteres o más> -e ALLOWED_HOSTS=ejemplo.cl -e SITIO_URL=https://ejemplo.cl -e PROXY_CONFIANZA_REDES=10.0.0.0/8 -e PROXY_HTTPS_ENCABEZADO=X-Forwarded-Proto -e DOCUMENTOS_ALMACENAMIENTO=local -e CORREO_HOST=smtp.ejemplo.cl web python manage.py check --deploy
```

Debe mostrar solo dos advertencias, las de HSTS para subdominios y precarga (`docs/SEGURIDAD.md`, sección 5).

Las pruebas usan PostgreSQL real (el servicio `db`) e informan la cobertura. Los archivos de prueba se generan en memoria y se guardan en una carpeta temporal; el almacenamiento S3 se prueba contra `moto`, un emulador que corre dentro del mismo proceso, sin red. La CI de GitHub Actions ejecuta lo mismo, audita las dependencias con `pip-audit`, comprueba que `docker compose up` levante la aplicación desde cero y construye, prueba y publica la imagen de producción.

## Producción

La aplicación se publica en una máquina de Google Cloud detrás de Cloudflare Tunnel. Todo el procedimiento, incluidos los pasos en las consolas, está en [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md).

Para probar en el equipo la misma imagen que corre en el servidor:

```powershell
docker build --target prod -t web-seba-prod:local .
```

La CI construye esa imagen en cada `push` a `main`, la levanta con `despliegue/compose.prod.yaml` y, si responde, la publica en `ghcr.io/felipe-martinez-contreras/web-seba` con el commit como etiqueta.

### Lista de paso a producción

El primer despliegue es staging, con datos DEMO. El responsable decide el paso a producción cuando se cumple esta lista:

1. `contenido_pendiente --estricto` termina sin pendientes, con una política de privacidad real que mencione el almacenamiento en EE. UU.
2. El simulacro de restauración está hecho y anotado en `docs/DESPLIEGUE.md`, sección 7.
3. HSTS a un año (`SECURE_HSTS_SECONDS=31536000`); en staging está en una hora.
4. Decidido si se activa `SECURE_HSTS_INCLUDE_SUBDOMAINS`, según el dominio real del cliente.
5. El responsable lo aprueba de forma explícita.

La revisión legal por el traslado de datos a EE. UU. es una recomendación documentada (`docs/DESPLIEGUE.md`, sección 14), no un requisito de esta lista.

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
panel/         Vistas del administrador: inicio, clientes, usuarios, carpetas, documentos, solicitudes, contenido del sitio y auditoría
sitio/         Páginas públicas, servicios, datos del negocio, fotografías y contenido pendiente
solicitudes/   Formularios de consulta y cotización, antispam y notificación al profesional
templates/     Plantillas base, componentes, íconos y páginas 404 y 500
static/        Fuentes, fotografías y JavaScript propios (sin CDN), incluida la subida con progreso
static_src/    Entrada de Tailwind con los tokens de diseño
docker/        Script de arranque de desarrollo y comprobación de salud de producción
despliegue/    Compose de producción, guiones de la máquina y tareas programadas
docs/          Especificación, plan, arquitectura, decisiones, trazabilidad, seguridad, despliegue y manual del administrador
```

## Configuración

Todas las variables están documentadas en [`.env.example`](.env.example). La configuración de producción (`config.settings.prod`) se niega a arrancar si faltan `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, `SITIO_URL` (con https), `PROXY_CONFIANZA_REDES` (puede ir vacía) o `DOCUMENTOS_ALMACENAMIENTO` (`local` o `s3`), o si `SECRET_KEY` es la clave de ejemplo. `python manage.py check` falla si el almacenamiento está mal configurado: carpeta de documentos dentro de una ruta de estáticos, o `s3` sin bucket o sin credenciales.

El admin de Django solo se publica si `DJANGO_ADMIN_RUTA` está definida. Si agrega variables nuevas a `.env.example`, cópielas también a su `.env`.
