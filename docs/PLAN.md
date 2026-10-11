# Plan del proyecto

Plan de la Etapa 0 (sección 11 de `ESPECIFICACION.md`). Se actualiza al avanzar cada etapa.

## Estado de las etapas

| Etapa | Contenido | Estado |
| --- | --- | --- |
| 0 | Reconocimiento y plan | Aprobada por el responsable el 09-10-2026 |
| 1 | Base del proyecto | Terminada el 09-10-2026 |
| — | Ajuste visual (tokens azul marino, Inter y componentes del mockup) | Terminado el 09-10-2026; pendiente de aprobación del responsable |
| 2 | Cuentas y acceso | Aprobada por el responsable el 11-10-2026 |
| 3 | Empresas, usuarios y carpetas | Aprobada por el responsable el 11-10-2026, tras probar el flujo en el navegador |
| 4 | Documentos | Aprobada por el responsable el 11-10-2026, tras probarla en el navegador |
| 5 | Portal del cliente | Terminada el 11-10-2026; pendiente de aprobación del responsable |
| 6 | Sitio público y solicitudes | Terminada el 11-10-2026, con las fotografías aprobadas; pendiente de aprobación del responsable |
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
├─ documentos/  # Documento, VersionDocumento, validación, almacenamiento, descargas y papelera
├─ portal/  panel/  sitio/  solicitudes/  auditoria/
├─ templates/   # base.html, base_publica.html, base_aplicacion.html (portal y panel), componentes/, iconos/, 404.html, 500.html
├─ static_src/css/app.css     # entrada de Tailwind con los tokens de la sección 9
├─ static/{vendor,fonts,js}/   # HTMX, Inter woff2 y JavaScript propio (sin CDN)
├─ docs/
└─ .github/workflows/ci.yml
```

- Cada app: `models.py`, `querysets.py`, `services.py`, `forms.py`, `views.py`, `urls.py`, `templates/<app>/`, `tests/` y `management/commands/`, según lo que necesite.
- Las apps se crean en la etapa que las implementa (R1: nada vacío ni simulado). La Etapa 1 crea `config`, `core`, `cuentas` y `empresas` (ver D2).
- Archivos subidos en desarrollo: volumen Docker `documentos_datos` montado en `/var/app/media`, fuera de `static/` y sin URL que lo sirva.
- El CSS compilado queda fuera del código, en `/opt/estaticos` dentro del contenedor; se genera en el build y al arrancar.
- Compose: `web` (Django) y `db` (PostgreSQL 18), con límites de memoria. Perfiles opcionales: `tailwind --watch` (`--profile css`) y el emulador de S3 (`--profile s3`).
- Pruebas y comandos se ejecutan dentro del contenedor: `docker compose run --rm web pytest`.

## 3. Dependencias

El detalle y el motivo de cada una están en `DECISIONES.md`.

- **Ejecución, instaladas:** Django 6.1.2, psycopg 3.3.6, argon2-cffi 25.1.0, WhiteNoise 6.12.0, django-otp 1.7.4, segno 1.6.6 y boto3 1.43.111.
- **Ejecución, por agregar:** Gunicorn (Etapa 8).
- **Desarrollo y CI:** pytest, pytest-django, pytest-cov, ruff, pip-audit, y moto (con flask y flask-cors) como emulador de S3.
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
- **El almacenamiento S3 solo se probó contra un emulador** (`moto`), que no valida firmas ni vencimientos. Falta el bucket real, con `comprobar_almacenamiento --firma`, antes de producción (Etapa 8). Se descartó `django-storages`, que no declara soporte para Django 6.x (DEC-96).
- **Con el versionado del bucket, purgar la papelera no borra el archivo al instante** (ver `SEGURIDAD.md`). Importa para las solicitudes de eliminación de datos.
- **Una notificación de solicitud puede tardar hasta 15 minutos.** Si el proceso se reinicia antes de que parta el hilo que envía el correo, la solicitud queda "por enviar" y la retoma `reintentar_notificaciones`. La solicitud nunca se pierde.
- **El límite de 5 envíos por hora es por IP.** Varias personas detrás de una misma IP (una oficina) comparten el cupo; quien lo supera ve el aviso neutro con el teléfono y el correo de contacto.
- **Contadores de bloqueo en caché de base de datos** no atómicos; aceptable para este volumen. Documentado en `SEGURIDAD.md`, junto con las demás limitaciones de la Etapa 2.
- **Dos clics con carpetas grandes (CLI-07).** En una carpeta con más de 25 documentos, los de la segunda página quedan a dos clics solo por el buscador (DEC-122).
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
- Etapa 8: programar `depurar_auditoria` una vez al mes y `purgar_papelera` a diario.
- Etapa 8: comprobar el almacenamiento contra un bucket de prueba real con `comprobar_almacenamiento --firma`, incluido que el objeto no se lea sin firma (prueba 11); credenciales con permisos mínimos; versionado del bucket con expiración de versiones antiguas, y el procedimiento para una solicitud de eliminación de datos.
- Etapa 8: límite de tamaño de subida en el servidor web y el proxy (SEG-07) y tiempos de espera para 25 MB (RNF-02).
- Etapa 8: la base de producción debe permitir crear la extensión `unaccent`, o traerla creada (DEC-116).
- Revisión del responsable: recorrer el portal en un teléfono real (pasos en el README).
- Etapa 7: la barra de pestañas muestra una barra de desplazamiento fina en pantallas angostas (portal y panel); es solo de aspecto.
- Etapa 7: "Ver en pantalla" con `Content-Security-Policy: sandbox` en Firefox y Safari (en Edge ya se comprobó).
- Revisión del responsable: recorrer E2 y E6 en el navegador con un administrador real y su 2FA, y probar el botón "Copiar enlace".
- Etapa 7: repetir en staging la medición de tiempos de `SEGURIDAD.md`.
- Etapa 8: valor de `PROXY_CONFIANZA_REDES` según el hosting; formato de los logs de Gunicorn y del proxy sin el token de los enlaces; proveedor SMTP.
- Etapa 7: revisión de accesibilidad con lector de pantalla y teclado sobre pantallas reales.
- Fotos reales del profesional: cuando existan, reemplazan a las de banco (`docs/FOTOS.md`).
- Responsable: cargar los datos del negocio y los servicios en Panel › Configuración › Contenido del sitio; hasta entonces el sitio público muestra solo navegación y pie.
- Etapa 8: definir `NOTIFICACIONES_DESTINATARIOS` y el proveedor SMTP; programar `reintentar_notificaciones` cada 15 minutos; ejecutar `contenido_pendiente --estricto` antes de publicar.
- Etapa 8: `cargar_demo` en staging con `DEMO_PERMITIDO=true`; producción no define esa variable.
- Etapa 7: `favicon.ico` (hoy responde 404) y Lighthouse del sitio público.
- Logo real: hasta tenerlo se usa la marca provisional (DEC-48).

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

## 11. Etapa 2: qué quedó construido

Requisitos AUT-01 a AUT-12, ADM-12 y SEG-03. El detalle de cada control está en `SEGURIDAD.md` y las decisiones en `DECISIONES.md` (DEC-52 a DEC-78).

- **Acceso** en `/acceso/` con RUT y contraseña, mensaje genérico y redirección por rol. Cierre de sesión solo por POST.
- **Bloqueo** por RUT e IP y por IP, con la IP tomada del proxy de confianza. Desbloqueo por una vista del panel y por comando.
- **Enlaces de un solo uso** para activar la cuenta (72 horas) y restablecer la contraseña (1 hora). Al usarlos, la persona queda con la sesión iniciada.
- **Recuperación** en `/recuperar/`, con pantalla fija y el correo enviado fuera de la petición.
- **2FA de administradores**: TOTP y 10 códigos de recuperación. Solo se enrola en la sesión que acaba de usar un enlace.
- **"Mi cuenta"** en `/cuenta/`: datos de solo lectura y cambio de contraseña.
- **Corte inmediato** al desactivar un usuario o su empresa.
- **Auditoría**: modelo `EventoAuditoria`, que solo admite agregar, con los eventos de esta etapa.
- **Inicios mínimos** del portal (`/portal/`) y del panel (`/panel/`), como destinos reales del acceso.
- **Admin de Django** en la ruta de `DJANGO_ADMIN_RUTA`, solo para el superusuario técnico con 2FA.
- **Comandos**: `crear_administrador`, `restablecer_2fa` y `desbloquear_acceso`.

Lo que todavía no existe: crear empresas y usuarios desde el panel, y entregarles su enlace de activación (Etapa 3). Hasta entonces, un cliente solo se puede crear desde la consola de Django.

### Diferencias con el plan aprobado de la etapa

- La pantalla de acceso no se agregó a la página de referencia de componentes: existe la pantalla real en `/acceso/` (DEC-78).
- El hilo de envío de correo parte entre 2 y 4 segundos después de la petición, no de inmediato: la medición de tiempos mostró que, si partía de inmediato, la respuesta tardaba más cuando la cuenta existía (DEC-64).
- Se agregó el ocultamiento del token de los enlaces en los logs, detectado al revisar la aplicación en el navegador (DEC-71).
- Se agregó el cierre de sesión tras 5 fallos al cambiar la contraseña (DEC-68).

Respuestas del responsable al cierre (11-10-2026): la pantalla de acceso mantiene el título "Acceso clientes" y la espera de 2 a 4 segundos del correo de recuperación queda aprobada.

## 12. Etapa 3: qué quedó construido

Requisitos ADM-01 a ADM-07, ADM-11 y AUD-03, con sus eventos de auditoría. Decisiones DEC-79 a DEC-94.

- **Panel** con Inicio, Clientes, Auditoría y Configuración (Mi cuenta). El buscador superior busca clientes por RUT o razón social.
- **Inicio** con datos reales: clientes activos, cuentas pendientes de activación por cliente y clientes recientes.
- **Clientes**: listado con búsqueda, filtro por estado y paginación de a 25; alta con las cinco carpetas base (opción marcada por defecto); edición; desactivar y reactivar con confirmación. Sin borrado.
- **Ficha del cliente** con tres pestañas: Documentos (por ahora, sus carpetas), Usuarios y Actividad.
- **Carpetas**: crear, editar, ordenar con subir y bajar, y eliminar con confirmación.
- **Usuarios**: crear, editar, desactivar y reactivar; estado (pendiente, activo, bloqueado, inactivo) y último acceso; enlace de activación o de restablecimiento que se copia y, si el correo está configurado, también se envía; botón de desbloqueo en la fila de la cuenta bloqueada.
- **Auditoría**: listado de solo lectura con filtros por cliente, RUT, acción y fechas; comando `depurar_auditoria` con `AUDITORIA_RETENCION_MESES`.
- **E2 completo**: crear empresa y usuario, copiar el enlace, definir la contraseña y entrar al portal vacío.

Lo que todavía no existe: documentos (Etapa 4), portal completo (Etapa 5), solicitudes y contenido del sitio (Etapa 6).

### Diferencias con el plan aprobado de la etapa

- La cabecera de la ficha no usa `tarjeta_empresa.html`: lleva el mismo aspecto, pero necesita la insignia de estado y los botones Editar y Desactivar, que ese componente no tiene.
- Las acciones de cada usuario van en un menú "Acciones"; solo "Desbloquear" queda como botón visible en la fila.
- Las tablas de usuarios y de eventos pasan a lista hasta los 1.280 px (DEC-92): a 768 px la de usuarios desbordaba.
- Se agregó el evento "Correo con enlace de acceso", con el resultado del envío, y el evento "Depuración de la auditoría".
- Respuestas del responsable al cierre (11-10-2026): el menú "Acciones" por usuario queda como está; "Pendiente" en ámbar queda aprobado (DEC-84); para desbloquear a un administrador basta con el comando (DEC-85).
- La revisión visual se hizo con Edge sin interfaz sobre una base de datos temporal (DEC-94), con una sesión de administrador creada para ese fin. No se recorrió el ingreso con un código 2FA real: queda para la revisión del responsable.

## 13. Etapa 4: qué quedó construido

Requisitos DOC-01 a DOC-09, ADM-08 y ADM-09, el cierre de ADM-07 y el indicador de documentos de ADM-02, con sus eventos de auditoría. Decisiones DEC-95 a DEC-113. El flujo completo está en `ARQUITECTURA.md`.

- **App `documentos`**: `Documento` y `VersionDocumento` (las versiones solo se agregan), consultas `visibles_para`, servicios y validación.
- **Validación en el servidor**: lista blanca de formatos, tipo real por firma de bytes, estructura OOXML, rechazo de macros, tamaño y archivo vacío. Cada rechazo lleva su motivo.
- **Almacenamiento intercambiable**: local (volumen fuera del código) y S3 (`boto3`), con la clave `docs/<uuid_empresa>/<uuid_version>`.
- **Ver y descargar**: por vistas con sesión, con evento de auditoría. Local: transmisión con `nosniff` y CSP `sandbox`. S3: redirección a una URL firmada de 120 segundos.
- **Panel**: página de cada carpeta con la subida de varios archivos (progreso y resultado por archivo), ficha del documento (editar, mover, reemplazar, historial, eliminar) y papelera por cliente (restaurar).
- **Portal**: solo los endpoints de ver y descargar la versión vigente. Sus pantallas son de la Etapa 5.
- **Carpetas**: una carpeta con documentos, también en la papelera, no se elimina.
- **Inicio del panel**: indicador de documentos subidos en los últimos 30 días.
- **Comandos**: `purgar_papelera` y `comprobar_almacenamiento`.
- **Página 400 propia** y `docs/ARQUITECTURA.md`.

Lo que todavía no existe: las pantallas del portal (Etapa 5), solicitudes y contenido del sitio (Etapa 6), y la verificación del almacenamiento contra un bucket real (Etapa 8).

### Diferencias con el plan aprobado de la etapa

- Agregados pedidos por el responsable al aprobar el plan: `Content-Security-Policy: sandbox` en la entrega local (DEC-103), el motivo propio para Office antiguo o con contraseña (DEC-102) y la nota sobre la purga con el versionado del bucket (`SEGURIDAD.md`).
- Se instala `moto[s3]` con `flask` y `flask-cors`, no `moto[s3,server]`: el extra `server` arrastra paquetes que el emulador de S3 no usa (DEC-97).
- `comprobar_almacenamiento` sumó dos opciones: `--crear-bucket`, para el emulador, y `--firma`, para el bucket real. La segunda nació de un hallazgo: el emulador no valida la firma ni el vencimiento de las URL.
- Tras subir, la lista de documentos se actualiza sola (DEC-113); el plan no lo decía y la revisión en el navegador mostró que hacía falta.
- El reemplazo de un archivo usa un formulario normal, sin barra de progreso.
- Se corrigió un error detectado por una prueba de la Etapa 3: al contar documentos por carpeta, la lista perdía su orden.

Respuestas del responsable al cierre (11-10-2026): autorizado el `push` y la verificación de la CI; la publicación inmediata queda aprobada, con el aviso del cliente en la zona de subida y en cada resultado (DEC-114); la barra de progreso al reemplazar se agrega al inicio de la Etapa 5. El responsable probó la etapa en el navegador y la aprobó el 11-10-2026.

## 14. Etapa 5: qué quedó construido

Requisitos CLI-01 a CLI-08 (CLI-06 parcial), el cierre de DOC-09 y de ADM-08, las pruebas 2, 3 y 4 de la sección 12.2 y los escenarios E3, E4, E5 y E7 del lado del cliente. Decisiones DEC-115 a DEC-126.

- **Reemplazo con barra de progreso** en la ficha del documento del panel, con el mismo `subida.js`.
- **Inicio del portal:** saludo, tarjeta de la empresa, buscador, "Sus carpetas" con contador y fecha, y los 10 documentos más recientes, con "Nuevo" durante 14 días.
- **Carpetas y carpeta:** documentos con tipo, tamaño y fecha, Ver y Descargar en cada fila, orden por fecha o por nombre, de a 25.
- **Buscador** por título, sin distinguir mayúsculas ni tildes (`unaccent`), con el texto limitado a 100 caracteres.
- **Ficha del documento:** migas, datos, Descargar y Ver en pantalla en una pestaña nueva. Sin visor incrustado.
- **Solo lectura:** todas las rutas del portal admiten solo GET y parten de `visibles_para`.
- **Menú del portal:** Inicio, Carpetas y Mi cuenta, con el buscador en la barra superior.
- **Áreas táctiles:** los enlaces de texto sueltos pasan a 44 px de alto, también en el acceso y la recuperación.

Lo que todavía no existe: el contacto del profesional en el estado vacío (Etapa 6), el sitio público y las solicitudes (Etapa 6).

### Diferencias con el plan aprobado de la etapa

- Agregado pedido por el responsable al aprobar el plan: tope de 100 caracteres en la búsqueda y prueba de que un texto con `<script>` se muestra escapado.
- Se agregó la clase `enlace-tactil` (DEC-125): la medición a 360 px mostró enlaces de 17 a 20 px de alto, dos de ellos en pantallas de la Etapa 2 (acceso y recuperación).
- El resultado del reemplazo reutiliza `resultado_subida.html`, con un parámetro nuevo para el número de versión.
- La revisión en el navegador fue con Edge sin interfaz emulando un teléfono (360 px, táctil), no con un teléfono real. La sesión del administrador se creó por script, sin código 2FA real, y el enlace de E7 se leyó de la consola del contenedor.

## 15. Etapa 6: qué quedó construido

Requisitos PUB-01 a PUB-08, SOL-01 a SOL-11, ADM-10, el cierre de ADM-01, ADM-02 y CLI-06, SEG-06, SEG-13 y el mecanismo de SEG-12; pruebas 12, 13 y 14 de la sección 12.2 y escenario E1. Decisiones DEC-127 a DEC-142.

- **Sitio público:** Inicio (portada con fotografía, servicios, bloque de contacto con el formulario de cotización y pie), Servicios, Contacto, Solicitar cotización, Política de privacidad, `sitemap.xml` y `robots.txt`. Todo el contenido sale de la base de datos.
- **Formularios:** consulta y cotización con validación en el servidor, antispam (campo trampa, 3 segundos, 5 por hora por IP) y confirmación neutra.
- **Solicitudes:** se guardan primero y se notifican después, fuera de la petición. El resultado queda en la solicitud: enviada, fallida o correo no configurado.
- **Panel:** bandeja con pestañas Consultas y Cotizaciones, detalle con estado, notas y reintento; Contenido del sitio (datos del negocio y servicios); inicio con indicadores, solicitudes recientes y avisos.
- **Contenido pendiente:** una sola regla (`sitio/pendientes.py`) para el sitio, el panel y el comando `contenido_pendiente`.
- **Fotografías:** tres fotos de Unsplash (una obra en construcción, un casco colgado y un casco sobre fondo oscuro), optimizadas y registradas en `docs/FOTOS.md`.
- **Portal:** contacto del profesional en el estado vacío, cuando está registrado.
- **Comandos:** `contenido_pendiente`, `reintentar_notificaciones` y `cargar_demo`.

Estado real del sitio hoy: los datos de la sección 0 siguen en [COMPLETAR], así que el sitio público muestra solo la navegación y el pie. Con `cargar_demo` se ve completo, con datos marcados DEMO.

### Diferencias con el plan aprobado de la etapa

- **Fotografías.** Ninguna de las candidatas del plan quedó. Al verlas se descartaron dos: una muestra un rostro y el logo de una empresa; la otra, un trabajador en altura sin protección contra caídas. De la primera selección, el responsable aprobó la de contacto y pidió cambiar la portada (una refinería, por una obra en construcción) y la de acceso (su humo se lee como contaminación). Las tres finales son de Unsplash, sin personas; no se encontró un trabajador de espaldas con casco y chaleco que cumpliera el criterio.
- **Datos de prueba.** El plan decía que un dato con "TEXTO DE PRUEBA" estaba pendiente. Quedó en dos reglas: lo vacío o con [COMPLETAR] no se muestra; lo de prueba (los datos de `cargar_demo`) sí se muestra, y ambos se listan como pendientes (DEC-137).
- **`cargar_demo` exige un administrador.** Los documentos de demostración necesitan a alguien que los haya subido (DEC-138).
- **Página de confirmación.** Solo se muestra a quien acaba de enviar un formulario; abrirla directamente lleva al inicio (DEC-131).
- **Páginas sin contenido.** Además de no mostrarse sus secciones, no se indexan ni entran al sitemap (DEC-135).
- **Áreas táctiles.** La medición a 360 px encontró enlaces de 17 a 40 px de alto en el panel y en la marca del encabezado; se llevaron a 44 px.
- **Pruebas anteriores actualizadas.** Tres pruebas afirmaban el estado anterior y se ajustaron al nuevo: las pantallas de acceso ahora llevan una imagen (solo la propia), y el inicio y el menú del panel ahora incluyen las solicitudes.
- **Commits.** Se hicieron al final, después de que el responsable aprobó las fotos: el plan comprometía mostrárselas antes de confirmarlas.
- La revisión en el navegador fue con Edge sin interfaz sobre una base temporal (DEC-94), con una sesión de administrador creada por script. La llegada real de un correo por un proveedor SMTP no se probó: no hay proveedor.
