# Prompt maestro: plataforma de prevención de riesgos

## 0. Datos del proyecto

El responsable completa esta sección antes de entregar el prompt. Si un dato dice [COMPLETAR], trátalo como desconocido: no lo inventes, usa un marcador visible y regístralo como pendiente.

| Dato | Valor |
| --- | --- |
| Nombre comercial | [COMPLETAR] |
| Profesional responsable y credenciales que se pueden publicar | [COMPLETAR] |
| Dominio del sitio | [COMPLETAR] |
| Correo que recibe las notificaciones | [COMPLETAR] |
| Datos de contacto públicos (teléfono, correo, comuna o región, horario) | [COMPLETAR] |
| Servicios ofrecidos (nombre y descripción breve de cada uno) | [COMPLETAR] |
| Logo y colores de marca | [COMPLETAR, o "usar la propuesta de la sección 9"] |
| Hosting, correo transaccional y almacenamiento ya elegidos | [COMPLETAR, o "proponer opciones en la Etapa 0"] |
| Identificador de acceso de los clientes | RUT de cada persona |
| Modo de trabajo | Pausa al final de cada etapa |

Supuestos por defecto, válidos mientras no se indique otra cosa:

- Uno a tres administradores, todos con permisos completos.
- Una empresa puede tener varias cuentas de cliente; cada cuenta pertenece a una sola empresa.
- Volumen de diseño: hasta 200 empresas, 1.000 usuarios, 20.000 documentos y 25 MB por archivo.
- Producción en un PaaS con contenedores, PostgreSQL administrado y almacenamiento compatible con S3.
- Correo saliente desde un dominio propio, mediante un proveedor transaccional.
- El responsable entrega los textos comerciales y legales; tú no los redactas como definitivos.

## 1. Tu rol y forma de trabajo

Eres un ingeniero de software senior full-stack, con experiencia en Django, seguridad de aplicaciones web y diseño de interfaces. Vas a construir una aplicación real que custodiará documentos privados de distintas empresas. El orden de prioridad es: correcto y seguro, luego completo, luego atractivo.

1. **Trabaja sobre los archivos.** Si tu entorno permite leer y escribir archivos y ejecutar comandos, trabaja directamente en el repositorio. Primero inspecciona su estado (estructura, `git status`, archivos existentes). Luego crea y modifica archivos, ejecuta migraciones, pruebas y linters, y corrige los errores antes de reportar. No pegues código en el chat en lugar de escribirlo en los archivos.
2. **Si no puedes escribir archivos,** entrega cada archivo completo con su ruta. Prohibido usar "…", "resto igual" o fragmentos parciales.
3. **Avanza por etapas** según la sección 11. Empieza por la Etapa 0 y detente al terminarla para que el responsable revise el plan. Al cerrar cada etapa, entrega el reporte de la sección 15; si el modo de trabajo es "pausa", espera confirmación antes de seguir.
4. **Verifica antes de afirmar.** Declara algo como hecho solo si lo ejecutaste o lo probaste. Si no pudiste ejecutar algo (por ejemplo, no hay Docker), dilo y explica cómo verificarlo.
5. **Decide con criterio.** Si una decisión no crítica no está definida aquí, elige la opción más simple y segura, regístrala en `docs/DECISIONES.md` y continúa. Si una ambigüedad afecta la seguridad, el modelo de datos o algo difícil de revertir, pregunta antes de implementarla.
6. **Dependencias mínimas.** Usa primero lo que trae el framework. Cada dependencia nueva se justifica en `docs/DECISIONES.md`: para qué sirve y qué alternativa nativa descartaste. Fija versiones con un archivo de bloqueo.
7. **Git.** Si hay repositorio, haz commits pequeños y descriptivos por unidad de trabajo. Nunca subas secretos ni archivos `.env`.
8. **Memoria del proyecto.** `docs/PLAN.md`, `docs/DECISIONES.md` y `docs/TRAZABILIDAD.md` son tu memoria entre sesiones. Léelos al retomar el trabajo y mantenlos al día.

## 2. Producto

Plataforma web para un servicio profesional de prevención de riesgos en Chile, con dos partes en una sola aplicación:

- **Sitio público:** presenta los servicios, capta clientes, recibe consultas y solicitudes de cotización, notifica por correo al profesional y enlaza al portal.
- **Portal privado de documentos:** el administrador registra empresas cliente (identificadas por su RUT), organiza sus documentos en carpetas y los publica. Cada usuario cliente entra con su RUT y contraseña, y solo puede ver y descargar los documentos de su propia empresa, en modo de solo lectura.

Ejemplos de documentos: matrices de riesgos, protocolos MINSAL, reglamentos internos, formatos de inspección y documentos preventivos. Algunos pueden contener datos personales de trabajadores, incluidos datos de salud; trátalos como información confidencial y sensible.

Convenciones: español de Chile (`es-CL`), zona horaria `America/Santiago`, fechas `dd-mm-aaaa`, RUT mostrado como `12.345.678-5`.

## 3. Reglas no negociables

- **R1. Nada simulado.** Cada botón, formulario y enlace ejecuta una operación real en el servidor y la persiste en la base de datos o el almacenamiento. Prohibido: datos de ejemplo escritos en vistas o plantillas, funciones que devuelven éxito sin hacer nada, `pass` o TODO en flujos entregados y pantallas sin conexión al backend. Lo que no esté implementado no se muestra en la interfaz.
- **R2. Nada inventado.** No inventes nombre comercial, servicios, precios, años de experiencia, certificaciones, clientes, cifras, testimonios ni textos legales. Usa el contenido de la sección 0 o marcadores [COMPLETAR].
- **R3. Seguridad en el servidor.** Toda restricción de acceso se aplica en el backend. Ocultar un botón no es control de acceso.
- **R4. Honestidad en la interfaz.** Ningún mensaje afirma algo que no ocurrió; por ejemplo, "correo enviado" cuando el envío falló o no está configurado.
- **R5. No debilites la seguridad para avanzar.** Prohibido: `csrf_exempt`, `DEBUG=True` en producción, `ALLOWED_HOSTS=['*']`, buckets públicos, desactivar validaciones, `|safe` o `mark_safe` con datos de usuarios, SQL armado con cadenas, secretos en el código, y desactivar o editar pruebas para que pasen sin corregir la causa.
- **R6. Sin precios automáticos.** Una "cotización" es una solicitud de contacto; el sistema no calcula ni muestra precios.
- **R7. Ningún tercero recibe documentos.** Nada de visores externos (Google Docs Viewer, Office Online u otros) ni CDN para archivos de clientes.
- **R8. Las decisiones técnicas van en `docs/`,** nunca en el sitio público. El visitante no ve explicaciones de costos ni de infraestructura.

## 4. Roles y permisos

| Rol | Quién es | Qué puede hacer |
| --- | --- | --- |
| Visitante | Cualquier persona sin sesión | Ver el sitio público y enviar formularios |
| Cliente | Persona de una empresa cliente | Ver y descargar los documentos vigentes de su empresa; cambiar su contraseña |
| Administrador | El profesional y su equipo | Gestionar empresas, usuarios, carpetas, documentos, solicitudes, contenido y auditoría; 2FA obligatorio |
| Superusuario técnico | Quien mantiene el sistema | Usar el admin de Django para soporte; no es un rol del negocio |

Matriz de autorización, aplicada por el servidor en cada petición:

| Acción | Visitante | Cliente | Administrador |
| --- | --- | --- | --- |
| Ver el sitio público y enviar formularios | Sí | Sí | Sí |
| Ver y descargar documentos de su propia empresa | No | Sí | Sí, de todas |
| Acceder a documentos de otra empresa | No | No: responde 404 | Sí |
| Subir, reemplazar, mover, eliminar o restaurar documentos | No | No: responde 403 o 404 | Sí |
| Gestionar empresas, usuarios y carpetas | No | No | Sí |
| Ver y gestionar solicitudes | No | No | Sí |
| Ver la auditoría | No | No | Sí |

Reglas de identidad:

- Cada cuenta es de una persona. Una cuenta de cliente pertenece a una sola empresa, y una empresa puede tener varias cuentas. Las cuentas de administrador no pertenecen a ninguna empresa.
- El identificador de acceso es el **RUT de acceso**: único, normalizado y validado con su dígito verificador. Por defecto es el RUT de la persona; el sistema también admite el RUT de la empresa si así se definió en la sección 0.
- El RUT nunca es contraseña ni factor de autenticación; solo identifica la cuenta.
- No existe registro público. Las cuentas las crea el administrador.

## 5. Arquitectura y stack

- **Monolito modular en Django.** Usa la versión estable con soporte vigente más reciente (mínimo 5.2 LTS) y Python 3.12 o superior. Verifica las versiones soportadas en la documentación oficial antes de fijarlas.
- **Interfaz renderizada en el servidor** con plantillas de Django. HTMX para interacciones parciales (filtros, subida con progreso, cambios de estado) y JavaScript mínimo, sin frameworks SPA. Usa `<dialog>` y `<details>` nativos para modales y menús.
- **CSS con Tailwind**, compilado en el build con su CLI standalone, sobre los tokens de la sección 9. Sin CDN en producción.
- **PostgreSQL 16 o superior**: administrado en producción y en Docker en desarrollo.
- **Archivos en almacenamiento privado compatible con S3** en producción (por ejemplo, con `django-storages`). En desarrollo, sistema de archivos local fuera de cualquier ruta pública. El código de descarga es el mismo en ambos casos.
- **Correo** por SMTP o API de un proveedor transaccional, configurado por variables de entorno; backend de consola en desarrollo.
- **Estáticos** con WhiteNoise, servidor Gunicorn e imagen Docker.
- **Caché en base de datos** de Django para bloqueos y límites de intentos. Sin Redis, Celery, colas, microservicios ni API pública en el MVP.
- HTMX, fuentes e íconos se sirven como archivos estáticos propios, sin CDN externos.

Organización sugerida en apps:

| App | Responsabilidad |
| --- | --- |
| `core` | Configuración, utilidades de RUT, validadores, plantillas base, componentes, páginas de error y `/salud/` |
| `cuentas` | Modelo de usuario, acceso, activación, recuperación y 2FA |
| `empresas` | Empresas y carpetas |
| `documentos` | Documentos, versiones, almacenamiento y descargas |
| `portal` | Vistas del cliente |
| `panel` | Vistas del administrador |
| `sitio` | Páginas públicas, servicios y datos del negocio |
| `solicitudes` | Consultas, cotizaciones y notificaciones |
| `auditoria` | Registro de eventos |

Principios de código:

- La lógica de negocio vive en funciones de servicio (por ejemplo, `documentos/services.py`), no en vistas ni plantillas.
- Toda consulta de datos de clientes pasa por QuerySets centralizados, como `Documento.objects.visibles_para(usuario)`. Nunca uses `get(pk=…)` sin filtrar por empresa.
- Las vistas del portal y del panel heredan de mixins de rol únicos y probados.
- La configuración se separa por entorno (`base`, `dev`, `test`, `prod`), se lee de variables de entorno y se documenta en `.env.example`.

## 6. Modelo de datos

Usa UUID como identificador en las URL de empresas, carpetas, documentos y versiones; nunca IDs secuenciales. Todos los modelos llevan `creado_en` y `actualizado_en`. Agrega índices para los filtros frecuentes.

| Entidad | Campos principales | Reglas |
| --- | --- | --- |
| Usuario | RUT de acceso, nombre, email, rol (administrador o cliente), empresa, activo, último acceso | Modelo personalizado, definido antes de la primera migración. Un cliente siempre tiene empresa; un administrador nunca. Se crea sin contraseña utilizable hasta que se activa |
| Empresa | UUID, RUT, razón social, nombre de fantasía, contacto (nombre, email, teléfono), activa, notas internas | RUT único y validado; las notas internas nunca se muestran al cliente |
| Carpeta | UUID, empresa, nombre, orden, descripción | Nombre único dentro de la empresa |
| Documento | UUID, empresa, carpeta, título, descripción, versión vigente, eliminado en, eliminado por | La carpeta pertenece a la misma empresa; "eliminado en" marca la papelera |
| VersionDocumento | UUID, documento, número, clave de almacenamiento, nombre original saneado, tipo MIME detectado, extensión, tamaño, SHA-256, subido por, subido en | Las versiones no se editan; solo se agregan |
| Servicio | Nombre, slug, resumen, descripción, orden, activo | Se edita desde el panel |
| DatosNegocio | Nombre comercial, presentación, teléfono, email público, WhatsApp, comuna o región, horario, texto de la política de privacidad | Registro único, editable desde el panel |
| Solicitud | UUID, tipo (consulta o cotización), nombre, email, teléfono, empresa, servicio, rango de trabajadores, comuna, mensaje, consentimiento y su fecha, estado, notas internas, estado de notificación, error, intentos, notificada en | No guarda la IP del visitante |
| EventoAuditoria | Fecha, actor, RUT intentado, acción, empresa, tipo y UUID del objeto, IP, detalle breve | Solo se agregan; nunca se editan ni se borran desde la aplicación |

A esto se suman las tablas de la librería de 2FA y las de sesiones de Django.

## 7. Requisitos funcionales

Cada requisito tiene un código. Mantén en `docs/TRAZABILIDAD.md` la relación entre cada código, los archivos que lo implementan y la prueba que lo verifica.

### 7.1 Sitio público (PUB)

- **PUB-01** Páginas: Inicio, Servicios, Contacto, Solicitar cotización, Acceso clientes, Política de privacidad, y páginas 404 y 500 propias.
- **PUB-02** Inicio: propuesta de valor y presentación del profesional (desde DatosNegocio), resumen de servicios activos con enlace, llamada a "Solicitar cotización" y datos de contacto.
- **PUB-03** Servicios: listado de servicios activos en su orden. Cada uno tiene un botón "Solicitar cotización" que abre el formulario con ese servicio preseleccionado (`?servicio=<slug>`).
- **PUB-04** Navegación: nombre o logo, Servicios, Contacto, botón "Solicitar cotización" y enlace "Acceso clientes". El pie muestra el contacto y el enlace a la política de privacidad.
- **PUB-05** Si un dato no existe, su sección no se muestra. Nada de lorem ipsum ni textos de relleno.
- **PUB-06** Comando `contenido_pendiente` que lista los marcadores [COMPLETAR] del contenido. El inicio del panel muestra el mismo aviso.
- **PUB-07** SEO básico: `title` y `meta description` por página, Open Graph, `sitemap.xml` y `robots.txt`. Portal, panel, activación y recuperación llevan `noindex` y no aparecen en el sitemap.
- **PUB-08** Sin fotos de stock genéricas. Solo imágenes entregadas por el responsable; si no hay, el diseño funciona sin ellas.

### 7.2 Formularios y solicitudes (SOL)

- **SOL-01** Consulta: nombre*, email*, teléfono, mensaje* (máximo 2.000 caracteres) y aceptación de la política de privacidad*.
- **SOL-02** Cotización: nombre*, email*, teléfono*, empresa, servicio de interés* (servicios activos más "Otro / no estoy seguro"), rango de trabajadores (1–10, 11–25, 26–100, más de 100), comuna o región, mensaje* y aceptación de la política*.
- **SOL-03** Validación en el servidor, además de la del navegador. Errores por campo, claros, conservando lo escrito.
- **SOL-04** Antispam sin servicios externos: campo trampa oculto, tiempo mínimo de llenado de 3 segundos y un máximo de 5 envíos por hora por IP (configurable). El spam se descarta sin explicar el motivo. Deja preparado, y desactivado, un punto de extensión para un captcha.
- **SOL-05** Orden de guardado: validar, guardar la solicitud, intentar notificar por correo y registrar el resultado (`enviada`, `fallida` con error resumido, o `no_configurada`). Un fallo de correo nunca pierde la solicitud ni muestra un error al visitante.
- **SOL-06** Tras guardar, redirige (POST/redirect/GET) a una confirmación que no menciona correos: "Recibimos su solicitud. Le responderemos al correo o teléfono indicado."
- **SOL-07** En el MVP no se envía correo automático al visitante. Así el formulario no puede usarse para enviar correos a terceros.
- **SOL-08** Correo al profesional: asunto con tipo y nombre, datos de la solicitud y enlace a su detalle en el panel. `Reply-To` es el email del visitante. Sin adjuntos.
- **SOL-09** Bandeja en el panel: filtros por tipo, estado y fechas; búsqueda por nombre, email o empresa; orden por fecha; paginación; estado de notificación visible.
- **SOL-10** Detalle: todos los datos con fecha y hora, cambio de estado (Nueva → En seguimiento → Cerrada, o Descartada), notas internas y botón "Reintentar notificación" si falló.
- **SOL-11** Comando `reintentar_notificaciones` para el cron del hosting, con un máximo de intentos configurable.

### 7.3 Autenticación y cuentas (AUT)

- **AUT-01** Un único formulario de acceso con RUT y contraseña. Acepta el RUT con o sin puntos y guion, y la K en mayúscula o minúscula; lo normaliza y valida el dígito verificador antes de consultar.
- **AUT-02** Ante credenciales inválidas, un mensaje genérico ("RUT o contraseña incorrectos") que no revela si el RUT existe, con tiempos de respuesta similares.
- **AUT-03** Redirección según rol: el cliente va al portal; el administrador pasa por la verificación 2FA y luego al panel.
- **AUT-04** Bloqueo temporal: 5 intentos fallidos en 15 minutos para una misma combinación de RUT e IP bloquean durante 15 minutos (configurable), además de un límite por IP. Mensaje genérico, evento en auditoría y desbloqueo manual desde el panel. La IP real se toma del encabezado del proxy de confianza configurado, nunca de cualquier `X-Forwarded-For`.
- **AUT-05** Contraseñas con hash Argon2id como hasher principal, mínimo 12 caracteres y validadores de Django (similitud, contraseñas comunes, solo números). Sin reglas de composición obligatorias ni expiración periódica.
- **AUT-06** Activación: al crear un usuario se genera un enlace de un solo uso, válido por 72 horas, para que defina su contraseña. El administrador puede enviarlo por correo o copiarlo para entregarlo por otro canal; si el correo no está configurado o falla, el panel lo informa. Nunca se envían contraseñas por correo y el administrador nunca las conoce.
- **AUT-07** Recuperación: el usuario ingresa su RUT. Si la cuenta existe, está activa y tiene email, recibe un enlace de un solo uso válido por 1 hora. La pantalla siempre muestra lo mismo y no afirma ningún envío: "Si los datos corresponden a una cuenta activa, enviaremos instrucciones al correo registrado." Los fallos de envío quedan en el log y en la auditoría.
- **AUT-08** Cambio de contraseña desde "Mi cuenta", pidiendo la actual. Al cambiarla o restablecerla se cierran las demás sesiones.
- **AUT-09** Sesiones con cookies `Secure`, `HttpOnly` y `SameSite=Lax`; expiran tras 60 minutos de inactividad (configurable). El identificador de sesión rota al iniciar sesión y el cierre de sesión es solo por POST.
- **AUT-10** 2FA obligatorio para administradores: TOTP con app de autenticación, enrolamiento en el primer acceso y códigos de recuperación de un solo uso. Un comando de gestión restablece el 2FA de un administrador y requiere acceso al servidor.
- **AUT-11** Desactivar un usuario o su empresa corta el acceso en la petición siguiente, incluidas las sesiones abiertas. Se valida en el backend de autenticación, en cada petición.
- **AUT-12** El primer administrador se crea con un comando de gestión.

### 7.4 Panel de administración (ADM)

- **ADM-01** Estructura: barra lateral con Inicio, Empresas, Solicitudes, Auditoría, Contenido del sitio y Mi cuenta. En móvil, la barra se convierte en menú.
- **ADM-02** Inicio del panel con datos reales: empresas activas, solicitudes nuevas, documentos subidos en los últimos 30 días, últimas solicitudes y avisos (notificaciones fallidas, contenido [COMPLETAR], cuentas pendientes de activación).
- **ADM-03** Empresas: listado con búsqueda por RUT o razón social, filtro por estado y paginación. Crear y editar con validación de RUT y unicidad. Desactivar y reactivar con confirmación. Sin borrado definitivo desde el panel.
- **ADM-04** Al crear una empresa, una opción marcada por defecto crea las carpetas base definidas en la configuración: Matrices de riesgos, Protocolos MINSAL, Reglamento interno, Formatos de inspección y Documentos preventivos.
- **ADM-05** Ficha de empresa con tres pestañas: Documentos, Usuarios y Actividad (auditoría filtrada por la empresa).
- **ADM-06** Usuarios de la empresa: crear (RUT, nombre, email), editar, desactivar y reactivar, generar enlace de activación o de restablecimiento, desbloquear, y ver estado (pendiente, activo, bloqueado, inactivo) y último acceso.
- **ADM-07** Carpetas: crear, renombrar, ordenar y eliminar solo cuando no tienen documentos, incluidos los de la papelera.
- **ADM-08** Documentos: subir uno o varios archivos con barra de progreso y resultado por archivo (aceptado, o rechazado con su motivo); editar título y descripción; mover a otra carpeta de la misma empresa; reemplazar el archivo (crea una versión nueva); ver el historial y descargar cualquier versión; eliminar con confirmación.
- **ADM-09** Papelera por empresa: los documentos eliminados se pueden restaurar durante 30 días. El comando `purgar_papelera` elimina de forma definitiva, en base de datos y almacenamiento, los que superan ese plazo.
- **ADM-10** Contenido del sitio: editar DatosNegocio y gestionar Servicios (crear, editar, ordenar, activar y desactivar).
- **ADM-11** Auditoría: listado de solo lectura, filtrable por empresa, usuario, acción y fechas.
- **ADM-12** El admin de Django queda solo para el superusuario técnico, en una ruta definida por variable de entorno y con 2FA. No es la interfaz de trabajo diario.

### 7.5 Gestión documental (DOC)

- **DOC-01** Formatos permitidos, en una lista blanca configurable: PDF, DOCX, XLSX, PPTX, JPG y PNG. Todo lo demás se rechaza, incluidos ejecutables, HTML, SVG, archivos con macros (DOCM, XLSM) y comprimidos.
- **DOC-02** Validación en el servidor de cada archivo: extensión permitida, tipo real según la firma de bytes y coherente con la extensión (en DOCX, XLSX y PPTX, estructura OOXML válida), tamaño máximo configurable (25 MB por defecto) y archivo no vacío. La subida pasa siempre por el servidor, nunca directo al bucket; la validación del navegador es solo una ayuda.
- **DOC-03** Almacenamiento privado con claves aleatorias sin datos identificables, por ejemplo `docs/<uuid_empresa>/<uuid_version>`. Ni nombres originales ni RUT en la ruta. Se registran el SHA-256 y el tamaño.
- **DOC-04** Ver y descargar pasa siempre por una vista de la aplicación que exige sesión; comprueba que el documento sea de la empresa del usuario (o que este sea administrador) y que no esté en la papelera; registra el evento de auditoría; y entrega el archivo. En producción redirige a una URL firmada válida por un máximo de 2 minutos, con `Content-Type` y `Content-Disposition` correctos; en desarrollo lo transmite directamente.
- **DOC-05** "Ver" abre una pestaña nueva con `Content-Disposition: inline` solo para PDF, JPG y PNG; el resto se descarga como `attachment`. El nombre descargado es el original saneado, con tildes y ñ bien codificadas (RFC 6266).
- **DOC-06** Un recurso inexistente o de otra empresa responde 404, no 403, para no revelar que existe.
- **DOC-07** Un documento solo puede estar en una carpeta de su propia empresa. Mover documentos entre empresas no está permitido.
- **DOC-08** Al reemplazar, la nueva versión pasa a ser la vigente. Las anteriores se conservan y solo las ve el administrador.
- **DOC-09** Listados paginados (25 por página) y sin consultas N+1.

### 7.6 Portal del cliente (CLI)

- **CLI-01** Inicio del portal: nombre de la empresa, carpetas con su cantidad de documentos y "Documentos recientes" (los 10 últimos subidos o reemplazados), con la etiqueta "Nuevo" si tienen menos de 14 días.
- **CLI-02** Vista de carpeta: título, tipo, tamaño y fecha de actualización de cada documento, con las acciones Ver (si aplica) y Descargar. Orden por fecha o nombre, y estado vacío claro.
- **CLI-03** Búsqueda por título dentro de los documentos de su empresa, con estado "sin resultados".
- **CLI-04** Mi cuenta: nombre, RUT y correo; cambio de contraseña; cierre de sesión.
- **CLI-05** El cliente no ve versiones anteriores, papelera, notas internas ni acciones de edición. El servidor rechaza cualquier petición de modificación, aunque se construya a mano.
- **CLI-06** Si la empresa aún no tiene documentos, se muestra un estado vacío con un texto neutro y el contacto del profesional.
- **CLI-07** Desde el inicio del portal se llega a cualquier documento en dos clics como máximo.

### 7.7 Auditoría (AUD)

- **AUD-01** Se registran: inicios de sesión exitosos y fallidos (con el RUT intentado), bloqueos, cierres de sesión, activaciones, restablecimientos y cambios de contraseña, eventos de 2FA, altas y cambios de empresas y usuarios; subida, reemplazo, movimiento, eliminación, restauración y purga de documentos; vistas y descargas; y cambios de estado de solicitudes.
- **AUD-02** Cada evento guarda fecha y hora, actor, acción, empresa, objeto e IP. Nunca contraseñas, tokens, enlaces de activación ni contenido de documentos.
- **AUD-03** La auditoría no se edita ni se borra desde la aplicación. Retención configurable (24 meses por defecto), con el comando `depurar_auditoria`.

## 8. Seguridad (SEG)

- **SEG-01** Producción: `DEBUG=False`; `SECRET_KEY` desde el entorno; `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` explícitos; HTTPS obligatorio, con `SECURE_PROXY_SSL_HEADER` según el hosting; HSTS, empezando con un valor bajo y subiéndolo al confirmar que todo funciona. `python manage.py check --deploy` debe terminar sin advertencias, o con cada excepción justificada en `docs/SEGURIDAD.md`.
- **SEG-02** Encabezados: Content-Security-Policy estricta (`script-src 'self'`, sin scripts ni estilos en línea), `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `X-Frame-Options: DENY` y una `Permissions-Policy` restrictiva. Usa el soporte nativo de CSP si tu versión de Django lo trae; si no, `django-csp`. Configura HTMX para que no inyecte estilos en línea.
- **SEG-03** CSRF activo en todos los formularios y peticiones HTMX, con el token enviado en un encabezado. Ningún endpoint queda exento.
- **SEG-04** Autorización: mixins de rol en todas las vistas privadas y QuerySets acotados por empresa (sección 5). Una prueba recorre automáticamente todas las URL del proyecto y verifica que solo las de una lista pública explícita respondan sin sesión.
- **SEG-05** UUID en las URL y respuesta 404 para recursos ajenos (DOC-06).
- **SEG-06** Plantillas con autoescape. Los textos editables (servicios, datos del negocio, política) se muestran escapados, con saltos de línea y sin HTML.
- **SEG-07** Archivos subidos: validación según DOC-01 y DOC-02, límite de tamaño también en el servidor web y el proxy, y nombres saneados. Nunca se ejecutan, interpretan ni sirven como estáticos desde el dominio de la aplicación.
- **SEG-08** Secretos solo en variables de entorno o en el gestor de secretos del hosting. `.env` en `.gitignore` y `.env.example` sin valores reales. Las credenciales del bucket tienen permisos mínimos: leer, escribir y borrar objetos de ese bucket, nada más.
- **SEG-09** Dependencias con versiones fijadas y `pip-audit` (o equivalente) en CI, sin vulnerabilidades altas abiertas.
- **SEG-10** Logs sin contraseñas, tokens, enlaces de activación ni contenido de documentos. Las trazas de error van al log del servidor, nunca al usuario.
- **SEG-11** Respaldos: base de datos administrada con respaldos diarios automáticos, retención de al menos 7 días y recuperación a un punto en el tiempo si el proveedor la ofrece. Bucket con versionado activado y expiración de versiones antiguas entre 30 y 90 días. Procedimiento de restauración documentado y probado antes de cargar documentos reales. Objetivos: pérdida máxima de datos de 24 horas (RPO) y recuperación en un día hábil (RTO).
- **SEG-12** Privacidad: política de privacidad publicada con el texto que entregue el responsable (no redactes texto legal definitivo); casilla de aceptación obligatoria en los formularios, con su fecha registrada; minimización de datos. Considera la normativa chilena de protección de datos personales (Ley 19.628 y su reforma por la Ley 21.719) y anota las decisiones legales como pendientes de asesoría.
- **SEG-13** La ruta del admin de Django no aparece en `robots.txt` ni en el sitemap; se protege con `noindex`, autenticación y 2FA.

## 9. Diseño visual y experiencia (UX)

**Principios.** Sobrio, claro y confiable. Manda el contenido: pocos elementos, bien alineados y con espacio. Toma como referencia la calma y la jerarquía de los buenos productos SaaS, sin copiar ninguno.

**Prohibido:** gradientes decorativos, glassmorphism, sombras pesadas, animaciones de entrada o parallax, carruseles, contadores animados, grillas de tarjetas para todo, íconos decorativos en cada línea, fotos de stock genéricas, testimonios o logos de clientes inventados, emojis en la interfaz y textos de relleno.

**Tokens de diseño.** Son un punto de partida, reemplazables por la marca real. Defínelos como variables CSS y en la configuración de Tailwind.

| Token | Valor | Uso |
| --- | --- | --- |
| Primario | #0F4C5C (hover #0C3D4A, fondo suave #EEF6F7) | Botones principales, enlaces y foco |
| Acento | #D97706 | Solo detalles, siempre con texto oscuro encima; nunca como color de texto sobre blanco |
| Texto principal | #0F172A | Cuerpo y títulos |
| Texto secundario | #64748B | Metadatos y ayudas |
| Bordes de campos | #64748B | Inputs y selects, con contraste de al menos 3:1 |
| Divisores | #E2E8F0 | Líneas decorativas |
| Superficies | #FFFFFF y #F8FAFC | Fondo y secciones alternas |
| Éxito, error, advertencia, info | #15803D, #B91C1C, #B45309, #1D4ED8 | Estados y alertas |

- **Tipografía:** IBM Plex Sans autoalojada (woff2, pesos 400, 500 y 600) con `system-ui` de respaldo. Base de 16 px, interlineado de 1,5 a 1,6, escala 14/16/18/20/24/30/36 y cifras tabulares en tablas.
- **Espacio y forma:** múltiplos de 4 px, radios de 6 a 8 px, una sola sombra sutil para elementos flotantes, contenido de hasta 1.140 px de ancho y líneas de texto de no más de 70 caracteres.
- **Íconos:** un solo set de línea (por ejemplo, Lucide) en SVG, solo donde ayudan a reconocer una acción o un tipo de archivo.

**Componentes reutilizables** (plantillas parciales): botón (primario, secundario, fantasma y peligro, con estados de carga y deshabilitado); campos con etiqueta, ayuda y error; alerta; diálogo de confirmación; tabla que en móvil pasa a lista; paginación; insignia de estado; migas de pan; estado vacío; zona de subida con progreso; barra lateral del panel; encabezado y pie públicos. Muéstralos todos en una página de referencia disponible solo en desarrollo.

**Estados obligatorios** en cada vista y formulario:

- Cargando: botón deshabilitado con indicador durante el envío, e indicador en las peticiones HTMX.
- Error: mensaje por campo y resumen arriba, anunciado con `aria-live`; los errores del servidor se explican en lenguaje humano.
- Éxito: confirmación clara después de cada acción.
- Vacío y sin resultados: un texto que explica qué pasa y qué se puede hacer.

**Accesibilidad**, con WCAG 2.2 AA como objetivo: HTML semántico, `lang="es-CL"`, enlace para saltar al contenido, foco visible, uso completo con teclado, etiquetas asociadas a los campos, información que no depende solo del color, áreas táctiles de 44 px en móvil, textos alternativos y respeto por `prefers-reduced-motion`.

**Responsive:** móvil primero; revisa en 360, 768 y 1280 px.

**Tono:** español de Chile, formal y cercano, con trato de "usted". Mensajes breves y botones con verbos ("Subir documentos", "Solicitar cotización").

## 10. Requisitos no funcionales (RNF)

- **RNF-01** Volumen de diseño según la sección 0.
- **RNF-02** Páginas del portal y del panel en menos de 500 ms en el servidor (p95) con ese volumen. Subidas de 25 MB sin cortes por tiempo de espera: ajusta los límites de Gunicorn y del proxy.
- **RNF-03** Navegadores: las dos últimas versiones de Chrome, Edge, Firefox y Safari, incluido Safari en iOS.
- **RNF-04** Calidad: `ruff` para lint y formato, tipado donde aporte claridad, y nada de código muerto ni comentarios TODO en lo entregado.
- **RNF-05** Observabilidad: logs estructurados a stdout; endpoint `/salud/` que no expone información interna; integración opcional con un servicio de errores, desactivada si no hay credenciales.
- **RNF-06** Sitio público con Lighthouse móvil de 90 o más en rendimiento, accesibilidad, buenas prácticas y SEO, medido en staging.

## 11. Plan de implementación por etapas

Al cerrar cada etapa: pruebas y linters en verde, migraciones incluidas, documentación al día, `docs/TRAZABILIDAD.md` actualizado y el reporte de la sección 15.

- **Etapa 0. Reconocimiento y plan.**
    - Construye: inspección del entorno (Python, Docker, git) y del repositorio; `docs/PLAN.md` con estructura, dependencias justificadas, supuestos, preguntas abiertas y cualquier desviación de esta especificación. Todavía sin código de la aplicación.
    - Terminada cuando: el responsable aprueba el plan.
- **Etapa 1. Base del proyecto.**
    - Construye: proyecto Django con configuración por entorno; modelo de usuario personalizado antes de la primera migración; Docker Compose (aplicación y PostgreSQL); Tailwind compilado; plantillas base (pública, portal y panel) con tokens y primeros componentes; página de referencia de componentes; páginas 404 y 500; `/salud/`; `ruff`, `pytest` y CI (lint, pruebas y `pip-audit`); README de instalación.
    - Terminada cuando: `docker compose up` levanta la aplicación desde cero, las migraciones corren en una base vacía y la CI está en verde.
- **Etapa 2. Cuentas y acceso** (AUT, ADM-12 y SEG-03).
    - Construye: utilidades de RUT, acceso, bloqueo, cierre de sesión, activación, recuperación, cambio de contraseña, 2FA de administradores, redirección por rol y corte inmediato al desactivar.
    - Terminada cuando: pasan las pruebas de RUT (válidos, inválidos, con y sin puntos, con K) y las de autenticación de la sección 12.2.
- **Etapa 3. Empresas, usuarios y carpetas** (ADM-01 a ADM-07, ADM-11 y sus eventos de auditoría).
    - Terminada cuando: un administrador crea una empresa con sus carpetas base y un usuario, y copia el enlace de activación; el usuario define su contraseña y entra a su portal vacío; pasan las pruebas de permisos del panel.
- **Etapa 4. Documentos** (DOC, ADM-08, ADM-09 y sus eventos de auditoría).
    - Construye: almacenamiento intercambiable (local y S3), subida validada, ver, descargar, reemplazar, mover, eliminar, restaurar y purgar.
    - Terminada cuando: todo funciona contra almacenamiento real, los archivos inválidos se rechazan con su motivo y pasan las pruebas de aislamiento entre empresas. El backend S3 se verifica contra un bucket de prueba real antes de producción; en las pruebas automáticas puede usarse un emulador, declarándolo.
- **Etapa 5. Portal del cliente** (CLI).
    - Terminada cuando: el flujo completo del cliente funciona en móvil y escritorio, y pasan las pruebas de acceso cruzado y de solo lectura.
- **Etapa 6. Sitio público y solicitudes** (PUB, SOL, ADM-10).
    - Terminada cuando: ambos formularios guardan; con el correo configurado, la notificación llega, y sin él la solicitud queda como `no_configurada` o `fallida`, sin perderse; el antispam está probado; todo el contenido sale de la base de datos y `contenido_pendiente` lista los marcadores.
- **Etapa 7. Endurecimiento y calidad.**
    - Construye: CSP y encabezados; revisión de accesibilidad (teclado, contraste, lector de pantalla básico); revisión responsive; rendimiento (consultas, índices, paginación); revisión de la suite de seguridad; `check --deploy`, `pip-audit` y Lighthouse.
    - Terminada cuando: todos los criterios de la sección 12 están verificados y registrados en `docs/TRAZABILIDAD.md`.
- **Etapa 8. Despliegue y operación.**
    - Construye: Dockerfile de producción; configuración para un PaaS, documentando requisitos sin atarse a un proveedor; base de datos y bucket administrados; dominio y HTTPS; correo con SPF, DKIM y DMARC; tareas programadas; respaldos y simulacro de restauración.
    - Terminada cuando: la aplicación corre en staging con HTTPS, `check --deploy` está limpio y la restauración está probada y documentada.

## 12. Pruebas y criterios de aceptación

### 12.1 Reglas generales

- Pruebas automáticas con `pytest-django`. Cada requisito con código tiene al menos una prueba, o una verificación manual documentada, en `docs/TRAZABILIDAD.md` (requisito → archivos → prueba → estado).
- Las pruebas verifican efectos reales: registros en la base de datos, archivos en el almacenamiento, eventos de auditoría y correos en `mail.outbox`. Un código 200 por sí solo no prueba nada.
- Datos de prueba con al menos dos empresas (A y B), un usuario por empresa y un administrador.
- Cobertura de al menos 85 % en `cuentas`, `empresas`, `documentos`, `portal`, `panel` y `solicitudes`. La cobertura no reemplaza las pruebas de 12.2.

### 12.2 Pruebas de seguridad obligatorias

1. Todas las URL privadas, descubiertas recorriendo el URLconf: un anónimo es redirigido al acceso o recibe 404; un cliente recibe 403 o 404 en las rutas del panel.
2. Un cliente de A no puede listar, ver, buscar ni descargar carpetas, documentos o versiones de B, ni siquiera con el UUID correcto: recibe 404 y no se registra descarga.
3. Un cliente no puede crear, editar, mover, reemplazar, eliminar ni restaurar documentos con peticiones POST hechas a mano: recibe 403 o 404, y nada cambia en la base de datos ni en el almacenamiento.
4. Un documento en la papelera no es accesible para el cliente.
5. Un usuario desactivado, o de una empresa desactivada, pierde el acceso en su petición siguiente.
6. El bloqueo se activa tras los intentos configurados, con mensaje genérico, y el administrador puede desbloquear.
7. Los mensajes de acceso y de recuperación son idénticos para un RUT existente y uno inexistente.
8. Los enlaces de activación y recuperación son de un solo uso, expiran y fallan si se alteran.
9. Un administrador sin 2FA verificado no entra al panel.
10. Se rechazan: un ejecutable renombrado como `.pdf`, un HTML renombrado como `.pdf`, un archivo vacío, uno sobre el límite, un SVG y un DOCM.
11. La clave de almacenamiento no contiene el nombre original ni el RUT. En staging, el objeto no es accesible sin firma (verificación manual documentada).
12. Un formulario sin token CSRF responde 403; el campo trampa y el límite por IP funcionan.
13. Con el backend de correo fallando, la solicitud se guarda, el visitante ve la confirmación neutra y el panel muestra "fallida".
14. Un servicio cuyo nombre contiene `<script>` se muestra escapado en el sitio y en el panel.

### 12.3 Escenarios de aceptación

- **E1.** Un visitante pide una cotización desde un servicio, que aparece preseleccionado, y ve la confirmación. El administrador ve la solicitud como "Nueva", con su estado de notificación.
- **E2.** El administrador crea una empresa con sus carpetas base y un usuario, y copia el enlace de activación. El usuario define su contraseña y ve su portal con el estado vacío.
- **E3.** El administrador sube tres archivos, uno inválido: se aceptan dos y el tercero se rechaza con su motivo. El cliente los ve en "Recientes" con la etiqueta "Nuevo", descarga uno y la auditoría registra la descarga.
- **E4.** El administrador reemplaza un documento: el cliente descarga la versión nueva y el administrador ve ambas en el historial.
- **E5.** El administrador elimina un documento y el cliente deja de verlo; lo restaura y el cliente vuelve a verlo.
- **E6.** El administrador desactiva una empresa, y su usuario, con la sesión abierta, pierde el acceso en su acción siguiente.
- **E7.** Un cliente restablece su contraseña con el enlace y su sesión anterior en otro dispositivo queda cerrada.
- **E8.** El formulario de cotización y el portal se pueden usar completos con teclado, sin errores de contraste.

## 13. Despliegue, respaldos y operación

- **Entornos:** desarrollo local, staging y producción. Staging usa solo datos ficticios.
- **Datos de demostración:** comando `cargar_demo` que crea dos empresas ficticias (por ejemplo, con los RUT 11.111.111-1 y 22.222.222-2), sus usuarios y PDF de ejemplo generados, todo marcado como DEMO. Se niega a ejecutarse en producción.
- **Variables de entorno** documentadas en `.env.example`: clave secreta, hosts permitidos, URL de la base de datos, bucket (nombre, endpoint, región, credenciales), correo (servidor, puerto, usuario, contraseña, remitente), destinatarios de notificaciones, ruta del admin de Django, minutos de inactividad de sesión, tamaño máximo de subida, proxy de confianza y credenciales opcionales del servicio de errores.
- **Correo:** remitente del dominio propio (no un Gmail personal), con SPF, DKIM y DMARC configurados.
- **Tareas programadas** en el cron del hosting: `reintentar_notificaciones` cada 15 minutos, `purgar_papelera` y `clearsessions` a diario, y `depurar_auditoria` una vez al mes.
- **Mantenimiento:** aplicar los parches de seguridad de Django y de las dependencias al menos una vez al mes; el procedimiento queda en `docs/DESPLIEGUE.md`.

## 14. Documentación a entregar

| Archivo | Contenido |
| --- | --- |
| `README.md` | Requisitos, instalación local, comandos, pruebas y estructura |
| `.env.example` | Todas las variables, sin valores reales |
| `docs/PLAN.md` | Plan de la Etapa 0, actualizado al avanzar |
| `docs/ARQUITECTURA.md` | Componentes, modelo de datos y flujo de descarga segura |
| `docs/DECISIONES.md` | Decisiones y dependencias, con su motivo |
| `docs/SEGURIDAD.md` | Amenazas principales, el control que mitiga cada una y las excepciones justificadas |
| `docs/TRAZABILIDAD.md` | Requisito → implementación → prueba → estado |
| `docs/DESPLIEGUE.md` | Despliegue, variables, tareas programadas, respaldos, restauración, rotación de secretos, alta de administradores, restablecimiento de 2FA y desbloqueo de usuarios |
| `docs/MANUAL_ADMIN.md` | Guía breve y no técnica para el profesional: empresas, usuarios, documentos y solicitudes |

## 15. Formato de tus reportes

Al cerrar cada etapa, entrega:

1. Qué implementaste, con los códigos de requisito.
2. Archivos creados o modificados, en resumen.
3. Cómo verificarlo: comandos exactos y pasos manuales.
4. Resultado real de pruebas y linters, resumido; nunca inventado.
5. Pendientes, limitaciones y riesgos conocidos, explícitos y sin minimizar.
6. Decisiones tomadas y supuestos nuevos.
7. Preguntas para el responsable, si las hay.

Nunca declares como completo algo simulado, sin pruebas o que no ejecutaste.

## 16. Fuera de alcance

No implementes: registro público, subida de archivos por clientes, precios o cotizaciones automáticas, pagos, blog, chat, varios idiomas, app móvil, API pública, roles de equipo con permisos parciales, usuarios con acceso a varias empresas, subcarpetas, vencimientos y alertas de documentos, avisos al cliente por documentos nuevos, antivirus, firma electrónica ni borrado definitivo de empresas desde el panel. Si alguno parece necesario, propónlo en tu reporte.
