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
| DEC-21 | 09-10-2026 | HTMX 2.0.10 y no 4.0.0 | La 4.0.0 salió el 28-08-2026 y no se pudo confirmar que conserve los eventos de progreso de subida que necesita ADM-08. Reevaluada y cerrada en DEC-95 |
| DEC-22 | 09-10-2026 | Gunicorn se agrega en la Etapa 8, con la imagen de producción | En la Etapa 1 no se usa. `django-otp` y `segno` entraron en la Etapa 2; `django-storages`, en la 4 |
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
| DEC-36 | 09-10-2026 | Ajuste visual previo a la Etapa 2: tokens azul marino de la sección 9 y estilo del mockup `docs/diseno/mockup-referencia.jpg` | Cambio pedido por el responsable. Del mockup se toma el estilo, no los textos ni los datos (`docs/DISENO.md`) |
| DEC-37 | 09-10-2026 | Inter reemplaza a IBM Plex Sans, desde `@fontsource/inter` 5.3.0: subconjunto *latin*, pesos 400, 500, 600 y 700 | Lo pide la sección 9. El subconjunto cubre el español y cada archivo pesa unos 24 KB, frente a más de 60 KB de los archivos completos (RNF-06) |
| DEC-38 | 09-10-2026 | Fondo suave de advertencia `#FDF3E3` | La sección 9 da el color de advertencia pero no su fondo suave; se eligió uno con contraste 4,5:1 o más, comprobado por prueba |
| DEC-39 | 09-10-2026 | Una prueba automática verifica el contraste AA de los pares de tokens (`core/tests/test_diseno.py`) | Si un token deja de cumplir, la prueba falla en vez de pasar inadvertido. Con los tokens actuales todos cumplen; el más justo es Resuelta (`#15803D` sobre `#E8F6EE`) |
| DEC-40 | 09-10-2026 | En la portada, el botón principal es blanco con texto azul marino (`inverso`) y el secundario lleva borde blanco (`contorno-claro`) | Sobre fondo o velo azul marino, un botón azul marino lleno no se distingue |
| DEC-41 | 09-10-2026 | La portada usa fondo azul marino liso; acepta una imagen opcional con velo | Las fotografías se eligen en la Etapa 6 y se registran en `docs/FOTOS.md` (PUB-08) |
| DEC-42 | 09-10-2026 | El encabezado público es una franja azul marino continua con la portada, no un bloque superpuesto con posición absoluta | Mismo resultado visual sin fotografía; se revisa en la Etapa 6 al incorporar la foto |
| DEC-43 | 09-10-2026 | Portal y panel comparten `base_aplicacion.html`, `barra_lateral.html` y `barra_superior.html` | El mockup usa la misma estructura en ambos; el menú y el usuario llegan por el contexto de cada vista |
| DEC-44 | 09-10-2026 | La tabla es un patrón de marcado con la clase `tabla` y `data-etiqueta` en cada celda, no una plantilla parcial | Las columnas cambian en cada pantalla; el paso a lista en móvil se resuelve solo con CSS |
| DEC-45 | 09-10-2026 | Las pestañas son enlaces con `aria-current`, sin JavaScript | Cada pestaña es una URL propia: funciona con historial, marcadores y sin scripts |
| DEC-46 | 09-10-2026 | Insignias con tonos genéricos: Pendiente = `error`, En proceso = `info`, Resuelta = `exito`, Descartada o inactivo = `neutro` | Los mismos cinco tonos sirven para solicitudes, usuarios y empresas |
| DEC-47 | 09-10-2026 | Los componentes hoja (botón, ícono, insignia) se incluyen con `only` | No heredan variables del contexto de la pantalla, como `nombre` o `tipo` |
| DEC-48 | 09-10-2026 | Marca provisional: ícono `shield-check` de Lucide y nombre comercial en texto | `DISENO.md`, diferencia 10. Sin nombre comercial no se muestra nada; el logo sigue [COMPLETAR] |
| DEC-49 | 09-10-2026 | Se postergan la zona de subida con progreso (Etapa 4) y la pantalla de acceso (Etapa 2) | Dependen de pantallas y endpoints futuros. El campo de contraseña con botón para mostrarla ya está listo |
| DEC-50 | 09-10-2026 | Cambios de modelo que pide la especificación actualizada, para la Etapa 6: ícono en `Servicio`; titular, bajada y redes sociales en `DatosNegocio`; estados Pendiente, En proceso, Resuelta y Descartada en `Solicitud` | Esos modelos aún no existen; se crean ya con la forma nueva |
| DEC-51 | 09-10-2026 | "Clientes" es el nombre visible de las empresas en el panel; el modelo sigue siendo `Empresa` | ADM-01 actualizado |
| DEC-52 | 09-10-2026 | `Usuario.uuid`, único, para las URL y la auditoría; el ID entero sigue como clave primaria | Sección 6: nunca IDs secuenciales en las URL. Pedido por el responsable. Migración en tres pasos para poblar las filas existentes |
| DEC-53 | 09-10-2026 | Las apps `auditoria`, `portal` y `panel` se crean en la Etapa 2, en versión mínima (ajusta DEC-10) | AUT-04 y AUT-07 exigen eventos de auditoría; AUT-03 necesita un destino real por rol. Aprobada por el responsable |
| DEC-54 | 09-10-2026 | Enlaces de activación y restablecimiento como filas de `EnlaceAcceso`, con el token guardado como SHA-256 | Un solo uso real, vencimientos distintos, revocación y estado visible. La URL no identifica al usuario. Se descartó el generador de tokens de Django. Aprobada por el responsable |
| DEC-55 | 09-10-2026 | La configuración SMTP por variables de entorno (`CORREO_*`) se adelanta a la Etapa 2 | La recuperación la necesita. Sin `CORREO_HOST` el envío se informa como no configurado. Aprobada por el responsable |
| DEC-56 | 09-10-2026 | Desbloqueo manual como servicio, vista POST del panel y comando; el botón llega en la Etapa 3 | Aún no existe la lista de usuarios donde ponerlo. Aprobada por el responsable |
| DEC-57 | 09-10-2026 | El bloqueo tiene un mensaje propio: "Demasiados intentos. Espere unos minutos e intente nuevamente." | No revela nada: se aplica igual a un RUT sin cuenta. Aprobada por el responsable |
| DEC-58 | 09-10-2026 | La pantalla de acceso lleva un bloque azul marino liso al pie; la fotografía entra en la Etapa 6 | PUB-08 y DEC-41. Aprobada por el responsable |
| DEC-59 | 09-10-2026 | Backend de autenticación propio: una sola verificación Argon2 por intento, también cuando la cuenta no existe, está inactiva, no se ha activado o hay un bloqueo | AUT-02: el tiempo de respuesta no depende del motivo del rechazo |
| DEC-60 | 09-10-2026 | La IP del cliente se toma del encabezado del proxy solo si la conexión viene de `PROXY_CONFIANZA_REDES`, de derecha a izquierda. Producción exige declarar la variable | AUT-04. Declararla siempre evita que quede olvidada detrás de un proxy |
| DEC-61 | 09-10-2026 | Contadores con ventana fija desde el primer fallo y "generación" por RUT en las claves de la caché | Desbloquear un RUT anula sus bloqueos desde cualquier IP sin tener que enumerarlas |
| DEC-62 | 09-10-2026 | El 2FA solo se enrola en la sesión que acaba de usar un enlace de activación o de restablecimiento, durante 30 minutos. `restablecer_2fa` genera ese enlace | Pedido por el responsable: conocer la contraseña de un administrador sin 2FA no debe bastar para registrar un dispositivo propio |
| DEC-63 | 09-10-2026 | Al usar un enlace, la persona queda con la sesión iniciada | Poseer el enlace prueba más que la contraseña recién escrita, y permite ligar el enrolamiento del 2FA a esa sesión |
| DEC-64 | 09-10-2026 | El correo de recuperación se envía en un hilo del mismo proceso, que parte entre 2 y 4 segundos después de la petición y cierra su conexión a la base. En las pruebas es síncrono | Sin colas (sección 5). Si partiera de inmediato competiría por CPU con la petición: medido, 27,7 ms contra 16,8 ms. Limitación documentada en `SEGURIDAD.md` |
| DEC-65 | 09-10-2026 | `EnlaceAcceso.envio` nace como "pendiente" y pasa a "enviada", "fallida" o "no configurada" | Si el proceso se reinicia en medio del envío, el registro nunca dice "enviada" |
| DEC-66 | 09-10-2026 | Los enlaces se arman con `SITIO_URL`, obligatoria y con https en producción | No se confía en el encabezado `Host` para un enlace que da acceso a una cuenta |
| DEC-67 | 09-10-2026 | "Mi cuenta" muestra nombre, RUT y correo sin permitir editarlos | Pedido por el responsable: el correo es por donde llega la recuperación; lo cambia solo un administrador |
| DEC-68 | 09-10-2026 | Cinco fallos seguidos con la contraseña actual en "Cambiar contraseña" cierran la sesión | Una sesión robada no debe servir para adivinar la contraseña |
| DEC-69 | 09-10-2026 | Admin de Django con un sitio propio: sin formulario de acceso propio, con 2FA, en la ruta de `DJANGO_ADMIN_RUTA` y sin alta, borrado ni edición de contraseñas de usuarios | ADM-12. Usa el acceso de la aplicación, con su bloqueo y su auditoría. Sin la variable, no se publica |
| DEC-70 | 09-10-2026 | `EventoAuditoria` no lleva `actualizado_en`; el RUT intentado solo se guarda si es un RUT válido | La fila nunca cambia. En el campo del RUT alguien puede escribir su contraseña por error |
| DEC-71 | 09-10-2026 | El formateador de logs oculta el token en las rutas `/activar/…` y `/restablecer/…` | SEG-10: el servidor registra la ruta de cada petición |
| DEC-72 | 09-10-2026 | En el acceso, un RUT con dígito verificador incorrecto recibe el mensaje genérico; en la recuperación, un error de formato | En el acceso toda falla responde igual. En la recuperación el error no depende de ninguna cuenta y ayuda a quien se equivocó al escribir |
| DEC-73 | 09-10-2026 | `crear_administrador` no pide contraseña: imprime un enlace de activación. Con `--tecnico` crea el superusuario técnico | AUT-06 y AUT-12: nadie conoce la contraseña de otro. Imprimir el enlace en la consola de quien ejecuta el comando no es escribirlo en un log |
| DEC-74 | 09-10-2026 | El código QR del 2FA es un SVG incrustado, generado por `segno` y marcado como seguro | Excepción a R5 justificada en `SEGURIDAD.md`: el SVG no contiene datos de formularios |
| DEC-75 | 09-10-2026 | Rol incorrecto en una vista privada: 404. Administrador sin 2FA verificado: redirección a la verificación | No se confirma que la dirección exista (misma idea que DOC-06) |
| DEC-76 | 09-10-2026 | Sesiones con `SESSION_SAVE_EVERY_REQUEST` y `SESSION_EXPIRE_AT_BROWSER_CLOSE` | AUT-09: el plazo cuenta desde el último uso y no hay sesión persistente (sin "Recordarme") |
| DEC-77 | 09-10-2026 | En la verificación, el formato del código decide el dispositivo: 6 dígitos es TOTP; otro, código de recuperación | Un código de recuperación no suma fallos, ni espera, al TOTP |
| DEC-78 | 09-10-2026 | La pantalla de acceso no se replica en la página de referencia de componentes | Existe la pantalla real en `/acceso/`; duplicarla sería mantener dos copias |
| DEC-79 | 11-10-2026 | El inicio del panel muestra solo lo que existe: clientes activos, cuentas pendientes de activación y clientes recientes. El menú no lista Solicitudes ni Contenido del sitio | R1 y R2: los indicadores de solicitudes y de documentos entran con sus modelos (Etapas 4 y 6). Aprobada por el responsable con el plan de la Etapa 3 |
| DEC-80 | 11-10-2026 | El enlace de activación se muestra una sola vez, en la respuesta del POST que lo genera, y no se guarda en la sesión ni en la base | El token solo existe en memoria (DEC-54). Guardarlo para sobrevivir a una redirección lo dejaría en claro en la tabla de sesiones. Recargar la página genera otro enlace y revoca el anterior |
| DEC-81 | 11-10-2026 | El correo con el enlace que genera el administrador se envía dentro de la petición, con 10 segundos de espera máxima | AUT-06: el panel debe informar si falló. A diferencia de la recuperación (DEC-64), aquí no hay nada que ocultar con el tiempo de respuesta |
| DEC-82 | 11-10-2026 | "Generar enlace" decide el tipo en el servidor: activación (72 h) si la cuenta nunca definió su contraseña; restablecimiento (1 h) si ya lo hizo | El administrador no tiene que elegir, y no puede dar 72 horas a un enlace de restablecimiento |
| DEC-83 | 11-10-2026 | El RUT de un usuario solo se puede corregir mientras la cuenta está pendiente | Una vez activada, el RUT es su identificador de acceso y el que aparece en la auditoría. Para cambiarlo después: desactivar la cuenta y crear otra |
| DEC-84 | 11-10-2026 | Estados de usuario, en orden de precedencia: Inactivo (neutro), Bloqueado (error), Pendiente (advertencia), Activo (éxito). Se calculan en `cuentas/estados.py` | Ajusta DEC-46: el rojo de "Pendiente" es de las solicitudes; en usuarios el rojo queda para el bloqueo. El estado siempre lleva texto. Aprobada por el responsable |
| DEC-85 | 11-10-2026 | El desbloqueo pasa a `/panel/clientes/<empresa>/usuarios/<usuario>/desbloquear/` y solo alcanza a usuarios de esa empresa. A un administrador se le desbloquea con el comando `desbloquear_acceso` | Todo lo de un cliente cuelga de su UUID y se busca dentro de él. Cierra DEC-56. Aprobada por el responsable: para los administradores basta con el comando |
| DEC-86 | 11-10-2026 | `Carpeta` usa UUID como clave primaria, `PROTECT` hacia la empresa y nombre único por empresa sin distinguir mayúsculas, como restricción de la base | Sección 6. La restricción vale aunque se salte el formulario |
| DEC-87 | 11-10-2026 | Las carpetas se ordenan con botones "subir" y "bajar", cada uno un POST | Funciona con teclado y sin JavaScript; arrastrar exigiría una librería o código propio |
| DEC-88 | 11-10-2026 | "Eliminar carpeta solo si no tiene documentos" (ADM-07) se completa en la Etapa 4 | `Documento` aún no existe: hoy toda carpeta está vacía. En la Etapa 4 la relación será `PROTECT` y el servicio lo comprobará, papelera incluida. Completada en DEC-107 |
| DEC-89 | 11-10-2026 | Desactivar una cuenta revoca sus enlaces sin usar | Un enlace entregado antes no debe revivir al reactivar la cuenta |
| DEC-90 | 11-10-2026 | La retención borra eventos con `EventoAuditoria.objects.depurar()`, que solo usa el comando `depurar_auditoria`, y deja un evento "Depuración de la auditoría". Los meses son de calendario | AUD-03: único borrado permitido, con acceso al servidor y con su propio rastro |
| DEC-91 | 11-10-2026 | Un filtro inválido en la auditoría no muestra ningún evento | Mostrar todo sugeriría que el filtro se aplicó |
| DEC-92 | 11-10-2026 | Las tablas con muchas columnas (usuarios y eventos) siguen como lista hasta los 1.280 px | Entre 768 y 1.279 px el contenido mide unos 720 px: la tabla de usuarios desbordaba 24 px a 768 px. Detectado en la revisión visual |
| DEC-93 | 11-10-2026 | "Configuración" es un grupo de la barra lateral, sin enlace propio, con "Mi cuenta" dentro | ADM-01. "Contenido del sitio" se suma al grupo en la Etapa 6 |
| DEC-94 | 11-10-2026 | La revisión visual de pantallas privadas se hace contra una base de datos temporal, que se borra al terminar | Los datos de muestra y sus eventos de auditoría no quedan en la base de desarrollo |
| DEC-95 | 11-10-2026 | HTMX se queda en 2.0.10. La subida con progreso no usa HTMX: `static/js/subida.js` envía con `XMLHttpRequest` y `upload.onprogress` | Cierra DEC-21. htmx 4 usa `fetch()` y elimina `htmx:xhr:progress` sin reemplazo; su propia documentación recomienda `XMLHttpRequest` para un progreso confiable (verificado el 11-10-2026 en `four.htmx.org`, aún "en construcción"). Así una migración futura a la 4 no depende de la subida. Aprobada por el responsable |
| DEC-96 | 11-10-2026 | Almacenamiento con una interfaz propia (`documentos/almacenamiento.py`) y dos implementaciones: local y S3 sobre `boto3`. Sin `django-storages` | `django-storages` sigue en 1.14.6 (abril 2025) y no declara soporte para Django 6.1. Solo se necesitan guardar, abrir, borrar, existe, listar y URL firmada. Aprobada por el responsable |
| DEC-97 | 11-10-2026 | `moto` como emulador de S3: dentro del proceso en las pruebas y, opcional, como servidor en el perfil `s3` de Compose. Se instala `moto[s3]` más `flask` y `flask-cors`, no el extra `server` | Sin contenedor permanente ni imagen nueva en un equipo con poca memoria. El extra `server` arrastra más de diez paquetes que el servidor de S3 no usa. Aprobada por el responsable; el cambio de extra es una diferencia con el plan |
| DEC-98 | 11-10-2026 | Un documento en la papelera no lo descarga nadie, tampoco un administrador: primero se restaura | Lectura literal de DOC-04; la opción más simple y segura. Aprobada por el responsable |
| DEC-99 | 11-10-2026 | Los endpoints de ver y descargar del cliente (`/portal/documentos/<uuid>/…`) se construyen en la Etapa 4, sin pantallas que los enlacen | DOC-04 es de esta etapa y las pruebas 2 y 4 los necesitan. Las pantallas son de la Etapa 5. Aprobada por el responsable |
| DEC-100 | 11-10-2026 | Clave de almacenamiento `docs/<uuid_empresa>/<uuid_version>`, sin extensión. La forma la exigen el almacenamiento y una `CheckConstraint` de la base | DOC-03. La base rechaza una clave con nombre o RUT aunque se salte el servicio |
| DEC-101 | 11-10-2026 | `VersionDocumento` no lleva `actualizado_en` y rechaza editar y borrar; solo la borra la purga | Sección 6: las versiones solo se agregan. Mismo criterio que `EventoAuditoria` (DEC-70) |
| DEC-102 | 11-10-2026 | Orden de la validación: vacío, tamaño, firma OLE2, extensión, firma de bytes y estructura OOXML. La firma se exige en el byte 0 | Un `.doc`, `.xls` o `.ppt`, o un `.docx` con contraseña, recibe un motivo que dice qué hacer en vez de "formato no permitido" (pedido por el responsable) |
| DEC-103 | 11-10-2026 | La entrega local responde con `Content-Security-Policy: sandbox` y `nosniff`, sin relajar la CSP de la aplicación | Pedido por el responsable: un PDF o una imagen nunca ejecuta nada en el dominio de la aplicación. El visor de PDF de Edge funciona con `sandbox` (comprobado el 11-10-2026) |
| DEC-104 | 11-10-2026 | La subida envía un archivo por petición, en secuencia. Sin JavaScript, el formulario completo, con un tope por petición de 4 archivos del tamaño máximo, aplicado antes de leer el cuerpo | Progreso y resultado por archivo (ADM-08) y un solo archivo en tránsito a la vez. El tope responde con la página 400 propia |
| DEC-105 | 11-10-2026 | Un archivo aceptado queda publicado de inmediato; su título inicial es el nombre del archivo sin la extensión | La especificación no define borradores ni estados de publicación. La pantalla lo dice antes de subir. Aprobada por el responsable, con la protección de DEC-114 |
| DEC-106 | 11-10-2026 | Auditoría de documentos: el detalle lleva el título y la versión; "Ver" de un formato que no se abre en el navegador se registra como descarga; la purga no tiene actor | El evento dice lo que ocurrió y sigue siendo legible cuando el documento ya no existe |
| DEC-107 | 11-10-2026 | Una carpeta con documentos no se elimina: `PROTECT` en la base, comprobación en el servicio con la fila bloqueada, y el botón solo en carpetas vacías. Cuentan los de la papelera | ADM-07. Cierra DEC-88 |
| DEC-108 | 11-10-2026 | Restaurar se rechaza pasados los `PAPELERA_DIAS`, aunque `purgar_papelera` todavía no haya corrido | ADM-09: el plazo es de 30 días, no "hasta la próxima limpieza" |
| DEC-109 | 11-10-2026 | Producción exige declarar `DOCUMENTOS_ALMACENAMIENTO`. `manage.py check` falla con una carpeta de documentos dentro de una ruta de estáticos, con `s3` sin bucket o credenciales, o con un formato que la validación no sabe comprobar | SEG-07: no se cae al disco local por omisión ni se publica una carpeta por descuido |
| DEC-110 | 11-10-2026 | Comando `comprobar_almacenamiento`: guarda, lee, lista, descarga por URL firmada, comprueba que sin firma responda 403 y borra. Con `--firma`, además, que una firma alterada y una URL vencida se rechacen | Sección 11: el S3 real se verifica antes de producción. El emulador no valida firmas ni vencimientos, así que esa parte solo se prueba contra el bucket real |
| DEC-111 | 11-10-2026 | El indicador "Documentos subidos en los últimos 30 días" cuenta archivos subidos o reemplazados, sin los de la papelera | ADM-02 no lo precisa; un reemplazo también es un documento que el cliente recibe |
| DEC-112 | 11-10-2026 | Al reemplazar, el archivo nuevo puede ser de otro formato permitido; el título no cambia | Un Word puede pasar a PDF. El nombre del archivo queda en cada versión |
| DEC-113 | 11-10-2026 | Tras subir, `subida.js` vuelve a pedir la página y cambia solo el bloque de la lista de documentos | Detectado en la revisión en el navegador: la lista decía "sin documentos" junto a tres archivos aceptados |
| DEC-114 | 11-10-2026 | La zona de subida muestra destacado "Subiendo documentos para:" con la razón social y el RUT del cliente, y cada archivo aceptado dice "Publicado para" ese cliente | Pedido por el responsable al cierre de la Etapa 4: la publicación inmediata (DEC-105) queda aprobada, y el error más probable es subir un archivo al cliente equivocado |
| DEC-115 | 11-10-2026 | El reemplazo de un archivo usa el mismo `subida.js` de la subida: barra `<progress>`, resultado en una fila y recarga de la cabecera y del historial sin recargar la página. `data-refresca` admite varios bloques | Pedido por el responsable al cierre de la Etapa 4. Un solo script para subir y reemplazar; sin JavaScript sigue el formulario normal |
| DEC-116 | 11-10-2026 | El buscador del portal ignora tildes con la extensión `unaccent` de PostgreSQL (`django.contrib.postgres`, migración `documentos/0002_unaccent`) | Aprobada por el responsable: "inspeccion" debe encontrar "Inspección". Es parte de Django, sin dependencia nueva. En producción la base debe permitir crear la extensión (Etapa 8) |
| DEC-117 | 11-10-2026 | El texto de búsqueda se recorta a 100 caracteres, en el campo (`maxlength`) y en la vista | Pedido por el responsable. Un título admite 200, pero nadie busca con más de 100 |
| DEC-118 | 11-10-2026 | CLI-06 queda con un estado vacío de texto neutro, sin datos de contacto, hasta la Etapa 6 | Aprobada por el responsable: `DatosNegocio` no existe todavía y el contacto sigue [COMPLETAR] (R2). No se adelanta el modelo |
| DEC-119 | 11-10-2026 | "Sus carpetas" en vez de "Tus carpetas" | CLI-01 cita el texto del mockup, pero la sección 9 y `DISENO.md` (diferencia 12) piden trato de usted en todos los textos |
| DEC-120 | 11-10-2026 | Del mockup no se construyen el botón "Ver información" de la tarjeta de empresa ni el "Ver todos" de recientes; "Sus carpetas" sí lleva "Ver todas" | R1: no tienen destino en la especificación (no hay listado global de documentos, `DISENO.md` diferencia 3) |
| DEC-121 | 11-10-2026 | Las filas de carpeta y de búsqueda del portal llevan Ver y Descargar, además del título enlazado a la ficha (`fila_documento_acciones.html`) | CLI-02 y CLI-07: inicio → carpeta → archivo son dos clics. `fila_documento` es un solo enlace y no admite botones dentro |
| DEC-122 | 11-10-2026 | CLI-07 con paginación: un documento que queda en la página 2 de una carpeta de más de 25 se alcanza en dos clics por el buscador, no por la carpeta | DOC-09 exige paginar de a 25. Aprobada por el responsable con el plan; una prueba lo recorre con 30 documentos |
| DEC-123 | 11-10-2026 | La carpeta del portal ordena por fecha (lo último primero) salvo `?orden=nombre`; la búsqueda, por título | CLI-02 pide ambos órdenes sin fijar el predeterminado: el cliente suele venir por lo último publicado |
| DEC-124 | 11-10-2026 | "Nuevo" se calcula con la fecha de la versión vigente: menos de 14 días desde la subida o el reemplazo. La ficha no muestra número de versión | CLI-01 y E4: un reemplazo es un documento nuevo para el cliente, que no ve versiones (CLI-05) |
| DEC-125 | 11-10-2026 | Clase `enlace-tactil` (44 px de alto) en los enlaces de texto sueltos: migas de pan, "Ver todas", título de las filas con acciones, "¿Olvidó su contraseña?" y "Volver al acceso" | La medición a 360 px de la revisión en el navegador mostró esos enlaces con 17 a 20 px de alto (sección 9: áreas táctiles de 44 px) |
| DEC-126 | 11-10-2026 | `paginar` pasa a `core/paginacion.py` y el resumen de carpetas a `CarpetaQuerySet.con_resumen()` | Los usan el portal y el panel |
| DEC-127 | 11-10-2026 | Dos apps nuevas: `sitio` (páginas, servicios, datos del negocio) y `solicitudes` (formularios, antispam, notificación) | Sección 5. `Servicio` usa clave numérica y `slug`; `DatosNegocio` es un registro único que la base no deja duplicar (`pk = 1`) y que una migración crea vacío |
| DEC-128 | 11-10-2026 | Un servicio no se borra: se desactiva. `Solicitud.servicio` usa `PROTECT` y queda vacío para "Otro / no estoy seguro" | ADM-10 no pide borrar, y las solicitudes recibidas siguen nombrando su servicio. El `slug` se fija al crear y no cambia al renombrar |
| DEC-129 | 11-10-2026 | La notificación sale de la petición, por el hilo de `core/tareas.py`. La solicitud nace con notificación "por enviar" y pasa a enviada, fallida o correo no configurado | SOL-05. Enviar dentro de la petición haría esperar al visitante hasta 10 segundos si el SMTP no responde. Mismo criterio que DEC-64 y DEC-65. `reintentar_notificaciones` retoma las "por enviar" de más de 5 minutos |
| DEC-130 | 11-10-2026 | `notificar` bloquea la fila con `select_for_update(skip_locked=True)` durante el envío | Si el hilo de la petición y el cron coinciden, el profesional no recibe dos correos |
| DEC-131 | 11-10-2026 | La confirmación solo se muestra a quien acaba de enviar: el aviso viaja en una cookie firmada de mensajes de Django, sin crear sesión. Abrir la dirección sin él lleva al inicio | R4: la página afirma "Recibimos su solicitud" |
| DEC-132 | 11-10-2026 | Lo que el antispam descarta vuelve al mismo formulario, con lo escrito y un aviso neutro; si hay teléfono o correo registrados, los ofrece | Decidido por el responsable: no explica el motivo (SOL-04) ni afirma una recepción que no ocurrió (R4), y una persona real puede reintentar |
| DEC-133 | 11-10-2026 | Antispam: marca de tiempo firmada con `django.core.signing`, vigente 24 horas; al corregir un error se conserva la marca original. El límite por IP cuenta solo los envíos válidos | Sin servicios externos ni sesión. Quien corrige un campo no espera de nuevo. La IP vive una hora en la caché y no se guarda en la solicitud |
| DEC-134 | 11-10-2026 | Sin texto de política de privacidad no hay formularios: no se muestran, no se muestran los botones "Solicitar cotización" y un POST responde 404. En su lugar va el contacto registrado | Decidido por el responsable (SEG-12): no se registra un consentimiento a una política que no existe |
| DEC-135 | 11-10-2026 | Una página pública sin su contenido lleva `noindex` y no entra al sitemap. Todo lo que no es una página pública responde con `X-Robots-Tag: noindex`. `robots.txt` no enumera rutas privadas | PUB-07 y SEG-13. Prohibir una ruta en `robots.txt` la anuncia y le impide al buscador leer su `noindex`. `/acceso/` sigue con `noindex` |
| DEC-136 | 11-10-2026 | `sitemap.xml` y la URL canónica se arman con `SITIO_URL`, con una vista propia | `django.contrib.sitemaps` usa el encabezado `Host`; mismo criterio que DEC-66 |
| DEC-137 | 11-10-2026 | Contenido pendiente con dos reglas: lo vacío o con `[COMPLETAR]` no se muestra; lo de prueba ("TEXTO DE PRUEBA", "(DEMO)", correos `@ejemplo.test`) se muestra. Ambos se listan en `contenido_pendiente` y en el panel | Ajusta el plan: con los datos de `cargar_demo` hay que poder ver el sitio completo, y `--estricto` impide publicarlos |
| DEC-138 | 11-10-2026 | `cargar_demo` se adelanta a la Etapa 6. Corre con `DEBUG` o con `DEMO_PERMITIDO=true`, exige que exista un administrador y no pisa datos existentes | Pedido por el responsable. Cada versión de un documento registra quién la subió |
| DEC-139 | 11-10-2026 | El velo sobre fotografías pasa de 75 % a 80 % | Con 75 %, el texto secundario `#C7D0DD` sobre una zona blanca de la foto queda en 4,0:1; con 80 %, en 4,7:1. Una prueba lo comprueba |
| DEC-140 | 11-10-2026 | En el inicio, el encabezado va dentro de la portada, sobre la fotografía; en las demás páginas es una franja azul marino | Revisa DEC-42: es la pantalla 1 del mockup, sin posicionar el encabezado en forma absoluta |
| DEC-141 | 11-10-2026 | Fotografías sin rostros reconocibles ni logos; tampoco escenas de trabajo inseguro. Conversión a WebP con Pillow de un solo uso, fuera del `uv.lock` | Criterio aprobado por el responsable: las licencias no cubren la imagen de las personas ni las marcas. Un trabajador en altura sin protección es mala referencia para un servicio de prevención. Detalle en `FOTOS.md` |
| DEC-142 | 11-10-2026 | Recibir una solicitud no deja evento de auditoría; sí lo dejan el cambio de estado y el reintento de la notificación. Nombre, empresa, teléfono y comuna rechazan saltos de línea | El evento guardaría la IP del visitante (sección 6). Esos datos van al asunto del correo de notificación |
| DEC-143 | 11-10-2026 | La revisión de seguridad de la Etapa 7 la hizo un revisor sin el contexto de las etapas anteriores, en solo lectura y sin leer `SEGURIDAD.md`, `DECISIONES.md`, `PLAN.md` ni `TRAZABILIDAD.md`. Sus hallazgos se verificaron contra el código y el responsable aprobó la lista antes de corregir | Pedido por el responsable: quien construyó el sistema tiende a dar por buenas sus propias justificaciones. Reporte en `SEGURIDAD.md` §7 |
| DEC-144 | 11-10-2026 | La caché en base de datos admite 100.000 entradas, y una IP que superó su límite de recuperaciones no crea más entradas por RUT | H-01: con el tope de Django (300), al llenarse se borran primero las claves alfabéticamente menores, que son los bloqueos de acceso; se reprodujo con 299 solicitudes. Se descartó una tabla propia para los bloqueos: más código para el mismo resultado a este volumen |
| DEC-145 | 11-10-2026 | `Permissions-Policy` con un middleware propio que deniega 17 funciones del navegador, también al propio origen | SEG-02 y H-02. Django no trae el encabezado; una dependencia para una sola línea no se justifica |
| DEC-146 | 11-10-2026 | `PROXY_HTTPS_ENCABEZADO` define `SECURE_PROXY_SSL_HEADER`: obligatorio si hay proxy de confianza y rechazado si no lo hay. `CSRF_TRUSTED_ORIGINS` vale `SITIO_URL` si no se define. HSTS para subdominios y precarga, por variable y apagados | SEG-01 y H-03. Ajusta el plan de la etapa, que decía exigir `CSRF_TRUSTED_ORIGINS`: con un solo origen, exigirla era pedir dos veces el mismo dato |
| DEC-147 | 11-10-2026 | `check --deploy` con la configuración de producción es una prueba automática, no un paso aparte de la CI | Ajusta el plan de la etapa: así corre también en el equipo de desarrollo, y fija qué advertencias se aceptan (`SEGURIDAD.md` §5) |
| DEC-148 | 11-10-2026 | La recuperación no revoca el enlace de activación vigente; solo los restablecimientos anteriores. Superar un límite deja un evento de auditoría, no uno por petición | H-04, decidido por el responsable. Ajusta DEC-54: "un enlace nuevo revoca los anteriores" sigue valiendo para los que genera el administrador. Una cuenta pendiente puede tener dos enlaces vigentes; usar uno revoca el otro |
| DEC-149 | 11-10-2026 | `cargar_demo` exige `DEMO_PERMITIDO=true`; `DEBUG` ya no lo autoriza. `.env.example` la trae activada para desarrollo | H-06, decidido por el responsable. Ajusta DEC-138. Quien ya tenía su `.env` debe agregar la variable |
| DEC-150 | 11-10-2026 | En el admin de Django, la empresa y los privilegios de un usuario son de solo lectura; editar nombre, correo o estado deja un evento de auditoría, y desactivar revoca sus enlaces | H-08, decidido por el responsable. Ajusta DEC-69. De paso se cierra un error 500: marcar `is_staff` en un cliente chocaba con la restricción de la base |
| DEC-151 | 11-10-2026 | Los códigos de recuperación del 2FA siguen en la sesión hasta que la persona pulsa "Ya los guardé, continuar" (POST) | H-09: mostrarlos con un GET que además los borraba hacía que una recarga los perdiera. Los códigos ya están en la base (`django-otp` los guarda en claro), así que la sesión no agrega exposición |
| DEC-152 | 11-10-2026 | La prueba 1 exige que toda ruta no pública herede de un mixin de rol sin reemplazar su `dispatch`, salvo el admin de Django y las tres pantallas del segundo factor, que se nombran. `next` solo acepta rutas que empiezan con `/` | H-10 y H-11 |
| DEC-153 | 11-10-2026 | Sin cambio: el bloqueo por IP se levanta solo por comando (H-05), la marca del antispam es reutilizable 24 horas (H-07) y las rutas de servicios usan un entero (H-12) | Aprobado por el responsable. Los dos primeros quedan como limitaciones en `SEGURIDAD.md` §4; el tercero no es un recurso de clientes |
| DEC-154 | 11-10-2026 | Favicon provisional: el escudo de la marca (DEC-48) en blanco sobre azul marino, como SVG y como ICO de 16, 32 y 48 px. `/favicon.ico` redirige al archivo estático | Los navegadores piden esa ruta aunque la página enlace otro ícono. El ICO se generó con Edge sin interfaz y un guion de Node, sin Pillow (ajusta el plan). Se reemplaza con el logo real |
| DEC-155 | 11-10-2026 | La línea inferior de las pestañas es una sombra interior del contenedor | La barra de desplazamiento era vertical: el borde del contenedor más el margen negativo de cada pestaña desbordaban 1 px (medido). Se corrige la causa en vez de ocultar la barra |
| DEC-156 | 11-10-2026 | Accesibilidad, tras la revisión con teclado y axe-core: el resumen de errores lleva `role="alert"` y recibe el foco al cargar; Escape cierra los menús desplegables y devuelve el foco; el enlace "Saltar al contenido" mide 44 px al enfocarse; las fotografías de la portada y del acceso quedan dentro de una región; tres enlaces del panel pasan a 44 px de alto | E8. Una región `aria-live` que ya viene en la página no se anuncia al cargarla: por eso el foco. El enlace de saltar medía 24 px porque `not-sr-only` le quitaba el relleno |
| DEC-157 | 11-10-2026 | Las páginas públicas y las de acceso no cargan HTMX; el portal y el panel, sí | RNF-06: pesaba 17 KB y 120 ms de ejecución en el inicio sin usarse. **Hallazgo abierto:** ninguna plantilla usa atributos `hx-`; filtros, subida y cambios de estado se resolvieron con páginas completas y `XMLHttpRequest`. Quitarlo del todo se aparta de la sección 5: queda como pregunta al responsable |
| DEC-158 | 11-10-2026 | Fuente de respaldo "Inter respaldo" (Arial local con las medidas de Inter) y precarga de la fotografía de la portada desde el `<head>` | Lighthouse midió en el inicio un salto de diseño de 0,119 al cargar las fuentes y 2,5 s de LCP. Con ambos cambios: 0 y 2,4 s, y rendimiento de 89 a 98 |
| DEC-159 | 11-10-2026 | Contacto, Cotización y Privacidad llevan una `meta description` genérica con el nombre comercial ("Contacto de …."); sin nombre comercial no se publica | PUB-07 pide descripción por página. Revisa el criterio de la Etapa 6 ("la descripción no se inventa"): el texto solo dice qué página es y de quién, no afirma nada del negocio (R2) |
| DEC-160 | 11-10-2026 | El servicio de errores opcional (RNF-05) se decide en la Etapa 8, con el hosting. Firefox se revisa con el navegador real, manejado por WebDriver BiDi. El lector de pantalla se revisa por el árbol de accesibilidad, más una pasada del responsable con el Narrador | Decisiones del responsable al aprobar el plan de la etapa |
| DEC-161 | 11-10-2026 | Herramientas de la revisión, usadas una vez con `npx` y fuera del repositorio: axe-core 4.10.3 y Lighthouse 12.8.2 | No son dependencias del proyecto (mismo criterio que DEC-141) |
| DEC-162 | 11-10-2026 | Ningún índice nuevo tras medir con el volumen de diseño | RNF-01: la consulta más lenta tardó 8 ms y el peor p95 fue de 130 ms |
| DEC-163 | 11-10-2026 | HTMX se retira del proyecto: el archivo, su configuración, el atributo `hx-headers` y sus estilos. **Desviación de la sección 5**, que lo pide para filtros, subida con progreso y cambios de estado | Decidido por el responsable; cierra DEC-157. Ninguna plantilla lo usaba: los filtros y los cambios de estado son formularios y enlaces que recargan la página, y la subida con progreso usa `XMLHttpRequest` (DEC-95). Código sin uso es peso y superficie de ataque sin beneficio. La sección 5 se sigue cumpliendo en lo demás: interfaz renderizada en el servidor, JavaScript mínimo y sin frameworks. Si más adelante hace falta una interacción parcial, se reevalúa con una decisión nueva |

## Dependencias de ejecución

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| Django 6.1.2 | Framework | 5.2 LTS: exigiría `django-csp` y no es la serie más reciente |
| psycopg 3.3.6 (`binary`) | Driver de PostgreSQL, con ruedas precompiladas | Django no incluye driver |
| argon2-cffi 25.1.0 | Argon2id como hasher principal (AUT-05) | PBKDF2 nativo: no cumple el requisito |
| django-otp 1.7.4 | TOTP, códigos de recuperación y 2FA en el admin de Django (AUT-10, ADM-12) | TOTP propio: riesgo de seguridad innecesario. `django-two-factor-auth`: trae vistas, plantillas y más dependencias |
| segno 1.6.6 | Código QR del enrolamiento TOTP, generado en el servidor como SVG | Sin QR: enrolamiento poco usable. Servicio externo de QR: expondría el secreto |
| boto3 1.43.111 | Cliente de S3: subida en flujo y URL firmadas (DOC-03, DOC-04). Se importa solo con `DOCUMENTOS_ALMACENAMIENTO=s3` | `django-storages`: no declara soporte para Django 6.1 (DEC-96). Firmar a mano las peticiones: riesgo de seguridad innecesario |
| WhiteNoise 6.12.0 | Estáticos, en desarrollo y en producción | Servirlos con Django: no apto para producción |
| Gunicorn (Etapa 8) | Servidor WSGI | `runserver`: no es de producción |

## Dependencias de desarrollo y CI

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| pytest 9.1.1, pytest-django 4.14.0 | Pruebas (sección 12.1) | `unittest` nativo: la especificación pide `pytest-django` |
| pytest-cov 7.1.0 | Cobertura mínima del 85 % | Ninguna nativa |
| ruff 0.16.10 | Lint y formato (RNF-04) | Ninguna nativa |
| pip-audit 2.10.1 (solo CI) | Vulnerabilidades de dependencias en CI (SEG-09) | Ninguna nativa |
| moto 5.2.3 (extra `s3`) | Emulador de S3 para las pruebas, dentro del proceso (DEC-97) | Un contenedor MinIO: más memoria y otra imagen. Sustituir `boto3` con dobles a mano: no prueba las llamadas reales |
| flask 3.1.3, flask-cors 6.0.5 | Solo para `moto_server`, el emulador del perfil opcional `s3` de Compose | El extra `server` de moto: instala además más de diez paquetes que S3 no usa |

## Herramientas del build

| Herramienta | Versión | Origen | Verificación |
| --- | --- | --- | --- |
| uv | 0.12.24 | `ghcr.io/astral-sh/uv:0.12.24` (Docker) y PyPI (CI) | Versión fijada; el `uv.lock` se generó con ella |
| Tailwind CLI standalone | 4.3.3 | `https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/tailwindcss-linux-x64` | sha256 `dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a`, tomado del `sha256sums.txt` de la release y exigido por el `Dockerfile` |

## Archivos de terceros incluidos en el repositorio

Descargados el 09-10-2026 desde el registro npm y servidos desde la propia aplicación, sin CDN. Para comprobar uno: `Get-FileHash <archivo> -Algorithm SHA256`.

| Paquete | Versión | Licencia | Origen | sha256 del paquete |
| --- | --- | --- | --- | --- |
| @fontsource/inter | 5.3.0 (Inter v20 de Google Fonts, modificada el 10-09-2025) | OFL-1.1 | `https://registry.npmjs.org/@fontsource/inter/-/inter-5.3.0.tgz` | `02034af8d41dcc67ac8eab88f642e129bb8a2e8922abf30229c32725f54d8fd6` |
| lucide-static | 1.54.0 | ISC | `https://registry.npmjs.org/lucide-static/-/lucide-static-1.54.0.tgz` | `e902c38c3b0b132c90c26cd24e7021068e278a53c4c72fc3e49ef53dfe9d35fa` |

El paquete de Inter coincide además con el `shasum` SHA-1 que publica el registro npm (`866278dc2357659f8be1755c8b67f29d3697b440`).

| Archivo en el repositorio | Paquete y ruta de origen | sha256 del archivo |
| --- | --- | --- |
| `static/fonts/inter-latin-400-normal.woff2` | @fontsource/inter: `package/files/inter-latin-400-normal.woff2` | `8909904ab6c872eb994093482a88a28eca2cd95912d7b6fecd72103b0dc07edc` |
| `static/fonts/inter-latin-500-normal.woff2` | @fontsource/inter: `package/files/inter-latin-500-normal.woff2` | `f3779f1efccc4bdcdf9c0a02ab95bf6bd092ed09c48c08cedc725889edd1d19f` |
| `static/fonts/inter-latin-600-normal.woff2` | @fontsource/inter: `package/files/inter-latin-600-normal.woff2` | `f9a06e79cd3a2a20951c0f0e28f66dd0e6d3fda73911d640a2125c8fcb78f21a` |
| `static/fonts/inter-latin-700-normal.woff2` | @fontsource/inter: `package/files/inter-latin-700-normal.woff2` | `6f56409fd3d64bb85f7d070bce20749db2d66b6d63cec586cc22d1c761be2491` |
| `static/fonts/LICENCIA-Inter.txt` | @fontsource/inter: `package/LICENSE` | `3b0a5fca3d17942cde889069889dedbbbd075e9b599968c82a95f4d944e9b345` |
| `templates/iconos/building-2.svg` | lucide-static: `package/icons/building-2.svg` | `317f2bce8b0ce9807403caa59bb44a7e4dc8c69e86d847ff6af32f5d5b760d1a` |
| `templates/iconos/chevron-down.svg` | lucide-static: `package/icons/chevron-down.svg` | `354fcbf413773d63f8171a941abc9f76fe901a30da3b362d5bbd6df1faffc68d` |
| `templates/iconos/chevron-left.svg` | lucide-static: `package/icons/chevron-left.svg` | `a57c5c9b0516a4114236cb0ece0e53ed84b144fce50e1ff8b61e209869b17ad5` |
| `templates/iconos/chevron-right.svg` | lucide-static: `package/icons/chevron-right.svg` | `fece1122c8afb1bf5420fbbebab8c06823d9104041047cc27b0a2dc0c5210f6b` |
| `templates/iconos/circle-alert.svg` | lucide-static: `package/icons/circle-alert.svg` | `1c249776908aed049350da3a55f89e59febde9583aee2435389bdcddcc728df0` |
| `templates/iconos/circle-check.svg` | lucide-static: `package/icons/circle-check.svg` | `e4e78fa7f2f56508aa4432e911578ef5f726527ce1d879c1f8b587db0a42e0e3` |
| `templates/iconos/circle-user.svg` | lucide-static: `package/icons/circle-user.svg` | `659ba404275ff2f96b9ef642fc75aff7477fd43c00b2827d6fc7f7afc8d25687` |
| `templates/iconos/clipboard-list.svg` | lucide-static: `package/icons/clipboard-list.svg` | `4867272597be1fed356f5dbacbd72c35bca110c3d6112c5e1bc13a3bc6524c6b` |
| `templates/iconos/download.svg` | lucide-static: `package/icons/download.svg` | `32feff96642570a08940d3ff01486b05f644c689509fe747d1d02f9737c5dd3d` |
| `templates/iconos/eye-off.svg` | lucide-static: `package/icons/eye-off.svg` | `99f0a019e06f32a4288c4a59f4f60619656265d11807d9939f2386d06764c657` |
| `templates/iconos/eye.svg` | lucide-static: `package/icons/eye.svg` | `290d21625351cf13ef51fd443421e280da6896e0c790d4fb6833fdc251f4daa2` |
| `templates/iconos/file-image.svg` | lucide-static: `package/icons/file-image.svg` | `21f5ece743b8aaedc895751b5d715490c4c25934734dd8cba4adfcc3cc8e0cc2` |
| `templates/iconos/file-spreadsheet.svg` | lucide-static: `package/icons/file-spreadsheet.svg` | `226f1670e52cf6b58da18e38c55ecf8ac64343c69389410f1ee4e07ce18d2321` |
| `templates/iconos/file-text.svg` | lucide-static: `package/icons/file-text.svg` | `f6d8bfa5ebfaabc6ec2ebe830526007be2823d46a06e6a9421a13c1e0d5f9165` |
| `templates/iconos/file-type.svg` | lucide-static: `package/icons/file-type.svg` | `0081d398fa503b667e49faa38310e051ac0281a33fbef6fd9f5c35ef11f853cf` |
| `templates/iconos/folder.svg` | lucide-static: `package/icons/folder.svg` | `c525ffd338b3cf15e00470a9ea809579a1f6b92a09cb0a4be1bde00caec647ff` |
| `templates/iconos/house.svg` | lucide-static: `package/icons/house.svg` | `5c2625652f6ab72ad5047da7f0eb39d36725594caefbd655f5dbc1611d886527` |
| `templates/iconos/inbox.svg` | lucide-static: `package/icons/inbox.svg` | `215b4db66da94b3fff4330f21fdc8d0935212d069885b98b0e9fda64ad159851` |
| `templates/iconos/info.svg` | lucide-static: `package/icons/info.svg` | `cc1dd1dda0ecc62cd2ab3f92e75bf3d360e23c819273eb1b9ace00d3ceffcdd5` |
| `templates/iconos/loader-circle.svg` | lucide-static: `package/icons/loader-circle.svg` | `334abce32e8da0ff8f385522a726ba44e5681561e35d0c9a36cbdc0a5b88e67e` |
| `templates/iconos/lock.svg` | lucide-static: `package/icons/lock.svg` | `9cc54a58838cd07186c0d80c3f1033127551d62d31b4fc87d5d66dc93c4ebdc8` |
| `templates/iconos/log-out.svg` | lucide-static: `package/icons/log-out.svg` | `ef7277ff89e23e926166100f17b23802c00ec68c651d54aee2ceb7de8ee42891` |
| `templates/iconos/menu.svg` | lucide-static: `package/icons/menu.svg` | `2e13846bbadb5cf0c8eac246b0d7f53133688c688f3115b9735bade90aca0519` |
| `templates/iconos/message-square.svg` | lucide-static: `package/icons/message-square.svg` | `194a1003d4fddc7b830fac323a5f325e7a818494cc7fcbe8772aeb7b73933fff` |
| `templates/iconos/presentation.svg` | lucide-static: `package/icons/presentation.svg` | `7b09cf736339963e0e9374733a9239a89de49061faa5b6d955c2415fecdebc0d` |
| `templates/iconos/search.svg` | lucide-static: `package/icons/search.svg` | `9f9aa68d889ad150b25f72be17c3058c924d0ee6d8ca2e081866f7ddef99a054` |
| `templates/iconos/settings.svg` | lucide-static: `package/icons/settings.svg` | `cf4b3002bff5846e113f9a169a3b8892f42aa7798808367a1d3eeae710726a6f` |
| `templates/iconos/shield-check.svg` | lucide-static: `package/icons/shield-check.svg` | `f70a1b1b967cd6b587592a2df1254aa7eebc8c2477aa405de7c988ca5f92d299` |
| `templates/iconos/triangle-alert.svg` | lucide-static: `package/icons/triangle-alert.svg` | `b94124235a81cdf4f8e2bb813e955049e0d501cd30793e495b2d62c584a7a8af` |
| `templates/iconos/users.svg` | lucide-static: `package/icons/users.svg` | `7ecdabd5f6d168aa28f45a22569743c4bd7e036f0672cb7882810f8373859477` |
| `templates/iconos/arrow-down.svg` | lucide-static: `package/icons/arrow-down.svg` | `3b11c97f4321f6185be03fb0d14dcc3145706f5efbe61349fda5c36b02439ddc` |
| `templates/iconos/arrow-up.svg` | lucide-static: `package/icons/arrow-up.svg` | `2082b52f3880aaf55b20465f7b799ebc7e64812918916e35c19e289f74ce3011` |
| `templates/iconos/copy.svg` | lucide-static: `package/icons/copy.svg` | `f3ec65a85c2cb061e8112c907f7b3af731ccb3fc58808f41a45f6b46e92abec1` |
| `templates/iconos/history.svg` | lucide-static: `package/icons/history.svg` | `b43ba5de5518b8a990ce4a6569d691ec60483c93f89723274f7d89f89d2114b6` |
| `templates/iconos/lock-open.svg` | lucide-static: `package/icons/lock-open.svg` | `4f1c25e08c0c527e890eafc38eeaf01cd2b830ebfb8c1e2c76f54230717f666f` |
| `templates/iconos/pencil.svg` | lucide-static: `package/icons/pencil.svg` | `f8acff8aeb59ae50ce8de4a9151e595774463d1e362d8b1f9eec26d9fe7cee37` |
| `templates/iconos/plus.svg` | lucide-static: `package/icons/plus.svg` | `88616829bc4eaeb711fea7564f7db19871de5cce4cd832ad261caa926df289de` |
| `templates/iconos/trash-2.svg` | lucide-static: `package/icons/trash-2.svg` | `39a05b8b1e6631650ffb22077e27c12748b22dc17d3121d7e448e921d3ee99ef` |
| `templates/iconos/upload.svg` | lucide-static: `package/icons/upload.svg` | `4db8eda8e39632c83749f32f2582096ac6c5b7a143e51e46cffc8f9ed6b04652` |
| `templates/iconos/rotate-ccw.svg` | lucide-static: `package/icons/rotate-ccw.svg` | `33e03e50f8e1c91c4576c6376debcada525542e09a430b0f0d583ba82283d59e` |
| `templates/iconos/LICENCIA-lucide.txt` | lucide-static: `package/LICENSE` | `b495047bd93a9b06913511076f504daba17d5bbeb3e0650f3bb53a4220329c57` |

Los ocho íconos de la Etapa 3 (flechas, copiar, historial, candado abierto, lápiz, más y papelera) y los dos de la Etapa 4 (subir y restaurar) se extrajeron el 11-10-2026 del mismo paquete, descargado de nuevo y con el mismo sha256.

Los catorce íconos de la Etapa 6 se extrajeron el 11-10-2026 del mismo paquete, descargado de nuevo y con el mismo sha256: ocho para la lista fija de servicios (`hard-hat`, `clipboard-check`, `file-check`, `graduation-cap`, `search-check`, `flame`, `heart-pulse` y `scale`) y seis de interfaz (`phone`, `mail`, `map-pin`, `clock`, `message-circle` y `globe`).

| Archivo en el repositorio | sha256 del archivo |
| --- | --- |
| `templates/iconos/hard-hat.svg` | `64aaedb5d82deed59964d8da9850aa900ae4c6dd6d6dbf86163433e4995a4176` |
| `templates/iconos/clipboard-check.svg` | `282e9e20933834fb68470b3a14beef8090013eb08089b25eb7c8223115f7941b` |
| `templates/iconos/file-check.svg` | `56090986c724b52161759e94615a22afd0a9f0784f1f973d920316859cd56cae` |
| `templates/iconos/graduation-cap.svg` | `7eca97c943744559bd5fff5e75168116694d64d3cd8364adceb5d3301d2593a7` |
| `templates/iconos/search-check.svg` | `dae78db399184a25f8e4ee436d4fd153341698064ba6421004d8803613fb879a` |
| `templates/iconos/flame.svg` | `2ebdce96af7f4971df532cac68c4bdf3faa1af732887e857308c4e6320c1c5c4` |
| `templates/iconos/heart-pulse.svg` | `9367c76677f019829e7d25469ebf49ae5f150aa382c30bd1b227971156351fda` |
| `templates/iconos/scale.svg` | `7cb6f487ae10569256c116f0e94c872c04627135367a470d379787c9c7c7bfc5` |
| `templates/iconos/phone.svg` | `3cc192c0af510ffb0157833aac736e02f316c5ff7b3f028abd2b0e0908e4c550` |
| `templates/iconos/mail.svg` | `7c8d6e81dba3a89b5826338470f3aa28bae322813d8f6f0e338c4430d1c11ac5` |
| `templates/iconos/map-pin.svg` | `1cdff837a47df6bde70b81168e9e13c7008b8997e38a97d2cb6daab8e184ee43` |
| `templates/iconos/clock.svg` | `c321654a4cf667a6321296c359e8203ff238936ac09ecb4dc1fb0601df7acf4a` |
| `templates/iconos/message-circle.svg` | `5ad14e9dd248ea27450a2f6f5ba41a46c98b58fb5036ced2f9509c80548ba690` |
| `templates/iconos/globe.svg` | `5d591ab9888ac71f268923abc8c2552c8840b3775aeea5b78131638e9a700073` |

Las fotografías del sitio tienen su propio registro en `docs/FOTOS.md`.

Los archivos se copiaron sin modificar; todos tienen fin de línea LF, que es como el repositorio guarda el texto (`.gitattributes`).

Retirado el 09-10-2026: IBM Plex Sans (`@ibm/plex-sans` 1.1.0), reemplazada por Inter (DEC-37).

Retirado el 11-10-2026: HTMX (`htmx.org` 2.0.10, `static/vendor/htmx.min.js` y su licencia), que ninguna plantilla usaba (DEC-163).

## Dependencias descartadas

`django-storages` (DEC-96), `django-environ`, `dj-database-url`, `python-magic`, `filetype`, `django-axes`, `django-ratelimit`, `django-csp`, `django-htmx`, `factory-boy`, `python-json-logger`, `mypy` y `django-debug-toolbar`: lo que aportan se resuelve con Django o con la biblioteca estándar. El servicio de errores opcional (RNF-05) se decide en la Etapa 8 (DEC-160).
