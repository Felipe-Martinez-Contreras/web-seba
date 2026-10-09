# Trazabilidad

Requisito → implementación → prueba → estado. Se actualiza al cerrar cada etapa.

Estados: `Pendiente`, `En curso`, `Verificado` (prueba automática en verde) y `Verificado manual` (con el procedimiento documentado). La etapa es la prevista en `PLAN.md`.

## Sitio público (PUB)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| PUB-01 | Páginas públicas y páginas 404 y 500 propias | 1 y 6 | `templates/404.html`, `templates/500.html` | `core/tests/test_vistas.py` (`test_pagina_404_propia`, `test_pagina_500_propia_no_muestra_la_traza`) | En curso: 404 y 500 verificadas; páginas públicas en la Etapa 6 |
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
| SEG-02 | CSP y encabezados | 1 y 7 | `config/settings/base.py` (`SECURE_CSP`), `templates/base.html` | `config/tests/test_configuracion.py` (`test_encabezados_de_seguridad`), `core/tests/test_vistas.py` (`test_las_plantillas_no_llevan_estilos_ni_scripts_en_linea`) | En curso: CSP activa; `Permissions-Policy` y revisión completa en la Etapa 7 |
| SEG-03 | CSRF en formularios y HTMX | 2 | — | — | Pendiente |
| SEG-04 | Mixins de rol y prueba de todas las URL | 3 y 7 | — | — | Pendiente |
| SEG-05 | UUID en las URL y 404 para lo ajeno | 4 | — | — | Pendiente |
| SEG-06 | Autoescape y textos editables sin HTML | 6 | — | — | Pendiente |
| SEG-07 | Archivos subidos nunca ejecutados ni servidos como estáticos | 4 | — | — | Pendiente |
| SEG-08 | Secretos fuera del código y credenciales mínimas | 1 y 8 | `config/env.py`, `config/settings/prod.py`, `.env.example`, `.gitignore` | `config/tests/test_configuracion.py` (`test_prod_se_niega_*`, `test_la_clave_de_ejemplo_es_la_de_env_example`) | En curso: configuración verificada; credenciales del almacenamiento en la Etapa 8 |
| SEG-09 | Versiones fijadas y `pip-audit` en CI | 1 | `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` (trabajo `auditoria`) | Trabajo `auditoria` de la CI | Verificado manual: resultado de la CI |
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
| RNF-04 | `ruff`, tipado y sin código muerto | 1 | `pyproject.toml` (`tool.ruff`), `.github/workflows/ci.yml` (trabajo `lint`) | `ruff check .` y `ruff format --check .` en la CI | En curso: se comprueba en cada etapa |
| RNF-05 | Logs estructurados y `/salud/` | 1 y 7 | `core/views.py`, `core/logs.py`, `config/settings/base.py` (`LOGGING`) | `core/tests/test_vistas.py` (`test_salud_*`, `test_formato_json_de_los_logs`) | En curso: `/salud/` y logs verificados; servicio de errores opcional en la Etapa 7 |
| RNF-06 | Lighthouse móvil de 90 o más | 7 y 8 | — | — | Pendiente |

## Base de la Etapa 1 (sin código de requisito)

Reglas de las secciones 4, 5 y 6 de la especificación que sostienen a los requisitos de las etapas siguientes.

| Regla | Archivos | Prueba | Estado |
| --- | --- | --- | --- |
| RUT: normalización, dígito verificador y formato `12.345.678-5` | `core/rut.py`, `core/validators.py`, `core/fields.py`, `core/templatetags/formato.py` | `core/tests/test_rut.py` | Verificado |
| Usuario personalizado con RUT único como identificador | `cuentas/models.py`, `cuentas/migrations/0001_initial.py` | `cuentas/tests/test_modelos.py` | Verificado |
| Cliente con empresa y administrador sin empresa, en la base de datos | `cuentas/models.py` (`usuario_rol_coherente_con_empresa`) | `test_la_base_rechaza_un_cliente_sin_empresa`, `test_la_base_rechaza_un_administrador_con_empresa` | Verificado |
| La cuenta se crea sin contraseña utilizable | `cuentas/managers.py` | `test_create_user_sin_contrasena_deja_una_contrasena_no_utilizable` | Verificado |
| `is_staff` e `is_superuser` solo para el superusuario técnico | `cuentas/managers.py`, `cuentas/models.py` | `test_create_user_no_admite_privilegios_tecnicos`, `test_la_base_rechaza_un_cliente_con_privilegios_tecnicos` | Verificado |
| Borrar una empresa nunca borra usuarios (`PROTECT`) | `cuentas/models.py` | `test_borrar_una_empresa_con_usuarios_no_borra_nada`, `test_la_base_tambien_impide_borrar_una_empresa_con_usuarios` | Verificado |
| Empresa con UUID y RUT único validado | `empresas/models.py`, `empresas/migrations/0001_initial.py` | `empresas/tests/test_modelos.py` | Verificado |
| Configuración por entorno; producción no arranca con configuración faltante o de ejemplo | `config/settings/`, `config/env.py` | `config/tests/test_configuracion.py` | Verificado |
| `es-cl`, `America/Santiago`, `USE_TZ` y fechas `dd-mm-aaaa` | `config/settings/base.py`, `config/formats/es_CL/formats.py` | `test_idioma_y_zona_horaria`, `test_fechas_con_formato_chileno_y_textos_en_espanol` | Verificado |
| Componentes y página de referencia solo en desarrollo | `templates/componentes/`, `core/referencia.py`, `core/urls_dev.py` | `test_la_referencia_*`, `test_el_campo_con_error_queda_asociado_a_su_mensaje` | Verificado (HTML; aspecto visual sin revisar) |
| `docker compose up` desde cero con migraciones en base vacía | `Dockerfile`, `compose.yaml`, `docker/arrancar-dev.sh` | Trabajo `arranque` de la CI y clon limpio local | Verificado manual |
