# Decisiones

Decisiones técnicas y dependencias, con su motivo. Cada dependencia indica para qué sirve y qué alternativa se descartó (sección 1, punto 6 de `ESPECIFICACION.md`).

## Decisiones

| # | Fecha | Decisión | Motivo |
| --- | --- | --- | --- |
| DEC-01 | 09-10-2026 | Django 6.1 | Es la serie estable más reciente con soporte (sección 5) y trae CSP nativo. Aprobada por el responsable. **Pendiente: migrar a 6.2 LTS cuando se publique** |
| DEC-02 | 09-10-2026 | CSP con el soporte nativo de Django (`SECURE_CSP`), sin `django-csp` | SEG-02 pide usar el soporte nativo si existe |
| DEC-03 | 09-10-2026 | `uv` con `pyproject.toml` y `uv.lock` | Archivo de bloqueo con versiones fijadas (SEG-09); ya está instalado en el equipo |
| DEC-04 | 09-10-2026 | La aplicación, las pruebas y los comandos corren dentro de Docker | El equipo es Windows; así los comandos son iguales en desarrollo y en CI |
| DEC-05 | 09-10-2026 | El PostgreSQL de Compose no publica el puerto 5432 en el host (D3) | Lo ocupa un PostgreSQL 16 local instalado como servicio de Windows |
| DEC-06 | 09-10-2026 | Tokens de diseño definidos en CSS con `@theme` de Tailwind (D1) | Es la forma de configurar las versiones actuales del CLI; evita duplicar los tokens |
| DEC-07 | 09-10-2026 | Modelos `Usuario` y `Empresa` y utilidades de RUT en la Etapa 1 (D2) | El usuario personalizado debe existir antes de la primera migración y depende de ambos |
| DEC-08 | 09-10-2026 | Barra de progreso con `<progress>` nativo y HTMX sin estilos de indicador en línea (D4) | Cumplir la CSP sin estilos en línea |
| DEC-09 | 09-10-2026 | Apps como paquetes en la raíz del repositorio (`core/`, `cuentas/`, …) | Opción más simple; coincide con las rutas que usa la especificación |
| DEC-10 | 09-10-2026 | Las apps se crean en la etapa que las implementa | R1: nada vacío ni simulado |
| DEC-11 | 09-10-2026 | Lectura de variables de entorno con un módulo propio (`config/env.py`) | Son pocas variables; evita `django-environ` y `dj-database-url` |
| DEC-12 | 09-10-2026 | Detección del tipo real de archivo con firmas de bytes propias y `zipfile` | Solo hay 6 formatos permitidos; evita `python-magic` y la librería del sistema `libmagic` |
| DEC-13 | 09-10-2026 | Bloqueo de acceso y límites de envío implementados sobre la caché en base de datos | Lo indica la sección 5; evita `django-axes` y `django-ratelimit` |
| DEC-14 | 09-10-2026 | CI en GitHub Actions | El remoto es GitHub. Autorizada por el responsable |
| DEC-15 | 09-10-2026 | El RUT de acceso es siempre el de la persona; un RUT pertenece a una sola empresa | Definido por el responsable |
| DEC-16 | 09-10-2026 | RUT guardado normalizado: sin puntos ni guion y con K mayúscula | Una sola forma canónica para la unicidad y la búsqueda |
| DEC-17 | 09-10-2026 | Email obligatorio para administradores y opcional para clientes | AUT-07 contempla cuentas sin email; el enlace de activación se puede copiar |
| DEC-18 | 09-10-2026 | Hosting, correo y almacenamiento se deciden en la Etapa 8 | No hay nada elegido. Se evaluará la opción de una VM única (e2-micro) frente a los supuestos de la sección 0 |
| DEC-19 | 09-10-2026 | Python 3.13.16 (`python:3.13.16-slim-trixie`) | Django 6.1 admite 3.12, 3.13 y 3.14; la serie 3.13 tiene soporte hasta 10-2029 |
| DEC-20 | 09-10-2026 | PostgreSQL 18.6 (`postgres:18-alpine`, fijada por digest) | Cumple "16 o superior" y la imagen ya estaba descargada en el equipo de desarrollo |
| DEC-21 | 09-10-2026 | HTMX 2.0.10 y no 4.0.0 | La 4.0.0 salió el 28-08-2026 y no se pudo confirmar que conserve los eventos de progreso de subida que necesita ADM-08. **Pendiente: reevaluar antes de la Etapa 4** |
| DEC-22 | 09-10-2026 | Gunicorn se agrega en la Etapa 8, con la imagen de producción | En la Etapa 1 no se usa. `django-otp` y `segno` entran en la Etapa 2; `django-storages`, en la 4 |
| DEC-23 | 09-10-2026 | `django.contrib.admin` no se instala hasta la Etapa 2 | ADM-12 exige ruta por variable de entorno y 2FA; antes de eso quedaría un admin sin proteger |
| DEC-24 | 09-10-2026 | CSP nativa activa desde la Etapa 1, con política estricta | Ninguna plantilla nace con estilos o scripts en línea. La verificación formal de SEG-02 sigue en la Etapa 7 |
| DEC-25 | 09-10-2026 | `/` responde 404 hasta la Etapa 6 y la página 404 no enlaza al inicio | Aún no hay página de inicio con contenido real (R1, R2) |
| DEC-26 | 09-10-2026 | `Usuario` hereda de `AbstractBaseUser` y `PermissionsMixin`; el campo "activo" es `is_active` y "último acceso" es `last_login` | Son los nombres que espera Django. `is_staff` e `is_superuser` quedan solo para el superusuario técnico: `create_user` los rechaza y la base impide dárselos a un cliente |
| DEC-27 | 09-10-2026 | Reglas de `Usuario` como `CheckConstraint` en la base: rol coherente con empresa, cliente sin privilegios técnicos y RUT normalizado | La base rechaza datos incoherentes aunque se salte la validación de Python. `Usuario.empresa` usa `PROTECT` |
| DEC-28 | 09-10-2026 | `Empresa` usa UUID como clave primaria | Nunca hay IDs secuenciales en las URL (sección 6) y evita un segundo identificador |
| DEC-29 | 09-10-2026 | `CampoRut` propio: normaliza al guardar y al consultar | Buscar por `12.345.678-5` o por `123456785` da el mismo resultado; una sola forma en la base |
| DEC-30 | 09-10-2026 | Íconos como SVG incluidos en las plantillas (`templates/iconos/`), no como archivos estáticos | Heredan el color del texto sin estilos en línea ni peticiones adicionales |
| DEC-31 | 09-10-2026 | El CSS compilado vive en `/opt/estaticos` dentro del contenedor, fuera del código | El contenedor no escribe en la carpeta del proyecto; funciona igual en Windows y en la CI |
| DEC-32 | 09-10-2026 | Correo con el ajuste `MAILERS` de Django 6.1 (`EMAIL_BACKEND` quedó obsoleto); vacío salvo en desarrollo | Sin proveedor configurado, enviar falla de forma explícita. Se completa en la Etapa 6 |
| DEC-33 | 09-10-2026 | `prod.py` exige `SECRET_KEY` (propia y de 50 caracteres o más), `ALLOWED_HOSTS` (sin `*`) y `DATABASE_URL` | Producción no arranca con configuración faltante o de ejemplo |
| DEC-34 | 09-10-2026 | Formatos `es_CL` propios en `config/formats/` | Django no trae formatos para es-CL; se fijan fechas `dd-mm-aaaa` |
| DEC-35 | 09-10-2026 | En desarrollo corren dos contenedores con límite de memoria (`web` 512 MB, `db` 256 MB); `tailwind --watch` es un perfil opcional | El equipo de desarrollo tiene poca RAM |

## Dependencias de ejecución

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| Django 6.1.2 | Framework | 5.2 LTS: exigiría `django-csp` y no es la serie más reciente |
| psycopg 3.3.6 (`binary`) | Driver de PostgreSQL, con ruedas precompiladas | Django no incluye driver |
| argon2-cffi 25.1.0 | Argon2id como hasher principal (AUT-05) | PBKDF2 nativo: no cumple el requisito |
| django-otp (Etapa 2) | TOTP, códigos de recuperación y 2FA en el admin de Django (AUT-10, ADM-12) | TOTP propio: riesgo de seguridad innecesario. `django-two-factor-auth`: trae vistas, plantillas y más dependencias |
| segno (Etapa 2) | Código QR del enrolamiento TOTP, generado en el servidor como SVG | Sin QR: enrolamiento poco usable. Servicio externo de QR: expondría el secreto |
| django-storages + boto3 (Etapa 4) | Almacenamiento S3 privado y URL firmadas (desde la Etapa 4) | Backend S3 propio. Queda como alternativa si no funciona con Django 6.1 |
| WhiteNoise 6.12.0 | Estáticos, en desarrollo y en producción | Servirlos con Django: no apto para producción |
| Gunicorn (Etapa 8) | Servidor WSGI | `runserver`: no es de producción |

## Dependencias de desarrollo y CI

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| pytest 9.1.1, pytest-django 4.14.0 | Pruebas (sección 12.1) | `unittest` nativo: la especificación pide `pytest-django` |
| pytest-cov 7.1.0 | Cobertura mínima del 85 % | Ninguna nativa |
| ruff 0.16.10 | Lint y formato (RNF-04) | Ninguna nativa |
| pip-audit 2.10.1 (solo CI) | Vulnerabilidades de dependencias en CI (SEG-09) | Ninguna nativa |

## Herramientas del build

| Herramienta | Versión | Origen | Verificación |
| --- | --- | --- | --- |
| uv | 0.12.24 | `ghcr.io/astral-sh/uv:0.12.24` (Docker) y PyPI (CI) | Versión fijada; el `uv.lock` se generó con ella |
| Tailwind CLI standalone | 4.3.3 | `https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64` | sha256 `dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a`, tomado del `sha256sums.txt` de la release y exigido por el `Dockerfile` |

## Archivos de terceros incluidos en el repositorio

Descargados el 09-10-2026 desde el registro npm y servidos desde la propia aplicación, sin CDN. Para comprobar uno: `Get-FileHash <archivo> -Algorithm SHA256`.

| Paquete | Versión | Licencia | Origen | sha256 del paquete |
| --- | --- | --- | --- | --- |
| htmx.org | 2.0.10 | 0BSD | `https://registry.npmjs.org/htmx.org/-/htmx.org-2.0.10.tgz` | `577ad40c1c94c9de47edb89e0aec78a8353d36024c50017eb53e02992a55e889` |
| @ibm/plex-sans | 1.1.0 | OFL-1.1 | `https://registry.npmjs.org/@ibm/plex-sans/-/plex-sans-1.1.0.tgz` | `c3818979c2a2c82927ea3e7c485e389a18de0b7462887dd4f7acc9a525568962` |
| lucide-static | 1.54.0 | ISC | `https://registry.npmjs.org/lucide-static/-/lucide-static-1.54.0.tgz` | `e902c38c3b0b132c90c26cd24e7021068e278a53c4c72fc3e49ef53dfe9d35fa` |

| Archivo en el repositorio | Ruta dentro del paquete | sha256 del archivo |
| --- | --- | --- |
| `static/vendor/htmx.min.js` | `package/dist/htmx.min.js` | `71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de` |
| `static/vendor/LICENCIA-htmx.txt` | `package/LICENSE` | `d3d2456f76414f2456104660ebd65aff1c04cd7966b942bdabd63f3cdb316a38` |
| `static/fonts/IBMPlexSans-Regular.woff2` | `package/fonts/complete/woff2/IBMPlexSans-Regular.woff2` | `ba711a3085ff9f27440b6b9c4550cfc47c97bf36591d5da958b975bb3add8c1a` |
| `static/fonts/IBMPlexSans-Medium.woff2` | `package/fonts/complete/woff2/IBMPlexSans-Medium.woff2` | `5660f8a658f8bb50dbc005232f885eadffd2bc1c235c4f6fbb63469d1f9cde6d` |
| `static/fonts/IBMPlexSans-SemiBold.woff2` | `package/fonts/complete/woff2/IBMPlexSans-SemiBold.woff2` | `f78048030eab62e860efa39a0df79e2e5581bf122eb95b9bc42c0b8a4988d205` |
| `static/fonts/LICENCIA-IBM-Plex.txt` | `package/LICENSE.txt` | `37784b44044a4ffd9256702b7c0982c37e5c8887ba90c6dca0479aea93dc898d` |
| `templates/iconos/chevron-left.svg` | `package/icons/chevron-left.svg` | `a57c5c9b0516a4114236cb0ece0e53ed84b144fce50e1ff8b61e209869b17ad5` |
| `templates/iconos/chevron-right.svg` | `package/icons/chevron-right.svg` | `fece1122c8afb1bf5420fbbebab8c06823d9104041047cc27b0a2dc0c5210f6b` |
| `templates/iconos/circle-alert.svg` | `package/icons/circle-alert.svg` | `1c249776908aed049350da3a55f89e59febde9583aee2435389bdcddcc728df0` |
| `templates/iconos/circle-check.svg` | `package/icons/circle-check.svg` | `e4e78fa7f2f56508aa4432e911578ef5f726527ce1d879c1f8b587db0a42e0e3` |
| `templates/iconos/inbox.svg` | `package/icons/inbox.svg` | `215b4db66da94b3fff4330f21fdc8d0935212d069885b98b0e9fda64ad159851` |
| `templates/iconos/info.svg` | `package/icons/info.svg` | `cc1dd1dda0ecc62cd2ab3f92e75bf3d360e23c819273eb1b9ace00d3ceffcdd5` |
| `templates/iconos/loader-circle.svg` | `package/icons/loader-circle.svg` | `334abce32e8da0ff8f385522a726ba44e5681561e35d0c9a36cbdc0a5b88e67e` |
| `templates/iconos/menu.svg` | `package/icons/menu.svg` | `2e13846bbadb5cf0c8eac246b0d7f53133688c688f3115b9735bade90aca0519` |
| `templates/iconos/triangle-alert.svg` | `package/icons/triangle-alert.svg` | `b94124235a81cdf4f8e2bb813e955049e0d501cd30793e495b2d62c584a7a8af` |
| `templates/iconos/x.svg` | `package/icons/x.svg` | `4dafa4724c98da256b066efe3ea32540d929ebf20dd727ecf466c2f206d7d13d` |
| `templates/iconos/LICENCIA-lucide.txt` | `package/LICENSE` | `b495047bd93a9b06913511076f504daba17d5bbeb3e0650f3bb53a4220329c57` |

Los archivos se copiaron sin modificar. Única excepción: `LICENCIA-IBM-Plex.txt` venía con fin de línea CRLF y se convirtió a LF, que es como el repositorio guarda el texto (`.gitattributes`); su hash es el del archivo ya convertido.

## Dependencias descartadas

`django-environ`, `dj-database-url`, `python-magic`, `filetype`, `django-axes`, `django-ratelimit`, `django-csp`, `django-htmx`, `factory-boy`, `python-json-logger`, `mypy` y `django-debug-toolbar`: lo que aportan se resuelve con Django o con la biblioteca estándar. El servicio de errores opcional (RNF-05) se decide en la Etapa 7.
