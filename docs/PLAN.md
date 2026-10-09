# Plan del proyecto

Plan de la Etapa 0 (sección 11 de `ESPECIFICACION.md`). Se actualiza al avanzar cada etapa.

## Estado de las etapas

| Etapa | Contenido | Estado |
| --- | --- | --- |
| 0 | Reconocimiento y plan | Aprobada por el responsable el 09-10-2026 |
| 1 | Base del proyecto | Terminada el 09-10-2026 |
| — | Ajuste visual (tokens azul marino, Inter y componentes del mockup) | Terminado el 09-10-2026; pendiente de aprobación del responsable |
| 2 | Cuentas y acceso | Pendiente |
| 3 | Empresas, usuarios y carpetas | Pendiente |
| 4 | Documentos | Pendiente |
| 5 | Portal del cliente | Pendiente |
| 6 | Sitio público y solicitudes | Pendiente |
| 7 | Endurecimiento y calidad | Pendiente |
| 8 | Despliegue y operación | Pendiente |

## 1. Entorno revisado (09-10-2026)

| Elemento | Resultado | Consecuencia |
| --- | --- | --- |
| Python | 3.12.3 (`py` launcher, único intérprete) | Cumple el mínimo. La app corre en Docker; el Python local queda para el editor |
| uv | 0.11.27 | Se usa para `pyproject.toml` + `uv.lock` (archivo de bloqueo) |
| Git | 2.45.1; rama `main`; `origin` = GitHub `Felipe-Martinez-Contreras/web-seba` | El primer commit es el de esta etapa |
| Git config | `core.autocrlf=true`, pero `.gitattributes` fuerza `eol=lf` | Correcto: los scripts del contenedor quedan en LF |
| Docker | CLI 29.8.2 y Compose v5.5.1. `docker info` responde en 1,2 s (servidor 29.8.2, linux/x86_64, 12 CPU, 3,2 GiB asignados a WSL2; hay 10 imágenes y 11 contenedores de otros proyectos) | El daemon responde. Construir y levantar contenedores se prueba en la Etapa 1 |
| Memoria en uso | Con Docker Desktop abierto quedan ≈ 430 MB de RAM libres en el host (6,8 GB en total) | Riesgo de lentitud. Si la Etapa 1 va muy lenta, se avisa antes de usar el plan B |
| Disco | 14,9 GB libres en C: | Imágenes `slim`/`alpine` y solo 2 contenedores |
| Puerto 5432 | Ocupado por el servicio Windows `postgresql-x64-16` (inicio automático) | El PostgreSQL de Compose no publica 5432 en el host (D3) |
| Puerto 8000 | Libre | — |
| Shell | Windows PowerShell 5.1 | Sin `&&`; los comandos documentados usan `;` o `docker compose ...` |
| Node | 24.19.0 | No se usa (Tailwind va con su CLI standalone) |
| Repositorio | Solo `CLAUDE.md`, `.gitignore`, `.gitattributes` y `docs/ESPECIFICACION.md` | Proyecto desde cero |

Versiones verificadas en fuentes oficiales el 09-10-2026:

- Django: series con soporte 5.2 LTS (5.2.18, hasta abril 2028), 6.0 (6.0.9, solo seguridad hasta abril 2027) y 6.1 (6.1.2, la más reciente). La serie 6 trae CSP nativo (`ContentSecurityPolicyMiddleware`, `SECURE_CSP`).
- `django-otp` 1.7.4 (requiere Django ≥ 4.2). `django-storages` 1.14.6 (abril 2025; sus clasificadores llegan a Django 5.1).

Las versiones que quedaron sin verificar en la Etapa 0 se confirmaron al iniciar la Etapa 1 y están en `DECISIONES.md`: Python 3.13.16, psycopg 3.3.6, WhiteNoise 6.12.0, Tailwind CLI 4.3.3, HTMX 2.0.10 y uv 0.12.24. Gunicorn (26.2.0 verificada) se agrega en la Etapa 8.

## 2. Estructura del proyecto

```
web-seba/
├─ CLAUDE.md  README.md  .env.example  .gitignore  .gitattributes  .dockerignore
├─ pyproject.toml  uv.lock
├─ Dockerfile  compose.yaml  docker/arrancar-dev.sh
├─ manage.py
├─ config/
│  ├─ settings/{base,dev,test,prod}.py
│  ├─ env.py            # lectura de variables de entorno (sin dependencia externa)
│  ├─ urls.py  wsgi.py
├─ core/        # RUT, validadores, mixins de rol, componentes, errores, /salud/
├─ cuentas/     # Usuario, backend de autenticación, activación, recuperación, 2FA
├─ empresas/    # Empresa, Carpeta
├─ documentos/  # Documento, VersionDocumento, almacenamiento, descargas
├─ portal/  panel/  sitio/  solicitudes/  auditoria/
├─ templates/   # base.html, base_publica.html, base_aplicacion.html (portal y panel), componentes/, iconos/, 404.html, 500.html
├─ static_src/css/app.css     # entrada de Tailwind con los tokens de la sección 9
├─ static/{vendor,fonts,js}/   # HTMX, Inter woff2 y JavaScript propio (sin CDN)
├─ docs/
└─ .github/workflows/ci.yml
```

- Cada app: `models.py`, `querysets.py`, `services.py`, `forms.py`, `views.py`, `urls.py`, `templates/<app>/`, `tests/` y `management/commands/`, según lo que necesite.
- Las apps se crean en la etapa que las implementa (R1: nada vacío ni simulado). La Etapa 1 crea `config`, `core`, `cuentas` y `empresas` (ver D2).
- Archivos subidos en desarrollo (desde la Etapa 4): volumen Docker montado en `/var/app/media`, fuera de `static/` y sin URL que lo sirva.
- El CSS compilado queda fuera del código, en `/opt/estaticos` dentro del contenedor; se genera en el build y al arrancar.
- Compose: `web` (Django) y `db` (PostgreSQL 18), con límites de memoria. `tailwind --watch` es un perfil opcional (`--profile css`).
- Pruebas y comandos se ejecutan dentro del contenedor: `docker compose run --rm web pytest`.

## 3. Dependencias

El detalle y el motivo de cada una están en `DECISIONES.md`.

- **Ejecución, instaladas:** Django 6.1.2, psycopg 3.3.6, argon2-cffi 25.1.0 y WhiteNoise 6.12.0.
- **Ejecución, por agregar:** django-otp y segno (Etapa 2), django-storages + boto3 (Etapa 4) y Gunicorn (Etapa 8).
- **Desarrollo y CI:** pytest, pytest-django, pytest-cov, ruff, pip-audit.
- **Estáticos propios:** Tailwind CLI standalone, HTMX, Inter, Lucide.

## 4. Supuestos

1. Valen los supuestos por defecto de la sección 0 (1–3 administradores, volumen de diseño, modo "pausa").
2. Todo dato [COMPLETAR] se trata como desconocido: la interfaz oculta la sección y `contenido_pendiente` lo lista.
3. Marca: tokens azul marino de la sección 9 y estilo del mockup (`docs/DISENO.md`). El logo sigue pendiente: mientras tanto, ícono neutro y nombre en texto.
4. Los administradores también entran con su RUT personal por el mismo formulario.
5. El RUT se guarda normalizado (sin puntos ni guion, K mayúscula) y se muestra como `12.345.678-5`.
6. Email obligatorio para administradores y opcional para clientes (AUT-07 contempla cuentas sin email; se activan copiando el enlace).
7. CI en GitHub Actions.
8. Las etapas 1 a 7 no dependen del proveedor de hosting, correo ni almacenamiento.
9. Python 3.13 en la imagen Docker (confirmado: Django 6.1 admite 3.12, 3.13 y 3.14).

## 5. Desviaciones de la especificación

Aprobadas por el responsable el 09-10-2026.

- **D1. Tokens de Tailwind.** Las versiones actuales del CLI se configuran en CSS (`@theme`), no en `tailwind.config.js`. Los tokens quedan una sola vez en `static_src/css/app.css`, como variables CSS y utilidades.
- **D2. `Empresa` y utilidades de RUT se adelantan a la Etapa 1.** El usuario personalizado debe existir antes de la primera migración, lleva RUT validado y una relación con `Empresa`; además la Etapa 2 prueba que una empresa desactivada pierde el acceso. En la Etapa 1 solo entran los modelos y `core/rut.py` con sus pruebas; las pantallas siguen en las Etapas 2 y 3.
- **D3. PostgreSQL de Compose sin publicar el puerto 5432**, por el servicio local. Si se necesita acceso desde el host, se publica en 5433.
- **D4. Barra de progreso de subida con `<progress>` nativo** y HTMX con `includeIndicatorStyles` desactivado, para cumplir la CSP sin estilos en línea (SEG-02).

## 6. Riesgos conocidos

- **Equipo de desarrollo con poca memoria** (6,8 GB; ≈ 430 MB libres con Docker Desktop abierto). Mitigación: imágenes livianas y, si hace falta, limitar la memoria de WSL2 en `.wslconfig`. El plan B (Django en local contra el PostgreSQL 16 instalado) requiere autorización previa del responsable.
- **`django-storages` no declara soporte para Django 6.x.** Se prueba en la Etapa 4; alternativa: backend propio delgado sobre `boto3`.
- **Contadores de bloqueo en caché de base de datos** no atómicos; aceptable para este volumen. Se documentará en `SEGURIDAD.md`.
- **Un RUT = una cuenta = una empresa.** Una persona que trabaje para dos empresas cliente no puede tener dos cuentas (multiempresa está fuera de alcance, sección 16).
- **Django 6.1 no es LTS.** Hay que migrar a 6.2 LTS cuando se publique.
- **Datos de salud de trabajadores** y Ley 21.719: la región del hosting y del almacenamiento queda pendiente de asesoría legal.
- **VM única en producción** (ver respuesta 5): se aparta de los supuestos de la sección 0.

## 7. Preguntas y respuestas del responsable (09-10-2026)

| # | Pregunta | Respuesta | Efecto |
| --- | --- | --- | --- |
| 1 | ¿Docker funciona? ¿Plan B en local? | Docker Desktop abierto. Si no responde o va muy lento, avisar antes de usar el plan B | `docker info` verificado. El plan B no se usa sin autorización |
| 2 | ¿Django 6.1 o 5.2 LTS? | 6.1 con CSP nativo | Migrar a 6.2 LTS cuando salga (`DECISIONES.md`) |
| 3 | ¿Desviaciones? | Aprobadas D1, D2, D3 y D4 | — |
| 4 | Datos de la sección 0 | Aún no disponibles | Se sigue con [COMPLETAR] |
| 5 | Hosting, correo y almacenamiento | Nada elegido; proponer en la Etapa 8. Probable: una VM e2-micro (free tier), todo en la misma VM | Ver nota |
| 6 | RUT de acceso | Siempre el de la persona | Sin RUT de empresa como acceso |
| 7 | ¿Contactos con dos empresas? | No por ahora | Se mantiene "un RUT = una empresa" |
| 8 | Correo de los commits | `fmartinez19@alumnos.utalca.cl` | Es el configurado en git |
| 9 | Push y CI | Autorizado `git push -u origin main` tras el primer commit, y CI en GitHub Actions | — |
| 10 | Política de privacidad y revisión legal | Las entrega el responsable del negocio | Pendiente |

**Nota sobre la VM única (respuesta 5).** Se aparta de los supuestos de la sección 0 (PaaS, PostgreSQL administrado, almacenamiento S3) y se evalúa en la Etapa 8. Puntos a resolver entonces: memoria muy reducida de una e2-micro para Django y PostgreSQL juntos; respaldos diarios y restauración fuera de la VM (SEG-11); HTTPS y proxy propios; versionado de los archivos; parches del sistema operativo a cargo nuestro. Las etapas 1 a 7 no cambian: el almacenamiento sigue siendo intercambiable (local o S3) y la configuración va por variables de entorno.

## 8. Pendientes abiertos

- Datos comerciales de la sección 0 (responsable).
- Texto de la política de privacidad y revisión legal de la Ley 19.628 y la Ley 21.719 (responsable del negocio).
- Hosting, correo y almacenamiento: propuesta comparada en la Etapa 8, incluida la VM única.
- Migración a Django 6.2 LTS cuando se publique.
- Reevaluar HTMX 4.x antes de la Etapa 4 (DEC-21).
- Etapa 6: agregar a la página 404 el enlace al inicio, cuando exista (DEC-25).
- Etapa 2: pantalla de acceso según las pantallas 2 y 7 del mockup (el campo de contraseña ya existe).
- Etapa 4: zona de subida con progreso.
- Etapa 6: fotografías con licencia y `docs/FOTOS.md` (PUB-08); modelos `Servicio`, `DatosNegocio` y `Solicitud` con la forma de la especificación actualizada (DEC-50).
- Etapa 7: revisión de accesibilidad con lector de pantalla y teclado sobre pantallas reales.

## 9. Etapa 1: qué quedó construido

- Proyecto Django con configuración por entorno (`base`, `dev`, `test`, `prod`) leída de variables de entorno; `prod` se niega a arrancar con configuración faltante o de ejemplo.
- Modelos `Usuario` (RUT como identificador) y `Empresa`, con sus migraciones iniciales, y utilidades de RUT en `core/rut.py` (D2).
- Docker Compose con `web` y `db`; Tailwind compilado en el build y al arrancar.
- Plantillas base (pública, portal y panel), páginas 404 y 500, y componentes: botón, campo, alerta, mensajes, insignia, migas de pan, estado vacío, paginación, encabezado y pie públicos, y barra lateral del panel. Tabla, diálogo de confirmación y zona de subida se agregan en la etapa que los usa.
- Página de referencia de componentes en `/_referencia/componentes/`, solo con `DEBUG`.
- `/salud/`, logs en JSON, CSP nativa, `ruff`, `pytest` con cobertura y CI en GitHub Actions (lint, pruebas, `pip-audit` y arranque con Docker Compose).

No hay todavía ninguna pantalla del negocio: acceso, panel, portal y sitio público llegan en las etapas 2 a 6.

## 10. Ajuste visual previo a la Etapa 2

Pedido por el responsable tras actualizar la sección 9 de la especificación y agregar `docs/DISENO.md` y el mockup.

- **Tokens:** azul marino `#1B2D4F`, fondo `#F5F7FA`, bordes finos, escala 13/14/16/18/20/24/30/40, radios de 8 px (6 px en botones), ancho público de 1.200 px y barra lateral de 240 px.
- **Tipografía:** Inter autoalojada (400, 500, 600 y 700); se retiró IBM Plex Sans.
- **Componentes adaptados:** botón (con variantes para fondo azul marino), campo, alerta, insignia, migas, paginación, estado vacío, encabezado y pie públicos.
- **Componentes nuevos:** campo de contraseña con botón para mostrarla, portada, tarjetas de servicio, de indicador y de empresa, filas de carpeta y de documento con ícono por tipo, tabla que en móvil pasa a lista, pestañas, barra lateral y barra superior del portal y del panel, diálogo de confirmación y marca provisional.
- **Sin cambios de modelo ni pantallas nuevas.** Todo se ve solo en `/_referencia/componentes/`, en desarrollo.
- **Revisión visual:** capturas con Edge emulando 360, 768 y 1280 px, comparadas con el mockup. Se corrigió un desborde horizontal a 360 px y el ajuste de buscador, paginación y títulos largos en pantallas angostas.
