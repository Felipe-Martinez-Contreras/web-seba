# Seguridad

Amenazas principales, el control que mitiga cada una y las limitaciones conocidas. Se completa etapa a etapa; la revisión general es de la Etapa 7. Este documento cubre lo construido hasta la Etapa 4 (cuentas, acceso, gestión de clientes y documentos).

## 1. Amenazas y controles

| Amenaza | Control | Dónde | Prueba |
| --- | --- | --- | --- |
| Adivinar contraseñas por fuerza bruta | Bloqueo de 15 minutos tras 5 fallos por RUT e IP en 15 minutos, y tras 30 fallos por IP. Durante el bloqueo se rechaza incluso la contraseña correcta | `cuentas/bloqueo.py`, `cuentas/services.py` | `cuentas/tests/test_bloqueo.py`, `test_acceso_bloqueo.py` |
| Evadir el bloqueo falsificando `X-Forwarded-For` | El encabezado solo se lee si la conexión viene de una red de `PROXY_CONFIANZA_REDES`, y de derecha a izquierda | `core/ip.py` | `core/tests/test_ip.py`, `test_cambiar_x_forwarded_for_no_evita_el_bloqueo` |
| Averiguar qué RUT tienen cuenta (por el mensaje) | Mismo mensaje, mismo código y misma página para todo fallo de acceso; pantalla fija en la recuperación | `cuentas/views.py` | `test_la_respuesta_es_identica_*` |
| Averiguar qué RUT tienen cuenta (por el tiempo) | Una verificación Argon2 por intento, exista o no la cuenta; el correo de recuperación sale de la petición | `cuentas/backends.py`, `core/tareas.py` | `test_cada_intento_ejecuta_exactamente_una_verificacion_de_contrasena`, `test_cada_intento_fallido_hace_las_mismas_consultas`, `test_el_envio_ocurre_fuera_de_la_peticion` y la medición de la sección 3 |
| Averiguar qué RUT tienen cuenta (por el bloqueo) | El bloqueo cuenta igual para un RUT sin cuenta | `cuentas/bloqueo.py` | `test_un_rut_inexistente_se_bloquea_igual_y_con_el_mismo_mensaje` |
| Usar la sesión de alguien que ya no debe entrar | El backend comprueba cuenta y empresa en cada petición, y la sesión se elimina | `cuentas/backends.py`, `cuentas/middleware.py` | `cuentas/tests/test_corte.py` |
| Robo de la contraseña de un administrador | 2FA obligatorio (TOTP) para el panel, "Mi cuenta" y el admin de Django | `core/mixins.py`, `cuentas/dos_factores.py` | `test_un_administrador_sin_2fa_verificado_no_entra_al_panel` |
| Tomar la cuenta de un administrador que aún no tiene 2FA | El 2FA solo se enrola en la sesión que acaba de usar un enlace de activación o de restablecimiento, y por 30 minutos | `cuentas/dos_factores.py` | `test_quien_entra_solo_con_la_contrasena_no_puede_enrolar_su_dispositivo`, `test_el_permiso_no_pasa_a_otra_sesion_ni_sobrevive_al_cierre` |
| Fuerza bruta sobre el código de 6 dígitos | Espera creciente de `django-otp` tras cada fallo (1, 2, 4… segundos); un código no se acepta dos veces | `cuentas/dos_factores.py` | `test_tras_un_codigo_errado_hay_que_esperar`, `test_un_codigo_totp_no_se_puede_reutilizar` |
| Reutilizar o falsificar un enlace de activación o recuperación | Token aleatorio de 256 bits, guardado solo como SHA-256; un solo uso; vence a las 72 h o a 1 h; un enlace nuevo revoca los anteriores | `cuentas/services.py`, `cuentas/models.py` (`EnlaceAcceso`) | `cuentas/tests/test_enlaces.py` |
| Enlace de recuperación que apunta al sitio de un atacante | La URL se arma con `SITIO_URL`, nunca con el encabezado `Host` | `cuentas/services.py` | `test_el_enlace_usa_la_url_configurada_y_no_el_encabezado_host` |
| Usar el formulario de recuperación para enviar correo en masa | 3 solicitudes por hora por RUT y 10 por IP, sin avisar | `cuentas/services.py` | `test_limite_silencioso_por_rut`, `test_limite_silencioso_por_ip` |
| Cambiar el correo de una cuenta para recibir su recuperación | "Mi cuenta" es de solo lectura; el correo y el RUT los cambia solo un administrador | `cuentas/views.py` (`MiCuenta`) | `test_el_cliente_no_puede_cambiar_su_correo_ni_su_rut_con_un_post_hecho_a_mano` |
| Sesión robada usada para adivinar la contraseña actual | 5 fallos seguidos en "Cambiar contraseña" cierran la sesión | `cuentas/views.py` (`MiCuenta`) | `test_varios_fallos_con_la_contrasena_actual_cierran_la_sesion` |
| Sesión que sigue viva tras cambiar la contraseña | Las demás sesiones dejan de valer en su petición siguiente | Django (`get_session_auth_hash`), `cuentas/services.py` | `test_cambiar_la_contrasena_cierra_las_demas_sesiones_y_conserva_la_actual`, `test_restablecer_cierra_la_sesion_abierta_en_otro_dispositivo` |
| Fijación de sesión | El identificador rota al iniciar sesión; cierre solo por POST | Django (`login`), `cuentas/views.py` | `test_el_cliente_entra_al_portal_y_queda_registrado`, `test_el_cierre_de_sesion_es_solo_por_post` |
| Peticiones falsificadas desde otro sitio (CSRF) | Token en todos los formularios y en el encabezado de HTMX; ninguna vista exenta | `templates/base.html`, `core/views.py` (`csrf_fallido`) | `test_un_formulario_sin_token_csrf_responde_403`, `test_ninguna_vista_esta_exenta_de_csrf` |
| Vista privada publicada sin control de acceso | Mixins de rol únicos; una prueba recorre todo el URLconf | `core/mixins.py` | `config/tests/test_urls_privadas.py` |
| Enumerar usuarios por ID en las URL | Las URL usan `Usuario.uuid`; el ID entero no sale de la aplicación | `cuentas/models.py`, `panel/urls.py` | `test_el_desbloqueo_exige_post_y_un_usuario_de_esa_empresa` |
| Un cliente usa las rutas del panel, con UUID reales o con POST hechos a mano | Todas las vistas del panel heredan de `AdministradorMixin`: responden 404 antes de ejecutar nada | `core/mixins.py`, `panel/views/` | `test_un_cliente_recibe_404_en_el_panel_con_identificadores_reales_y_nada_cambia` |
| Actuar sobre un usuario o una carpeta desde la URL de otra empresa | Usuarios y carpetas se buscan siempre dentro de la empresa de la URL; si no calzan, 404 | `panel/views/base.py` | `test_un_usuario_solo_se_alcanza_bajo_su_propia_empresa`, `test_una_carpeta_solo_se_alcanza_bajo_su_propia_empresa` |
| Que el administrador conozca o fije la contraseña de un cliente | La cuenta se crea sin contraseña utilizable; el administrador solo entrega un enlace de un solo uso | `cuentas/services.py` (`crear_cliente`, `entregar_enlace`) | `test_e2_crear_cliente_con_carpetas_usuario_y_enlace_hasta_el_portal_vacio` |
| Recuperar un enlace ya generado desde la base, la sesión o la auditoría | El enlace se muestra una sola vez, en la respuesta que lo genera, con `no-store`; se guarda solo el SHA-256 del token | `panel/views/usuarios.py`, `cuentas/services.py` | `test_e2_*`, `test_generar_un_enlace_nuevo_revoca_el_anterior_y_es_de_un_solo_uso` |
| Un enlace entregado antes revive al reactivar la cuenta | Desactivar una cuenta revoca sus enlaces sin usar; con la empresa inactiva ningún enlace vale | `cuentas/services.py` (`cambiar_estado_cliente`), `cuentas/models.py` (`esta_vigente`) | `test_desactivar_al_usuario_desde_el_panel_*`, `test_e6_*` |
| El panel afirma que envió un correo que no salió | El resultado del envío se muestra tal cual: enviado, fallido o no configurado | `core/correo.py`, `panel/templates/panel/usuario_enlace.html` | `test_si_el_correo_falla_el_panel_lo_informa_y_el_enlace_igual_sirve` |
| HTML o scripts en los datos de un cliente | Autoescape en todas las plantillas; las notas internas se muestran con saltos de línea y sin HTML | Plantillas de `panel/` | `test_un_nombre_con_script_se_muestra_escapado` |
| Las notas internas llegan al cliente | Solo se muestran en la ficha del panel | `panel/templates/panel/_cliente_cabecera.html` | `test_las_notas_internas_solo_aparecen_en_el_panel` |
| Secretos en los logs o en la auditoría | El log oculta el token de las rutas de enlace; la auditoría guarda textos fijos y solo RUT válidos | `core/logs.py`, `auditoria/services.py` | `test_los_logs_no_registran_el_token_de_los_enlaces`, `test_ni_el_token_ni_la_contrasena_quedan_en_la_auditoria`, `test_la_contrasena_escrita_en_el_campo_del_rut_no_queda_en_la_auditoria` |
| Alterar o borrar la auditoría | El modelo rechaza editar y borrar; en el admin de Django es de solo lectura | `auditoria/models.py`, `auditoria/admin.py` | `test_los_eventos_no_se_editan_ni_se_borran`, `test_el_listado_es_de_solo_lectura_y_pagina_sin_consultas_por_fila` |
| Acortar la auditoría sin dejar rastro | El único borrado es el de la retención, por comando en el servidor, y deja un evento propio | `auditoria/management/commands/depurar_auditoria.py` | `test_depurar_auditoria_borra_solo_lo_anterior_a_la_retencion` |
| Contraseñas débiles o filtradas de la base | Argon2id; mínimo 12 caracteres y validadores de Django | `config/settings/base.py` | `test_contrasenas_con_argon2_y_minimo_de_12_caracteres`, `test_la_contrasena_nueva_pasa_por_los_validadores` |
| Un cliente ve o descarga documentos de otra empresa con el UUID correcto | Los documentos se buscan con `visibles_para(usuario)`: solo los de su empresa. Uno ajeno responde el mismo 404 que uno inexistente, sin evento y sin tocar el almacenamiento | `documentos/querysets.py`, `portal/views.py` | `test_prueba_2_*` (`documentos/tests/test_aislamiento.py`) |
| Un cliente accede a una versión anterior | El portal no tiene ruta con UUID de versión: entrega siempre la vigente | `portal/urls.py`, `documentos/querysets.py` | `test_prueba_2_un_cliente_no_ve_versiones_anteriores_ni_de_su_propia_empresa` |
| Un cliente accede a un documento eliminado | `visibles_para` excluye la papelera; en la papelera tampoco lo descarga un administrador | `documentos/querysets.py`, `panel/views/documentos.py` | `test_prueba_4_*` |
| Un cliente modifica documentos con peticiones hechas a mano | Subir, editar, mover, reemplazar, eliminar y restaurar solo existen en el panel (404 por rol); ver y descargar solo admiten GET | `core/mixins.py`, `panel/views/documentos.py` | `test_un_cliente_recibe_404_en_el_panel_con_identificadores_reales_y_nada_cambia`, `test_prueba_3_*` |
| Actuar sobre un documento o una versión desde la URL de otra empresa u otro documento | Documento dentro de la empresa de la URL y versión dentro de ese documento; si no calzan, 404 | `panel/views/documentos.py` | `test_una_version_solo_se_alcanza_bajo_su_documento_y_su_empresa`, `test_no_se_sube_a_una_carpeta_por_la_url_de_otra_empresa` |
| Mover un documento a otra empresa | El formulario solo acepta carpetas de la misma empresa y el servicio lo vuelve a comprobar | `documentos/forms.py`, `documentos/services.py` (`mover`) | `test_mover_solo_entre_carpetas_de_la_misma_empresa` |
| Subir un ejecutable, HTML, SVG o un archivo con macros, renombrado | Lista blanca de extensiones, tipo real por firma de bytes, estructura OOXML y detección de macros. El tipo que declara el navegador no se usa | `documentos/validacion.py` | `documentos/tests/test_validacion.py`, `test_prueba_10_*` |
| Archivo comprimido malicioso (bomba ZIP, entidades XML) | Tope de entradas y de tamaño declarado; de `[Content_Types].xml` se lee como máximo 1 MB y se rechaza si declara DOCTYPE o entidades | `documentos/validacion.py` | `test_un_paquete_que_declara_demasiado_contenido_se_rechaza`, `test_un_zip_corrupto_o_con_entidades_xml_se_rechaza_como_danado` |
| Agotar la memoria o el disco con subidas enormes | Tope por petición antes de leer el cuerpo; 25 MB por archivo; los archivos grandes van a disco temporal y se procesan por trozos | `documentos/subida.py`, `documentos/validacion.py` | `test_una_peticion_enorme_se_corta_antes_de_leer_el_archivo`, `test_prueba_10_un_archivo_sobre_el_limite_se_rechaza` |
| Nombre de archivo malicioso (rutas, saltos de línea, caracteres invisibles) | El nombre se sanea al subir y nunca forma parte de una ruta; la descarga lo codifica según RFC 6266 | `documentos/validacion.py` (`sanear_nombre`), `documentos/services.py` | `test_el_nombre_original_se_sanea_*`, `test_el_nombre_descargado_conserva_tildes_y_enie_segun_rfc_6266` |
| Datos identificables en las rutas del almacenamiento | Clave `docs/<uuid_empresa>/<uuid_version>`, sin nombre, extensión ni RUT. La exige el almacenamiento y una restricción de la base. En S3 el objeto no lleva metadatos | `documentos/almacenamiento.py`, `documentos/models.py` | `test_prueba_11_*`, `test_la_base_rechaza_una_clave_con_otra_forma`, `test_en_s3_el_objeto_no_lleva_metadatos_con_el_nombre` |
| Leer archivos fuera del almacenamiento con una clave manipulada | Ninguna operación acepta una clave con otra forma | `documentos/almacenamiento.py` | `test_ninguna_operacion_acepta_una_clave_con_otra_forma` |
| Un archivo subido ejecuta código en el dominio de la aplicación | Nunca se sirven como estáticos. Se entregan con el tipo detectado, `nosniff` y `Content-Security-Policy: sandbox`; solo PDF, JPG y PNG se abren en el navegador | `documentos/almacenamiento.py` (`entregar`), `documentos/comprobaciones.py` | `test_descargar_entrega_el_archivo_como_adjunto_y_registra_el_evento`, `test_ver_abre_en_el_navegador_solo_pdf_jpg_y_png`, `test_las_comprobaciones_detectan_una_configuracion_insegura` |
| Un enlace de descarga compartido o filtrado | No hay enlaces permanentes: toda entrega exige sesión. Con S3, la URL firmada vence a los 120 segundos como máximo y fija tipo y disposición | `documentos/almacenamiento.py` | `test_con_s3_la_entrega_es_una_redireccion_a_una_url_firmada_de_dos_minutos`, `test_la_vigencia_de_la_url_nunca_supera_los_dos_minutos` |
| Descargas sin rastro | El evento y la entrega van en una transacción: sin evento no hay entrega | `documentos/services.py` (`entregar`) | `test_si_la_auditoria_falla_no_se_entrega_el_archivo`, `test_si_falta_el_archivo_responde_404_y_no_queda_evento` |
| Archivos sin registro, o registros sin archivo | Si la base falla tras guardar, el objeto se borra. La purga borra primero los objetos y después las filas | `documentos/services.py` | `test_si_la_base_falla_el_objeto_guardado_se_borra`, `test_si_la_purga_falla_a_medias_la_siguiente_ejecucion_la_termina` |
| Perder documentos al eliminar una carpeta | Una carpeta con documentos, también en la papelera, no se elimina: lo impiden el servicio y la base (`PROTECT`) | `empresas/services.py` (`eliminar_carpeta`), `documentos/models.py` | `test_una_carpeta_con_documentos_no_se_elimina_*`, `test_los_documentos_de_la_papelera_tambien_impiden_eliminar_la_carpeta`, `test_la_base_protege_la_carpeta_aunque_se_salte_el_servicio` |
| Alterar un archivo ya publicado | Las versiones no se editan: reemplazar crea otra. Se guarda el SHA-256 de cada una | `documentos/models.py` | `test_las_versiones_no_se_editan_ni_se_borran` |

## 2. Cómo se obtiene la IP del cliente

1. Sin `PROXY_CONFIANZA_REDES`, la IP es la de la conexión (`REMOTE_ADDR`) y ningún encabezado se lee.
2. Con redes configuradas, el encabezado (`X-Forwarded-For` por defecto) solo cuenta si la conexión viene de una de esas redes.
3. La lista se recorre de derecha a izquierda, saltando los proxies de confianza. La primera dirección que no lo es, es el cliente. Lo que esté más a la izquierda lo pudo escribir el cliente y no se usa.
4. Un valor que no es una IP hace volver a la dirección de la conexión.

Producción no arranca si `PROXY_CONFIANZA_REDES` no está declarada, aunque sea vacía. El valor concreto depende del hosting y se fija en la Etapa 8.

## 3. Medición de tiempos de respuesta

Las pruebas automáticas comprueban la causa (una sola verificación de contraseña, mismas consultas, envío fuera de la petición), porque medir el reloj en la CI no es fiable. Además se midió a mano el 09-10-2026, en el contenedor de desarrollo, con el cliente de pruebas de Django contra la base de desarrollo y los límites de intentos levantados.

Acceso, 25 intentos por caso:

| Caso | Mediana | Mínimo | Máximo |
| --- | --- | --- | --- |
| RUT existente, contraseña errada | 150,8 ms | 143,1 ms | 181,3 ms |
| RUT inexistente | 153,1 ms | 144,3 ms | 195,9 ms |
| RUT con dígito verificador inválido | 143,1 ms | 132,4 ms | 203,9 ms |

El RUT con dígito inválido tarda unos milisegundos menos porque no consulta la base. No revela nada: cualquiera puede calcular un dígito verificador.

Recuperación, 10 solicitudes por caso, alternadas y con 5 segundos entre una y otra:

| Caso | Mediana | Mínimo | Máximo |
| --- | --- | --- | --- |
| RUT existente con correo | 26,0 ms | 19,5 ms | 31,8 ms |
| RUT inexistente | 25,5 ms | 23,3 ms | 28,0 ms |

Una primera versión lanzaba el hilo de envío de inmediato y esta misma medición lo delató: 27,7 ms contra 16,8 ms, porque el hilo competía por la CPU con la petición. Por eso el hilo ahora parte entre 2 y 4 segundos después.

La medición es local y sobre un equipo de desarrollo. Debe repetirse en staging en la Etapa 7.

## 4. Limitaciones conocidas

- **Un correo de recuperación puede perderse.** El envío ocurre en un hilo del mismo proceso, entre 2 y 4 segundos después de la petición. Si el proceso se reinicia en ese intervalo o durante el envío, el correo no sale y nadie lo reintenta. Cómo queda registrado:
    - Siempre existe el evento "Recuperación solicitada".
    - Si el reinicio ocurre antes de crear el enlace, no hay enlace ni evento "Correo de recuperación".
    - Si ocurre durante el envío, el enlace queda con envío "pendiente", nunca "enviada".
    - La persona ve la misma pantalla de siempre y puede volver a pedirlo.
- **Canal lateral residual en la recuperación.** El trabajo de envío carga el servidor unos segundos después de la solicitud. Quien pudiera medir esa carga con otras peticiones podría, en teoría, inferir que la cuenta existe. Lo acotan la espera al azar y el límite de 3 solicitudes por hora por RUT. Eliminarlo del todo exigiría una cola de trabajos, que está fuera del MVP (sección 5 de la especificación).
- **Los contadores de intentos no son atómicos.** Viven en la caché de base de datos. Con peticiones simultáneas pueden colarse uno o dos intentos de más antes del bloqueo.
- **El límite por IP no agrupa IPv6.** Un atacante con un bloque IPv6 puede rotar direcciones. El límite por RUT e IP sigue aplicando a cada dirección; el límite por IP sola pierde eficacia.
- **Una red compartida puede bloquearse entera.** Varias personas de una misma empresa salen con la misma IP: 30 fallos entre todas, en 15 minutos, bloquean esa IP. Se desbloquea con `desbloquear_acceso --ip`.
- **Los logs del servidor web y del proxy.** La aplicación oculta el token de las rutas de enlace en sus propios logs. Gunicorn y el proxy de producción escriben los suyos: su formato se configura en la Etapa 8 para que no registren esa ruta completa.
- **El admin de Django no deja eventos de auditoría propios.** Lo que el superusuario técnico cambie ahí (por ejemplo, el correo o el estado de un usuario) queda en el historial del admin de Django, no en `EventoAuditoria`. Es una herramienta de soporte, no la interfaz de trabajo (ADM-12).
- **El corte de sesión no deja evento.** Cuando una sesión se elimina porque la cuenta o la empresa se desactivó, no se registra un evento aparte; lo que queda en la auditoría es la desactivación misma, con quién la hizo.
- **El enlace de activación pasa por la pantalla del administrador.** Quien vea esa pantalla, o reciba el enlace por un canal inseguro, puede definir la contraseña de la cuenta antes que su dueño. Lo acotan el uso único, el vencimiento (72 horas, o 1 hora si es de restablecimiento) y que generar otro enlace revoca el anterior. Si la persona avisa que su enlace "ya fue usado" sin haberlo usado ella, hay que desactivar la cuenta y revisar su actividad.
- **El enlace también queda en el portapapeles y en el historial del canal por donde se envíe.** La aplicación no lo puede controlar; el manual del administrador lo advierte.
- **El correo de activación se envía dentro de la petición.** Si el servidor de correo no responde, la pantalla tarda hasta 10 segundos y luego informa el fallo. El enlace se muestra igual.
- **Todos los administradores tienen permisos completos** (sección 0). Cualquiera de ellos puede desactivar clientes, generar enlaces y leer la auditoría completa. No hay segregación entre administradores.
- **Un administrador bloqueado no se desbloquea desde el panel.** Se usa `desbloquear_acceso`, en el servidor, o se espera a que venza el bloqueo (15 minutos).
- **La retención borra de verdad.** `depurar_auditoria` elimina los eventos más antiguos que `AUDITORIA_RETENCION_MESES`. Un valor mal puesto (por ejemplo, 1) borra casi todo en la siguiente ejecución; los respaldos de la base (Etapa 8) son la única vuelta atrás.
- **Purgar la papelera no borra el archivo al instante si el bucket tiene versionado.** SEG-11 pide activar el versionado del bucket, como respaldo. Con él, cuando `purgar_papelera` borra un objeto, el proveedor solo le pone una marca de borrado: el contenido queda como versión antigua hasta que la regla de expiración del bucket lo elimina, entre 30 y 90 días después según se configure. Consecuencias:
    - Para la aplicación el documento ya no existe (ni filas ni objeto visible), pero quien tenga acceso de administración al bucket todavía puede recuperarlo durante ese plazo.
    - El plazo real de eliminación de un documento es: hasta 30 días en la papelera, más la espera hasta la siguiente ejecución de `purgar_papelera`, más la expiración de versiones antiguas del bucket.
    - **Solicitudes de eliminación de datos** (Ley 19.628 y Ley 21.719): ese es el plazo que hay que informar. Si una solicitud exige borrar antes, hay que eliminar a mano las versiones antiguas de esos objetos en el bucket, además de purgar; las claves están en la tabla de versiones hasta el momento de la purga, así que deben anotarse antes. El procedimiento queda para `DESPLIEGUE.md` (Etapa 8), cuando exista el bucket.
    - Lo mismo vale para los respaldos de la base de datos: las filas borradas siguen en los respaldos hasta que vencen (SEG-11).
    - Con el almacenamiento local no hay versionado: el archivo se borra del disco en la purga.
- **El almacenamiento S3 solo se probó contra un emulador.** Las pruebas automáticas usan `moto` dentro del proceso, y la descarga por URL firmada se revisó además por HTTP contra `moto_server`. El emulador rechaza una petición sin firma, pero **no valida la firma ni el vencimiento**: el 11-10-2026 se comprobó que sigue sirviendo el archivo con la firma alterada y 125 segundos después de emitida la URL. Por eso el vencimiento de 2 minutos está verificado solo como parámetro de la URL (`X-Amz-Expires=120`); que el proveedor lo haga cumplir se comprueba contra el bucket real con `comprobar_almacenamiento --firma`, antes de cargar documentos (Etapa 8). Ese comando verifica que el objeto no se lea sin firma (prueba 11), que una firma alterada se rechace y que la URL vencida deje de servir.
- **Con S3, el evento de auditoría registra la emisión de la URL firmada.** La aplicación no sabe si la descarga terminó, ni cuántas veces se usó la URL dentro de sus 120 segundos.
- **La URL firmada es un permiso al portador durante 120 segundos.** En "Ver" queda en la barra de direcciones y en el historial de esa pestaña. Quien la copie dentro de ese plazo puede descargar el archivo sin sesión. La respuesta que la entrega lleva `no-store`.
- **`Content-Security-Policy: sandbox` solo cubre la entrega local.** En la entrega por S3 los encabezados los pone el bucket, que vive en otro dominio: un archivo abierto ahí no comparte origen con la aplicación ni recibe sus cookies. En Edge se comprobó que el visor de PDF funciona con `sandbox`; en Firefox y Safari queda para la revisión de navegadores de la Etapa 7 (RNF-03).
- **No hay antivirus** (fuera de alcance, sección 16). La validación comprueba el formato, no que el contenido sea inofensivo: un PDF válido puede traer contenido malicioso para el lector de quien lo abra. Los documentos los suben solo administradores con 2FA.
- **La firma de bytes se exige al inicio del archivo.** Un PDF con datos antes de `%PDF-` se rechaza, aunque algunos lectores lo abran.
- **Un archivo válido puede esconder otro contenido después de su cabecera** (archivos políglotas). Lo acotan la entrega con el tipo detectado, `nosniff` y `sandbox`.
- **El título de un documento queda en el detalle de los eventos de auditoría.** Sirve para saber qué se descargó aunque el documento ya no exista. Los títulos no deben llevar datos sensibles; el manual del administrador no lo exige todavía y conviene decidirlo con la asesoría legal.
- **Un archivo aceptado queda publicado de inmediato.** No hay borradores: lo que el administrador sube a la carpeta de un cliente, ese cliente lo ve. Para evitar subirlo al cliente equivocado, la zona de subida muestra destacados la razón social y el RUT del cliente, y cada resultado dice para quién quedó publicado (DEC-114). Es una ayuda visual, no un control: si igual ocurre, se corrige eliminando el documento, y la descarga que haya habido queda en la auditoría.
- **Subida sin JavaScript limitada a unos 100 MB por envío.** El tope por petición equivale a 4 archivos del tamaño máximo. Con JavaScript va un archivo por petición y no hay tope en la cantidad.
- **El límite de tamaño en el servidor web y el proxy** (SEG-07) se configura en la Etapa 8. Hoy lo aplica solo la aplicación.
- **Reemplazar un archivo no muestra barra de progreso.** Usa un formulario normal, con el botón en estado "cargando".
- **Si el proceso muere entre guardar el objeto y confirmar la base,** puede quedar un objeto sin registro. No es accesible por ninguna vista y su clave no revela nada. No hay todavía un comando que los detecte.

## 5. Excepciones justificadas

- **`mark_safe` en el código QR** (`cuentas/dos_factores.py`). R5 prohíbe `mark_safe` con datos de usuarios. Aquí el contenido es el SVG que genera `segno`, formado solo por trazos; no incluye texto de formularios. Es la forma de mostrar el QR sin imágenes `data:` (que la CSP bloquea) ni servicios externos (que conocerían el secreto).

## 6. Operación

Estos procedimientos se detallarán en `docs/DESPLIEGUE.md` (Etapa 8). Todos se ejecutan en el servidor.

| Para | Comando |
| --- | --- |
| Crear un administrador | `python manage.py crear_administrador` |
| Crear el superusuario técnico | `python manage.py crear_administrador --tecnico` |
| Restablecer el 2FA de un administrador | `python manage.py restablecer_2fa <rut>` |
| Desbloquear un RUT o una IP | `python manage.py desbloquear_acceso --rut <rut>` o `--ip <ip>` |
| Borrar la auditoría más antigua que la retención | `python manage.py depurar_auditoria` (una vez al mes) |
| Borrar definitivamente lo que superó el plazo de la papelera | `python manage.py purgar_papelera` (a diario) |
| Comprobar el almacenamiento de documentos, también que el bucket no se lea sin firma | `python manage.py comprobar_almacenamiento` (antes de cargar documentos reales y tras cambiar credenciales) |

El desbloqueo de un usuario cliente se hace desde el panel, en la pestaña Usuarios de su cliente; el comando queda para administradores, RUT sin cuenta e IP.

Los dos primeros y `restablecer_2fa` imprimen un enlace de un solo uso. Quien lo use define su contraseña y, en esa misma sesión, configura su 2FA. El enlace no debe pegarse en canales que guarden historial.
