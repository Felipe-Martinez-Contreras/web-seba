# Trazabilidad

Requisito → implementación → prueba → estado. Se actualiza al cerrar cada etapa.

Estados: `Pendiente`, `En curso`, `Verificado` (prueba automática en verde) y `Verificado manual` (con el procedimiento documentado). La etapa es la prevista en `PLAN.md`.

## Sitio público (PUB)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| PUB-01 | Páginas públicas y páginas 404 y 500 propias | 1 y 6 | — | — | Pendiente |
| PUB-02 | Inicio con contenido de DatosNegocio | 6 | — | — | Pendiente |
| PUB-03 | Servicios con cotización preseleccionada | 6 | — | — | Pendiente |
| PUB-04 | Navegación y pie | 6 | — | — | Pendiente |
| PUB-05 | Secciones sin dato no se muestran | 6 | — | — | Pendiente |
| PUB-06 | Comando `contenido_pendiente` y aviso en el panel | 6 | — | — | Pendiente |
| PUB-07 | SEO básico, sitemap, robots y `noindex` | 6 | — | — | Pendiente |
| PUB-08 | Sin fotos de stock | 6 | — | — | Pendiente |

## Formularios y solicitudes (SOL)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| SOL-01 | Formulario de consulta | 6 | — | — | Pendiente |
| SOL-02 | Formulario de cotización | 6 | — | — | Pendiente |
| SOL-03 | Validación en el servidor con errores por campo | 6 | — | — | Pendiente |
| SOL-04 | Antispam sin servicios externos | 6 | — | — | Pendiente |
| SOL-05 | Guardar, notificar y registrar el resultado | 6 | — | — | Pendiente |
| SOL-06 | Redirección a confirmación neutra | 6 | — | — | Pendiente |
| SOL-07 | Sin correo automático al visitante | 6 | — | — | Pendiente |
| SOL-08 | Correo al profesional con `Reply-To` | 6 | — | — | Pendiente |
| SOL-09 | Bandeja de solicitudes en el panel | 6 | — | — | Pendiente |
| SOL-10 | Detalle, estados, notas y reintento | 6 | — | — | Pendiente |
| SOL-11 | Comando `reintentar_notificaciones` | 6 | — | — | Pendiente |

## Autenticación y cuentas (AUT)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| AUT-01 | Acceso con RUT normalizado y validado | 2 | — | — | Pendiente |
| AUT-02 | Mensaje genérico ante credenciales inválidas | 2 | — | — | Pendiente |
| AUT-03 | Redirección según rol | 2 | — | — | Pendiente |
| AUT-04 | Bloqueo temporal por RUT e IP | 2 | — | — | Pendiente |
| AUT-05 | Argon2id y validadores de contraseña | 2 | — | — | Pendiente |
| AUT-06 | Activación con enlace de un solo uso | 2 | — | — | Pendiente |
| AUT-07 | Recuperación con mensaje único | 2 | — | — | Pendiente |
| AUT-08 | Cambio de contraseña y cierre de otras sesiones | 2 | — | — | Pendiente |
| AUT-09 | Cookies seguras, expiración y cierre por POST | 2 | — | — | Pendiente |
| AUT-10 | 2FA obligatorio para administradores | 2 | — | — | Pendiente |
| AUT-11 | Corte inmediato al desactivar usuario o empresa | 2 | — | — | Pendiente |
| AUT-12 | Comando para crear el primer administrador | 2 | — | — | Pendiente |

## Panel de administración (ADM)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| ADM-01 | Estructura del panel y menú móvil | 3 | — | — | Pendiente |
| ADM-02 | Inicio del panel con datos reales | 3 | — | — | Pendiente |
| ADM-03 | Gestión de empresas | 3 | — | — | Pendiente |
| ADM-04 | Carpetas base al crear una empresa | 3 | — | — | Pendiente |
| ADM-05 | Ficha de empresa con tres pestañas | 3 | — | — | Pendiente |
| ADM-06 | Usuarios de la empresa | 3 | — | — | Pendiente |
| ADM-07 | Gestión de carpetas | 3 | — | — | Pendiente |
| ADM-08 | Gestión de documentos | 4 | — | — | Pendiente |
| ADM-09 | Papelera y comando `purgar_papelera` | 4 | — | — | Pendiente |
| ADM-10 | Contenido del sitio | 6 | — | — | Pendiente |
| ADM-11 | Listado de auditoría | 3 | — | — | Pendiente |
| ADM-12 | Admin de Django restringido y con 2FA | 2 | — | — | Pendiente |

## Gestión documental (DOC)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| DOC-01 | Lista blanca de formatos | 4 | — | — | Pendiente |
| DOC-02 | Validación de cada archivo en el servidor | 4 | — | — | Pendiente |
| DOC-03 | Almacenamiento privado con claves aleatorias | 4 | — | — | Pendiente |
| DOC-04 | Ver y descargar por una vista con sesión | 4 | — | — | Pendiente |
| DOC-05 | `inline` o `attachment` y nombre RFC 6266 | 4 | — | — | Pendiente |
| DOC-06 | 404 para recursos inexistentes o ajenos | 4 | — | — | Pendiente |
| DOC-07 | Documento solo en carpetas de su empresa | 4 | — | — | Pendiente |
| DOC-08 | Versiones al reemplazar | 4 | — | — | Pendiente |
| DOC-09 | Paginación y sin consultas N+1 | 4 | — | — | Pendiente |

## Portal del cliente (CLI)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| CLI-01 | Inicio del portal | 5 | — | — | Pendiente |
| CLI-02 | Vista de carpeta | 5 | — | — | Pendiente |
| CLI-03 | Búsqueda por título | 5 | — | — | Pendiente |
| CLI-04 | Mi cuenta | 5 | — | — | Pendiente |
| CLI-05 | Solo lectura aplicada en el servidor | 5 | — | — | Pendiente |
| CLI-06 | Estado vacío con contacto | 5 | — | — | Pendiente |
| CLI-07 | Cualquier documento en dos clics | 5 | — | — | Pendiente |

## Auditoría (AUD)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| AUD-01 | Eventos registrados | 2 a 6 | — | — | Pendiente |
| AUD-02 | Contenido de cada evento, sin secretos | 2 a 6 | — | — | Pendiente |
| AUD-03 | Solo agregar; retención y `depurar_auditoria` | 3 | — | — | Pendiente |

## Seguridad (SEG)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| SEG-01 | Configuración de producción y `check --deploy` | 7 y 8 | — | — | Pendiente |
| SEG-02 | CSP y encabezados | 7 | — | — | Pendiente |
| SEG-03 | CSRF en formularios y HTMX | 2 | — | — | Pendiente |
| SEG-04 | Mixins de rol y prueba de todas las URL | 3 y 7 | — | — | Pendiente |
| SEG-05 | UUID en las URL y 404 para lo ajeno | 4 | — | — | Pendiente |
| SEG-06 | Autoescape y textos editables sin HTML | 6 | — | — | Pendiente |
| SEG-07 | Archivos subidos nunca ejecutados ni servidos como estáticos | 4 | — | — | Pendiente |
| SEG-08 | Secretos fuera del código y credenciales mínimas | 1 y 8 | — | — | Pendiente |
| SEG-09 | Versiones fijadas y `pip-audit` en CI | 1 | — | — | Pendiente |
| SEG-10 | Logs sin datos sensibles | 7 | — | — | Pendiente |
| SEG-11 | Respaldos y restauración probada | 8 | — | — | Pendiente |
| SEG-12 | Privacidad y consentimiento | 6 | — | — | Pendiente |
| SEG-13 | Admin de Django fuera de robots y sitemap | 6 | — | — | Pendiente |

## Requisitos no funcionales (RNF)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| RNF-01 | Volumen de diseño | 7 | — | — | Pendiente |
| RNF-02 | Tiempos de respuesta y subidas de 25 MB | 7 y 8 | — | — | Pendiente |
| RNF-03 | Navegadores soportados | 7 | — | — | Pendiente |
| RNF-04 | `ruff`, tipado y sin código muerto | 1 | — | — | Pendiente |
| RNF-05 | Logs estructurados y `/salud/` | 1 y 7 | — | — | Pendiente |
| RNF-06 | Lighthouse móvil de 90 o más | 7 y 8 | — | — | Pendiente |
