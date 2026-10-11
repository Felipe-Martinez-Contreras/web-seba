# Trazabilidad

Requisito → implementación → prueba → estado. Se actualiza al cerrar cada etapa.

Estados: `Pendiente`, `En curso`, `Verificado` (prueba automática en verde) y `Verificado manual` (con el procedimiento documentado). La etapa es la prevista en `PLAN.md`.

## Sitio público (PUB)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| PUB-01 | Páginas públicas y páginas 404 y 500 propias | 1 y 6 | `templates/404.html`, `templates/500.html` | `core/tests/test_vistas.py` (`test_pagina_404_propia`, `test_pagina_500_propia_no_muestra_la_traza`) | En curso: 404 y 500 verificadas; páginas públicas en la Etapa 6 |
| PUB-02 | Inicio según la referencia visual: portada, servicios, contacto con formulario y pie | 6 | — | — | Pendiente |
| PUB-03 | Servicios con cotización preseleccionada | 6 | — | — | Pendiente |
| PUB-04 | Navegación con logo y "Acceso clientes"; menú en móvil; pie con redes si existen | 6 | — | — | Pendiente |
| PUB-05 | Secciones sin dato no se muestran | 6 | — | — | Pendiente |
| PUB-06 | Comando `contenido_pendiente` y aviso en el panel | 6 | — | — | Pendiente |
| PUB-07 | SEO básico, sitemap, robots y `noindex` | 6 | — | — | Pendiente |
| PUB-08 | Fotografías de bancos gratuitos con licencia, registradas en `docs/FOTOS.md` | 6 | — | — | Pendiente |

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
| SOL-09 | Bandeja "Solicitudes" con pestañas Consultas y Cotizaciones e insignias | 6 | — | — | Pendiente |
| SOL-10 | Detalle, estados (Pendiente, En proceso, Resuelta, Descartada), notas y reintento | 6 | — | — | Pendiente |
| SOL-11 | Comando `reintentar_notificaciones` | 6 | — | — | Pendiente |

## Autenticación y cuentas (AUT)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| AUT-01 | Acceso con RUT normalizado y validado; botón para mostrar la contraseña; sin "Recordarme" | 2 | `cuentas/forms.py`, `cuentas/views.py` (`acceso`), `cuentas/templates/cuentas/acceso.html`, `templates/base_acceso.html` | `cuentas/tests/test_acceso.py` (`test_el_formulario_de_acceso_*`, `test_el_rut_se_acepta_*`, `test_el_rut_con_k_*`) | Verificado. Aspecto revisado con capturas a 360, 768 y 1280 px el 09-10-2026 |
| AUT-02 | Mensaje genérico ante credenciales inválidas | 2 | `cuentas/backends.py`, `cuentas/services.py` (`intentar_acceso`) | `test_la_respuesta_es_identica_exista_o_no_el_rut`, `test_cada_intento_ejecuta_exactamente_una_verificacion_de_contrasena`, `test_cada_intento_fallido_hace_las_mismas_consultas`; medición en `SEGURIDAD.md` | Verificado |
| AUT-03 | Redirección según rol | 2 | `cuentas/views.py` (`_continuar`), `core/navegacion.py`, `portal/`, `panel/` | `test_el_cliente_entra_al_portal_y_queda_registrado`, `test_el_administrador_pasa_primero_por_el_segundo_factor` | Verificado |
| AUT-04 | Bloqueo temporal por RUT e IP | 2 | `core/ip.py`, `core/middleware.py`, `core/limites.py`, `cuentas/bloqueo.py`, `panel/views/usuarios.py` (`UsuarioDesbloquear`), comando `desbloquear_acceso` | `core/tests/test_ip.py`, `cuentas/tests/test_bloqueo.py`, `test_acceso_bloqueo.py`, `test_comandos.py` | Verificado, con el botón de desbloqueo en la lista de usuarios |
| AUT-05 | Argon2id y validadores de contraseña | 2 | `config/settings/base.py` (`PASSWORD_HASHERS`, `AUTH_PASSWORD_VALIDATORS`), `cuentas/forms.py` | `test_contrasenas_con_argon2_y_minimo_de_12_caracteres`, `test_una_contrasena_debil_se_rechaza_sin_consumir_el_enlace`, `test_la_contrasena_nueva_pasa_por_los_validadores` | Verificado |
| AUT-06 | Activación con enlace de un solo uso | 2 y 3 | `cuentas/models.py` (`EnlaceAcceso`), `cuentas/services.py` (`generar_enlace`, `usar_enlace`), `cuentas/views.py` (`definir_contrasena`); desde el panel: `cuentas/services.py` (`entregar_enlace`), `templates/componentes/campo_copiable.html` | `cuentas/tests/test_enlaces.py`, `panel/tests/test_usuarios.py` (`test_con_correo_configurado_*`, `test_si_el_correo_falla_*`, `test_sin_marcar_la_casilla_*`, `test_generar_un_enlace_nuevo_*`) | Verificado. El botón "Copiar enlace" se revisó en capturas; el copiado al portapapeles se prueba a mano (README) |
| AUT-07 | Recuperación con mensaje único | 2 | `cuentas/services.py` (`solicitar_recuperacion`, `enviar_enlace_de_recuperacion`), `core/tareas.py`, `core/correo.py` | `cuentas/tests/test_recuperacion.py` | Verificado |
| AUT-08 | Cambio de contraseña y cierre de otras sesiones | 2 | `cuentas/views.py` (`MiCuenta`), `cuentas/services.py` (`cambiar_contrasena`) | `cuentas/tests/test_sesiones.py` (`test_cambiar_la_contrasena_*`, `test_el_cliente_no_puede_cambiar_su_correo_*`), `test_restablecer_cierra_la_sesion_abierta_en_otro_dispositivo` | Verificado |
| AUT-09 | Cookies seguras, expiración y cierre por POST | 2 | `config/settings/base.py` (`SESSION_*`), `config/settings/prod.py`, `cuentas/views.py` (`salir`) | `cuentas/tests/test_sesiones.py` (`test_configuracion_de_las_sesiones`, `test_en_produccion_las_cookies_son_seguras`, `test_la_sesion_vence_*`), `test_el_cierre_de_sesion_es_solo_por_post` | Verificado |
| AUT-10 | 2FA obligatorio para administradores | 2 | `cuentas/dos_factores.py`, `cuentas/views.py` (`verificacion`, `configurar_2fa`, `codigos_2fa`), comando `restablecer_2fa` | `cuentas/tests/test_dos_factores.py` | Verificado. Probado además en Edge con un código real el 09-10-2026 |
| AUT-11 | Corte inmediato al desactivar usuario o empresa | 2 | `cuentas/backends.py` (`get_user`, `user_can_authenticate`), `cuentas/middleware.py` | `cuentas/tests/test_corte.py` | Verificado |
| AUT-12 | Comando para crear el primer administrador | 2 | `cuentas/management/commands/crear_administrador.py` | `cuentas/tests/test_comandos.py` (`test_crear_administrador_*`) | Verificado |

## Panel de administración (ADM)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| ADM-01 | Estructura del panel: barra lateral azul marino (Inicio, Clientes, Solicitudes, Auditoría, Configuración) y menú móvil | 3 y 6 | `core/navegacion.py`, `templates/componentes/barra_lateral.html`, `_barra_lateral_enlaces.html`, `barra_superior.html`, `panel/urls.py` | `panel/tests/test_clientes.py` (`test_el_menu_del_panel_lista_solo_las_secciones_que_existen`) | En curso: estructura verificada, con capturas a 360, 768 y 1280 px el 11-10-2026; Solicitudes y Contenido del sitio entran al menú en la Etapa 6 |
| ADM-02 | Inicio del panel con indicadores, solicitudes y clientes recientes, y avisos | 3, 4 y 6 | `panel/views/inicio.py`, `panel/templates/panel/inicio.html`, `empresas/querysets.py` (`con_cuentas_pendientes`) | `test_el_inicio_muestra_solo_datos_reales`, `test_el_inicio_sin_clientes_explica_como_empezar` | En curso: clientes activos, cuentas pendientes, clientes recientes y documentos subidos en 30 días (`test_el_inicio_del_panel_cuenta_los_documentos_subidos_en_30_dias`) verificados; indicadores y tabla de solicitudes y avisos de notificaciones y de contenido en la Etapa 6 |
| ADM-03 | Gestión de empresas | 3 | `empresas/forms.py`, `empresas/services.py`, `panel/views/clientes.py`, `panel/templates/panel/clientes.html`, `cliente_formulario.html` | `panel/tests/test_clientes.py` (`test_los_datos_invalidos_*`, `test_el_listado_*`, `test_editar_*`, `test_e6_*`) | Verificado |
| ADM-04 | Carpetas base al crear una empresa | 3 | `config/settings/base.py` (`CARPETAS_BASE`), `empresas/services.py` (`crear_empresa`) | `test_e2_crear_cliente_con_carpetas_usuario_y_enlace_hasta_el_portal_vacio`, `test_sin_marcar_la_opcion_la_empresa_se_crea_sin_carpetas` | Verificado |
| ADM-05 | Ficha de empresa con tres pestañas | 3 y 4 | `panel/views/base.py`, `panel/views/clientes.py`, `panel/templates/panel/_cliente_cabecera.html`, `cliente_documentos.html`, `cliente_usuarios.html`, `cliente_actividad.html` | `test_la_ficha_tiene_tres_pestanas_con_url_propia`, `panel/tests/test_auditoria.py` (`test_la_pestana_actividad_*`) | Verificado. La pestaña Documentos lista las carpetas con su cantidad de documentos y lleva a cada una y a la papelera (`test_la_pestana_documentos_cuenta_los_documentos_sin_consultas_por_carpeta`) |
| ADM-06 | Usuarios de la empresa | 3 | `cuentas/forms.py` (`FormularioCliente`), `cuentas/services.py`, `cuentas/estados.py`, `panel/views/usuarios.py`, `panel/templates/panel/cliente_usuarios.html`, `usuario_formulario.html`, `usuario_enlace.html` | `panel/tests/test_usuarios.py`, `cuentas/tests/test_acceso_bloqueo.py` | Verificado |
| ADM-07 | Gestión de carpetas | 3 y 4 | `empresas/models.py` (`Carpeta`), `empresas/services.py` (`eliminar_carpeta`, `CarpetaConDocumentos`), `empresas/forms.py`, `panel/views/carpetas.py`, `panel/templates/panel/cliente_documentos.html`, `carpeta_formulario.html`, `documentos/models.py` (`PROTECT`) | `panel/tests/test_carpetas.py` (`test_una_carpeta_con_documentos_no_se_elimina_*`, `test_los_documentos_de_la_papelera_tambien_impiden_*`, `test_la_base_protege_la_carpeta_*`, `test_una_carpeta_se_puede_eliminar_tras_mover_*`) | Verificado, incluida la regla de no eliminar carpetas con documentos, también en la papelera (DEC-107) |
| ADM-08 | Gestión de documentos | 4 | `documentos/services.py`, `documentos/forms.py`, `panel/views/documentos.py`, `panel/templates/panel/carpeta.html`, `documento.html`, `documento_formulario.html`, `_resultados_subida.html`, `templates/componentes/zona_subida.html`, `resultado_subida.html`, `static/js/subida.js` | `documentos/tests/test_subida.py`, `documentos/tests/test_documentos.py` | Verificado. La barra de progreso y el resultado por archivo se comprobaron en Edge el 11-10-2026 con seis archivos, uno de 24,9 MB (ver el reporte de la etapa); el JavaScript no tiene prueba automática. El reemplazo no muestra progreso |
| ADM-09 | Papelera y comando `purgar_papelera` | 4 | `documentos/services.py` (`eliminar`, `restaurar`, `purgar_vencidos`), `documentos/management/commands/purgar_papelera.py`, `panel/views/documentos.py` (`ClientePapelera`), `panel/templates/panel/papelera.html` | `test_e5_eliminar_envia_a_la_papelera_y_restaurar_lo_devuelve`, `test_pasado_el_plazo_ya_no_se_puede_restaurar`, `test_purgar_papelera_borra_solo_lo_vencido_*`, `test_si_la_purga_falla_a_medias_*` | Verificado. Programar el comando en el cron es de la Etapa 8 |
| ADM-10 | Contenido del sitio | 6 | — | — | Pendiente |
| ADM-11 | Listado de auditoría | 3 | `auditoria/forms.py`, `auditoria/models.py` (`filtrar`), `panel/views/auditoria.py`, `panel/templates/panel/auditoria.html`, `_eventos.html` | `panel/tests/test_auditoria.py` | Verificado |
| ADM-12 | Admin de Django restringido y con 2FA | 2 | `core/sitio_admin.py`, `config/apps.py`, `config/urls.py`, `cuentas/admin.py`, `empresas/admin.py`, `auditoria/admin.py` | `test_el_admin_de_django_exige_superusuario_tecnico_con_2fa`, `test_el_admin_de_django_no_permite_fijar_contrasenas_ni_tocar_la_auditoria` | Verificado |

## Gestión documental (DOC)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| DOC-01 | Lista blanca de formatos | 4 | `config/settings/base.py` (`DOCUMENTOS_FORMATOS`), `documentos/validacion.py` | `documentos/tests/test_validacion.py` (`test_los_formatos_permitidos_*`, `test_la_lista_blanca_es_configurable`, `test_un_svg_*`, `test_un_archivo_con_macros_*`, `test_un_zip_comun_*`) | Verificado |
| DOC-02 | Validación de cada archivo en el servidor | 4 | `documentos/validacion.py`, `documentos/subida.py`, `documentos/services.py` (`subir`) | `documentos/tests/test_validacion.py`, `documentos/tests/test_subida.py` (`test_prueba_10_*`, `test_una_peticion_enorme_*`) | Verificado |
| DOC-03 | Almacenamiento privado con claves aleatorias | 4 y 8 | `documentos/almacenamiento.py`, `documentos/models.py` (`version_clave_sin_datos`), `documentos/comprobaciones.py`, `compose.yaml` (volumen `documentos_datos`) | `documentos/tests/test_almacenamiento.py` | Verificado con el almacenamiento local y con S3 emulado (`moto`). Pendiente: bucket real, con `comprobar_almacenamiento --firma` (Etapa 8) |
| DOC-04 | Ver y descargar por una vista con sesión | 4 y 8 | `documentos/services.py` (`entregar`), `documentos/almacenamiento.py` (`entregar`), `portal/views.py`, `panel/views/documentos.py` | `documentos/tests/test_entrega.py`, `documentos/tests/test_aislamiento.py` | Verificado. La redirección con URL firmada, contra S3 emulado: el emulador no valida firma ni vencimiento, así que los 2 minutos están verificados como parámetro de la URL y falta hacerlos cumplir contra el bucket real (Etapa 8) |
| DOC-05 | `inline` o `attachment` y nombre RFC 6266 | 4 | `documentos/services.py` (`entregar`), `documentos/validacion.py` (`sanear_nombre`, `VISIBLES_EN_NAVEGADOR`) | `test_ver_abre_en_el_navegador_solo_pdf_jpg_y_png`, `test_el_nombre_descargado_conserva_tildes_y_enie_segun_rfc_6266` | Verificado. "Ver" de un PDF comprobado en Edge el 11-10-2026 |
| DOC-06 | 404 para recursos inexistentes o ajenos | 4 | `documentos/querysets.py`, `portal/views.py`, `panel/views/documentos.py` | `test_prueba_2_un_cliente_de_a_no_ve_ni_descarga_documentos_de_b_con_el_uuid_correcto` (misma página que un UUID inexistente) | Verificado |
| DOC-07 | Documento solo en carpetas de su empresa | 4 | `documentos/forms.py` (`FormularioMover`), `documentos/services.py` (`mover`) | `test_mover_solo_entre_carpetas_de_la_misma_empresa` | Verificado. La base no lo puede expresar: lo aplican el formulario y el servicio |
| DOC-08 | Versiones al reemplazar | 4 | `documentos/services.py` (`reemplazar`), `documentos/models.py`, `documentos/querysets.py` (`VersionQuerySet`) | `test_e4_reemplazar_crea_una_version_nueva_y_conserva_la_anterior`, `test_el_cliente_recibe_siempre_la_version_vigente_y_el_administrador_cualquiera`, `test_las_versiones_no_se_editan_ni_se_borran` | Verificado |
| DOC-09 | Paginación y sin consultas N+1 | 4 y 5 | `panel/views/documentos.py` (`CarpetaDetalle`, `ClientePapelera`), `panel/views/clientes.py` | `test_la_lista_de_documentos_pagina_de_a_25_sin_consultas_por_fila`, `test_la_pestana_documentos_cuenta_los_documentos_sin_consultas_por_carpeta` | Verificado en el panel; los listados del portal son de la Etapa 5 |

## Portal del cliente (CLI)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| CLI-01 | Inicio del portal según la referencia visual: saludo, tarjeta de empresa, buscador, carpetas y recientes | 5 | — | — | Pendiente |
| CLI-02 | Vista de carpeta | 5 | — | — | Pendiente |
| CLI-03 | Búsqueda por título | 5 | — | — | Pendiente |
| CLI-04 | Mi cuenta | 5 | — | — | Pendiente |
| CLI-05 | Solo lectura aplicada en el servidor | 5 | — | — | Pendiente |
| CLI-06 | Estado vacío con contacto | 5 | — | — | Pendiente |
| CLI-07 | Cualquier documento en dos clics | 5 | — | — | Pendiente |
| CLI-08 | Ficha del documento: migas, ícono por tipo, datos y botones Descargar y Ver en pantalla; sin visor incrustado | 5 | — | — | Pendiente |

## Auditoría (AUD)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| AUD-01 | Eventos registrados | 2 a 6 | `auditoria/models.py`, `auditoria/services.py`; llamadas en `cuentas/services.py` y `cuentas/dos_factores.py` | `auditoria/tests/test_auditoria.py` y las pruebas de `cuentas` que comprueban cada evento | En curso: verificados los eventos de acceso, bloqueo, enlaces, contraseñas y 2FA; las altas y cambios de empresas, usuarios y carpetas; y los de documentos (subida, reemplazo, edición, movimiento, eliminación, restauración, purga, vista y descarga, en `documentos/tests/`). Solicitudes en la Etapa 6 |
| AUD-02 | Contenido de cada evento, sin secretos | 2 a 6 | `auditoria/services.py` (`registrar`) | `test_registrar_guarda_actor_empresa_objeto_e_ip`, `test_el_rut_intentado_se_guarda_normalizado_solo_si_es_un_rut_valido` | En curso: se comprueba con cada evento nuevo |
| AUD-03 | Solo agregar; retención y `depurar_auditoria` | 3 | `auditoria/models.py` (`SoloAgregar`, `depurar`), `auditoria/management/commands/depurar_auditoria.py` | `test_los_eventos_no_se_editan_ni_se_borran`, `panel/tests/test_auditoria.py` (`test_depurar_auditoria_*`, `test_con_la_retencion_por_defecto_*`, `test_restar_meses_*`) | Verificado. Programar el comando en el cron es de la Etapa 8 |

## Seguridad (SEG)

| Código | Requisito | Etapa | Archivos | Prueba | Estado |
| --- | --- | --- | --- | --- | --- |
| SEG-01 | Configuración de producción y `check --deploy` | 7 y 8 | — | — | Pendiente |
| SEG-02 | CSP y encabezados | 1 y 7 | `config/settings/base.py` (`SECURE_CSP`), `templates/base.html` | `config/tests/test_configuracion.py` (`test_encabezados_de_seguridad`), `core/tests/test_vistas.py` (`test_las_plantillas_no_llevan_estilos_ni_scripts_en_linea`) | En curso: CSP activa; `Permissions-Policy` y revisión completa en la Etapa 7 |
| SEG-03 | CSRF en formularios y HTMX | 2 | `templates/base.html` (`hx-headers`), `core/views.py` (`csrf_fallido`), `templates/403_csrf.html` | `config/tests/test_urls_privadas.py` (`test_un_formulario_sin_token_csrf_responde_403`, `test_ninguna_vista_esta_exenta_de_csrf`) | Verificado |
| SEG-04 | Mixins de rol y prueba de todas las URL | 3 y 7 | `core/mixins.py`, `panel/views/base.py`, `empresas/querysets.py` | `config/tests/test_urls_privadas.py`, `panel/tests/test_carpetas.py` (`test_visibles_para_*`, `test_una_carpeta_solo_se_alcanza_*`), `panel/tests/test_usuarios.py` (`test_un_usuario_solo_se_alcanza_*`) | En curso: mixins, recorrido de URL con identificadores reales, y carpetas, documentos y versiones por empresa (`documentos/tests/test_aislamiento.py`) verificados; revisión general en la Etapa 7 |
| SEG-05 | UUID en las URL y 404 para lo ajeno | 4 | `documentos/models.py`, `panel/urls.py`, `portal/urls.py` | `documentos/tests/test_aislamiento.py`, `test_una_version_solo_se_alcanza_bajo_su_documento_y_su_empresa` | Verificado |
| SEG-06 | Autoescape y textos editables sin HTML | 6 | — | — | Pendiente |
| SEG-07 | Archivos subidos nunca ejecutados ni servidos como estáticos | 4 y 8 | `documentos/validacion.py`, `documentos/subida.py`, `documentos/almacenamiento.py` (`entregar`: `nosniff` y CSP `sandbox`), `documentos/comprobaciones.py` | `documentos/tests/test_validacion.py`, `test_las_comprobaciones_detectan_una_configuracion_insegura`, `test_descargar_entrega_el_archivo_como_adjunto_y_registra_el_evento` | En curso: validación, nombres saneados y entrega aislada verificados; el límite de tamaño en el servidor web y el proxy es de la Etapa 8 |
| SEG-08 | Secretos fuera del código y credenciales mínimas | 1 y 8 | `config/env.py`, `config/settings/prod.py`, `.env.example`, `.gitignore` | `config/tests/test_configuracion.py` (`test_prod_se_niega_*`, `test_la_clave_de_ejemplo_es_la_de_env_example`) | En curso: configuración verificada; credenciales del almacenamiento en la Etapa 8 |
| SEG-09 | Versiones fijadas y `pip-audit` en CI | 1 | `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` (trabajo `auditoria`) | Trabajo `auditoria` de la CI | Verificado manual: resultado de la CI |
| SEG-10 | Logs sin datos sensibles | 7 | `core/logs.py` (`ocultar_tokens`), `auditoria/services.py` | `test_los_logs_no_registran_el_token_de_los_enlaces`, `test_ni_el_token_ni_la_contrasena_quedan_en_la_auditoria` | En curso: logs de la aplicación verificados; logs de Gunicorn y del proxy en la Etapa 8 |
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
| Componentes de la sección 9 y página de referencia solo en desarrollo | `templates/componentes/`, `templates/base_aplicacion.html`, `core/referencia.py`, `core/urls_dev.py`, `static/js/app.js` | `core/tests/test_vistas.py` (`test_la_referencia_*`, `test_el_campo_*`, `test_el_dialogo_*`, `test_cada_tipo_de_archivo_*`, `test_los_id_*`) | Verificado. Aspecto revisado con capturas a 360, 768 y 1280 px el 09-10-2026. La zona de subida con progreso se agregó en la Etapa 4 |
| Tokens de diseño de la sección 9, Inter autoalojada y contraste AA | `static_src/css/app.css`, `static/fonts/` | `core/tests/test_diseno.py` | Verificado |
| `docker compose up` desde cero con migraciones en base vacía | `Dockerfile`, `compose.yaml`, `docker/arrancar-dev.sh` | Trabajo `arranque` de la CI y clon limpio local | Verificado manual |

## Pruebas de seguridad obligatorias (sección 12.2)

| # | Prueba | Etapa | Dónde | Estado |
| --- | --- | --- | --- | --- |
| 1 | URL privadas recorriendo el URLconf | 2 en adelante | `config/tests/test_urls_privadas.py` | Verificado para las URL existentes. Desde la Etapa 3 el panel se recorre además con UUID reales de empresa, usuario y carpeta (propios y ajenos), por GET y POST, comprobando que nada cambia en la base. Una ruta nueva del panel debe sumarse a la lista `PANEL` o la prueba falla |
| 2 | Un cliente de A no accede a nada de B | 4 y 5 | `documentos/tests/test_aislamiento.py` (`test_prueba_2_*`) | En curso: ver y descargar con el UUID correcto (404, sin evento y sin leer el almacenamiento), versiones anteriores y consultas `visibles_para` verificados. Listar y buscar en las pantallas del portal se prueban en la Etapa 5, cuando existan |
| 3 | Un cliente no modifica documentos con POST hechos a mano | 4 y 5 | `config/tests/test_urls_privadas.py` (`test_un_cliente_recibe_404_en_el_panel_con_identificadores_reales_y_nada_cambia`, `test_prueba_3_*`) | Verificado sobre todas las rutas: 404 en las del panel con UUID reales, propios y ajenos, y 405 en las de ver y descargar; nada cambia en la base ni en el almacenamiento (se comparan las filas y el SHA-256 de cada objeto). En la Etapa 5 se suman las rutas nuevas del portal |
| 4 | Documento en la papelera inaccesible para el cliente | 4 y 5 | `documentos/tests/test_aislamiento.py` (`test_prueba_4_*`) | En curso: 404 en ver y descargar, fuera de `visibles_para` y borrado tras la purga, verificados. Que no aparezca en los listados del portal se prueba en la Etapa 5 |
| 5 | Usuario o empresa desactivados pierden el acceso en la petición siguiente | 2 y 3 | `cuentas/tests/test_corte.py`; por el panel: `test_e6_desactivar_la_empresa_desde_el_panel_corta_la_sesion_abierta`, `test_desactivar_al_usuario_desde_el_panel_corta_su_sesion_y_revoca_sus_enlaces` | Verificado, también por el camino real del administrador (E6) |
| 6 | Bloqueo tras los intentos configurados y desbloqueo por el administrador | 2 y 3 | `cuentas/tests/test_acceso_bloqueo.py` (`test_el_administrador_desbloquea_con_el_boton_de_la_lista_de_usuarios`) | Verificado, con el botón real |
| 7 | Mensajes idénticos para un RUT existente y uno inexistente | 2 | `test_acceso.py`, `test_recuperacion.py` (`test_la_respuesta_es_identica_*`) | Verificado |
| 8 | Enlaces de un solo uso, que expiran y fallan si se alteran | 2 y 3 | `cuentas/tests/test_enlaces.py`; desde el panel: `test_generar_un_enlace_nuevo_revoca_el_anterior_y_es_de_un_solo_uso` | Verificado |
| 9 | Un administrador sin 2FA verificado no entra al panel | 2 y 3 | `cuentas/tests/test_dos_factores.py`, `test_un_administrador_sin_segundo_factor_no_usa_ninguna_ruta_del_panel` | Verificado sobre todas las rutas del panel |
| 10 | Archivos inválidos rechazados | 4 | `documentos/tests/test_validacion.py`, `documentos/tests/test_subida.py` (`test_prueba_10_*`) | Verificado: ejecutable y HTML renombrados como `.pdf`, vacío, sobre el límite, SVG y DOCM, más Office antiguo, ZIP y otros; por la vista real de subida, con su motivo y sin dejar filas, objetos ni eventos |
| 11 | Clave de almacenamiento sin nombre ni RUT | 4 y 8 | `documentos/tests/test_almacenamiento.py` (`test_prueba_11_*`, `test_la_base_rechaza_una_clave_con_otra_forma`) | En curso: clave verificada con el almacenamiento local y con S3 emulado. "El objeto no es accesible sin firma" en staging es una verificación manual de la Etapa 8, con `comprobar_almacenamiento --firma` |
| 12 | Formulario sin token CSRF responde 403; campo trampa y límite por IP | 2, 3 y 6 | `test_un_formulario_sin_token_csrf_responde_403`, `test_ninguna_ruta_del_panel_acepta_un_post_sin_token_csrf` | En curso: CSRF verificado, incluidas todas las rutas del panel; campo trampa y límite de envíos en la Etapa 6 |

## Escenarios de aceptación (sección 12.3)

| # | Escenario | Etapa | Dónde | Estado |
| --- | --- | --- | --- | --- |
| E2 | Crear empresa con carpetas base y usuario, copiar el enlace, definir contraseña y ver el portal vacío | 3 | `test_e2_crear_cliente_con_carpetas_usuario_y_enlace_hasta_el_portal_vacio` | Verificado con prueba automática. El recorrido en el navegador con un administrador real y su 2FA queda para la revisión del responsable (README) |
| E6 | Desactivar una empresa corta al usuario con sesión abierta | 3 | `test_e6_desactivar_la_empresa_desde_el_panel_corta_la_sesion_abierta` | Verificado |
| E3 | Tres archivos, uno inválido; el cliente descarga uno y queda en la auditoría | 4 y 5 | `test_e3_tres_archivos_uno_invalido_*`, `test_descargar_entrega_el_archivo_como_adjunto_y_registra_el_evento` | En curso: subida, rechazo con motivo, descarga y auditoría verificados. "Recientes" y la etiqueta "Nuevo" son del portal (Etapa 5) |
| E4 | Reemplazo: el cliente descarga la versión nueva y el administrador ve ambas | 4 | `test_e4_reemplazar_crea_una_version_nueva_y_conserva_la_anterior`, `test_el_cliente_recibe_siempre_la_version_vigente_y_el_administrador_cualquiera` | Verificado |
| E5 | Eliminar y restaurar: el cliente deja de ver el documento y vuelve a verlo | 4 y 5 | `test_e5_eliminar_envia_a_la_papelera_y_restaurar_lo_devuelve`, `test_prueba_4_un_documento_en_la_papelera_no_es_accesible_para_el_cliente` | En curso: verificado por los endpoints de ver y descargar; los listados del portal, en la Etapa 5 |
| E1, E7 y E8 | Solicitudes, restablecimiento y accesibilidad | 6 y 7 | — | Pendiente (E7 tiene su prueba desde la Etapa 2) |
| 13 | Con el correo fallando, la solicitud se guarda | 6 | — | Pendiente |
| 14 | Un nombre con `<script>` se muestra escapado | 6 | — | Pendiente |
