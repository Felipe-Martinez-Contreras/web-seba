# Arquitectura

Componentes, modelo de datos y flujo de descarga segura. Describe lo construido hasta la Etapa 6; se completa con cada etapa. El porqué de cada decisión está en `DECISIONES.md` y los controles de seguridad, en `SEGURIDAD.md`.

## 1. Componentes

Una sola aplicación Django, renderizada en el servidor, con PostgreSQL y un almacenamiento privado de archivos.

| Pieza | Qué es | Dónde |
| --- | --- | --- |
| Aplicación | Django 6.1 sobre Python 3.13. Plantillas de Django, Tailwind compilado y JavaScript propio mínimo | Contenedor `web` |
| Base de datos | PostgreSQL 18. También guarda las sesiones y la caché (bloqueos y límites) | Contenedor `db` |
| Archivos | Local: carpeta `DOCUMENTOS_DIR`, fuera del código. S3: bucket privado | Volumen `documentos_datos` o bucket |
| Estáticos | CSS, fuentes, íconos y JavaScript propios, servidos por WhiteNoise. Sin CDN | Imagen de la aplicación |

Apps y su responsabilidad:

| App | Responsabilidad |
| --- | --- |
| `core` | RUT, IP de confianza, mixins de rol, correo, logs, componentes y `/salud/` |
| `cuentas` | Usuario, acceso, bloqueo, enlaces de un solo uso, recuperación y 2FA |
| `empresas` | Empresas (clientes) y carpetas |
| `documentos` | Documentos, versiones, validación de archivos, almacenamiento y papelera |
| `auditoria` | Eventos: solo se agregan |
| `panel` | Vistas del administrador |
| `portal` | Vistas del cliente |
| `sitio` | Páginas públicas, servicios, datos del negocio, fotografías y contenido pendiente |
| `solicitudes` | Formularios públicos, antispam y notificación al profesional |

Dependencias entre apps: `panel` y `portal` usan a las demás; `documentos` usa `empresas` y `auditoria`; `empresas` no conoce a `documentos` (llega a sus documentos solo por la relación inversa de la carpeta).

Reglas que sostienen el diseño:

- **La lógica vive en servicios** (`*/services.py`). Las vistas solo comprueban el acceso, llaman al servicio y arman la respuesta.
- **Toda vista privada hereda de un mixin de rol** (`core/mixins.py`). Sin sesión: redirección al acceso. Rol incorrecto: 404. Administrador sin 2FA: a la verificación.
- **Los datos de un cliente se buscan siempre acotados.** En el portal, con `visibles_para(usuario)` (sección 6). En el panel, dentro de la empresa de la URL (`panel/views/base.py`).
- **Cada operación deja su evento de auditoría** en la misma transacción.

## 2. Modelo de datos

```
Empresa 1 ── n Usuario (clientes)
Empresa 1 ── n Carpeta
Empresa 1 ── n Documento n ── 1 Carpeta
Documento 1 ── n VersionDocumento
Documento n ── 1 VersionDocumento (version_vigente)
EventoAuditoria n ── 1 Usuario (actor), n ── 1 Empresa
Usuario 1 ── n EnlaceAcceso
```

| Entidad | Clave en las URL | Reglas que aplica la base de datos |
| --- | --- | --- |
| `Empresa` | UUID (clave primaria) | RUT único y normalizado |
| `Usuario` | `uuid` (la clave primaria entera no sale de la aplicación) | RUT único; cliente con empresa y administrador sin ella |
| `Carpeta` | UUID | Nombre único por empresa, sin distinguir mayúsculas. `PROTECT` hacia la empresa |
| `Documento` | UUID | `PROTECT` hacia empresa y carpeta: una carpeta con documentos no se borra. `eliminado_en` marca la papelera |
| `VersionDocumento` | UUID | Número único por documento; clave con la forma `docs/<uuid>/<uuid>`; SHA-256 válido; tamaño mayor que cero |
| `EventoAuditoria` | — | Solo se agregan |

Lo que la base no puede expresar lo aplican los servicios y lo cubren las pruebas: que la carpeta de un documento sea de su misma empresa (`documentos.services.mover`) y que la versión vigente sea una versión de ese documento.

Las versiones no se editan ni se borran: `VersionDocumento.save()` rechaza cambios, y el único borrado es el de la purga de la papelera.

## 3. Subida de un archivo

1. El panel envía el archivo a `/panel/clientes/<empresa>/carpetas/<carpeta>/subir/`. Con JavaScript va un archivo por petición (`static/js/subida.js`, con `XMLHttpRequest` para tener progreso); sin JavaScript, el formulario completo.
2. Antes de leer el cuerpo, `documentos.subida.LimiteDePeticion` rechaza una petición que declare más bytes que el tope.
3. Django deja en memoria los archivos de hasta 2,5 MB y escribe los demás en un temporal en disco.
4. `documentos.validacion.validar` comprueba, en este orden: no vacío, tamaño, firma OLE2 (Office antiguo o con contraseña), extensión de la lista blanca, firma de bytes coherente con la extensión y, en Office, estructura OOXML sin macros. Calcula el SHA-256 por trozos.
5. `documentos.services.subir` genera el UUID de la versión, arma la clave `docs/<uuid_empresa>/<uuid_version>` y guarda el objeto.
6. En una transacción crea `Documento`, `VersionDocumento` y el evento de auditoría. Si la base falla, borra el objeto.

El nombre original, saneado, vive solo en la base de datos. En el almacenamiento no hay nombres, extensiones ni RUT.

## 4. Flujo de descarga segura

"Ver" y "Descargar" pasan siempre por una vista de la aplicación. Ningún archivo tiene una URL propia.

```
Navegador ── GET /portal/documentos/<uuid>/descargar/ ──► Aplicación
                                                           1. sesión, rol, cuenta y empresa activas
                                                           2. documento visible para el usuario; si no, 404
                                                           3. inline solo si es "Ver" y es PDF, JPG o PNG
                                                           4. evento de auditoría
                                                           5. entrega
   local ◄── 200, el archivo transmitido desde la aplicación
   S3    ◄── 302 a una URL firmada, válida 120 segundos ──► bucket privado
```

Rutas:

| Quién | Ruta | Qué versión |
| --- | --- | --- |
| Cliente | `/portal/documentos/<documento>/ver/` y `/descargar/` | Siempre la vigente |
| Administrador | `/panel/clientes/<empresa>/documentos/<documento>/versiones/<version>/ver/` y `/descargar/` | Cualquiera del historial |

Paso a paso (`documentos.services.entregar` y `documentos.almacenamiento.entregar`):

1. **Acceso.** El mixin de rol exige sesión. El backend de autenticación comprueba en cada petición que la cuenta y su empresa sigan activas.
2. **Búsqueda acotada.** El cliente solo encuentra documentos de su empresa que no estén en la papelera. Uno ajeno, eliminado o inexistente responde el mismo 404.
3. **Disposición.** `inline` solo si se pidió "Ver" y el archivo es PDF, JPG o PNG; en cualquier otro caso, `attachment`. El nombre es el original saneado, codificado según RFC 6266.
4. **Auditoría.** Se registra "visto" o "descargado" con actor, empresa, documento, versión e IP. Evento y entrega van en una transacción: sin evento no hay entrega.
5. **Entrega.** El mismo código para los dos almacenamientos:
    - **S3:** redirección a una URL firmada por `boto3` que vence a los 120 segundos como máximo. El tipo y la disposición van dentro de la firma.
    - **Local:** la aplicación transmite el archivo con `Content-Type`, `Content-Disposition`, `nosniff` y `Content-Security-Policy: sandbox`.

Toda respuesta de estas vistas lleva `Cache-Control: no-store`.

## 5. Papelera y purga

- Eliminar marca `eliminado_en`. El documento sale de `visibles_para` de inmediato y nadie puede descargarlo.
- Restaurar borra la marca, dentro de `PAPELERA_DIAS` (30).
- `purgar_papelera` borra primero los objetos y después las filas, y deja un evento por documento. Si falla a medias, la siguiente ejecución lo termina.
- Con el versionado del bucket activado, el borrado del objeto no es inmediato: ver `SEGURIDAD.md`.

## 6. Portal del cliente

Solo lectura: todas sus vistas admiten únicamente GET y heredan de `ClienteMixin`.

| Ruta | Qué muestra |
| --- | --- |
| `/portal/` | Saludo, tarjeta de la empresa, buscador, carpetas con su contador y fecha, y los 10 documentos más recientes |
| `/portal/carpetas/` | Las carpetas de la empresa |
| `/portal/carpetas/<carpeta>/` | Documentos de la carpeta, por fecha o por nombre (`?orden=`), de a 25 |
| `/portal/buscar/?q=` | Búsqueda por título, sin distinguir mayúsculas ni tildes, de a 25 |
| `/portal/documentos/<documento>/` | Ficha: datos y botones Descargar y Ver en pantalla |

- **Ninguna vista recibe la empresa.** Carpetas y documentos salen de `visibles_para(request.user)`; lo ajeno y lo que está en la papelera responden 404 como lo inexistente.
- **Consultas en los querysets:** `Carpeta.objects.con_resumen()` (cantidad y última fecha, sin la papelera; la usa también el panel) y `Documento.objects.con_vigente()`, `recientes()` y `buscar()`.
- **Búsqueda sin tildes** con la extensión `unaccent` de PostgreSQL, creada por la migración `documentos/0002_unaccent`. El texto se recorta a 100 caracteres.
- **"Nuevo"** se calcula con la fecha de la versión vigente: 14 días desde la subida o el último reemplazo.
- **Dos clics (CLI-07):** las filas de carpeta y de búsqueda llevan Ver y Descargar, además del enlace a la ficha.

## 7. Sitio público

| Ruta | Qué muestra |
| --- | --- |
| `/` | Portada, servicios activos, bloque de contacto con el formulario de cotización y pie |
| `/servicios/` | Presentación y servicios activos, cada uno con su botón de cotización |
| `/contacto/` | Datos de contacto y formulario de consulta |
| `/cotizacion/` | Formulario de cotización; `?servicio=<slug>` lo preselecciona |
| `/solicitud-recibida/` | Confirmación, solo para quien acaba de enviar |
| `/privacidad/` | Política de privacidad |
| `/sitemap.xml`, `/robots.txt` | Páginas públicas con contenido; sin rutas privadas |

- **Todo el contenido sale de la base:** `DatosNegocio` (registro único) y `Servicio`. Se editan en Panel › Configuración › Contenido del sitio.
- **Una sola regla de contenido pendiente** (`sitio/pendientes.py`): lo vacío o con `[COMPLETAR]` no se muestra; lo de prueba se muestra. La usan las páginas, el panel y el comando `contenido_pendiente`.
- **`PaginaPublica`** (`sitio/paginas.py`) arma navegación, pie y SEO de cada página, como `core/navegacion.py` lo hace para el portal y el panel.
- **Sin política de privacidad no hay formularios.**
- **Fotografías:** archivos estáticos propios, descritos en `sitio/fotos.py` y registrados en `FOTOS.md`.

## 8. Recorrido de una solicitud

```
Visitante ── POST /contacto/ o /cotizacion/
   1. Token CSRF                     sin él: 403
   2. Validación del formulario      con errores: mismo formulario, con lo escrito
   3. Antispam                       descarte: mismo formulario y aviso neutro
   4. Guardar la solicitud           desde aquí no se pierde
   5. Redirección a la confirmación  "Recibimos su solicitud..."
        └─ en un hilo, unos segundos después:
   6. Notificar al profesional       enviada · fallida · correo no configurado
```

- El visitante ve lo mismo pase lo que pase en el paso 6. El resultado se ve en el panel.
- `reintentar_notificaciones` (cron, cada 15 minutos) vuelve a intentar las fallidas, hasta `NOTIFICACIONES_INTENTOS_MAXIMOS`, y envía las que quedaron sin intentar.
- El correo va solo a `NOTIFICACIONES_DESTINATARIOS`, con `Reply-To` del visitante. El visitante no recibe ningún correo automático.
- La solicitud no guarda la IP. El seguimiento (Pendiente, En proceso, Resuelta, Descartada) y las notas internas se llevan en el panel; cada cambio de estado deja un evento de auditoría.
