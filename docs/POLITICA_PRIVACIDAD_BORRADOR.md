# Política de privacidad: borrador

**Es un borrador para revisión legal, no un texto definitivo** (SEG-12). Lo redactó el equipo de desarrollo a partir de lo que el sistema hace al 13-10-2026; el texto que se publique lo decide el responsable del negocio, con su abogado.

## Cómo usarlo

- El texto del bloque de abajo se pega tal cual en **Panel › Configuración › Contenido del sitio › Política de privacidad**.
- Ese campo es texto simple. Una línea en blanco separa párrafos y un salto de línea simple se respeta. No admite títulos, negritas, enlaces ni HTML: lo que se escriba se muestra literal. Por eso los títulos van como líneas numeradas y las listas con guion.
- La página ya muestra el encabezado "Política de privacidad": el texto no lo repite.
- **Reemplace todos los marcadores entre corchetes antes de publicar.** El sistema no los detecta: si quedan, se publican. El único que reconoce es `[COMPLETAR]`, que no se usa aquí porque oculta los formularios.

| Marcador | Qué va |
| --- | --- |
| `[NOMBRE COMPLETO]`, `[RUT]`, `[COMUNA]`, `[CORREO DE CONTACTO]` | Datos del responsable |
| `[FECHA]` | Fecha de vigencia |
| `[DEFINIR: …]` | Plazo que el sistema no tiene definido; lo decide el responsable |
| `[CONFIRMAR: …]` | Dato de un proveedor que no se pudo comprobar desde el proyecto |

## Texto para el panel

```text
Vigente desde el [FECHA].

Esta política explica qué datos personales se tratan en este sitio, para qué, por cuánto tiempo y con qué proveedores, y cómo puede usted ejercer sus derechos.

1. QUIÉN ES EL RESPONSABLE

El responsable del tratamiento es [NOMBRE COMPLETO], persona natural, RUT [RUT], con domicilio en la comuna de [COMUNA], Chile.
Para cualquier asunto sobre sus datos personales, escriba a [CORREO DE CONTACTO].

2. QUÉ DATOS SE RECOGEN Y PARA QUÉ

2.1. Formulario de consulta
- Datos: nombre, correo, teléfono (opcional) y el mensaje que usted escriba. Se guarda además la fecha y hora en que aceptó esta política.
- Para qué: responder su consulta.
- Base de licitud: su consentimiento, que usted da al marcar la casilla de aceptación.

2.2. Formulario de cotización
- Datos: nombre, correo, teléfono, empresa (opcional), servicio de interés, rango de trabajadores (opcional), comuna o región (opcional) y su mensaje. Se guarda además la fecha y hora en que aceptó esta política.
- Para qué: preparar y enviarle una cotización, y contactarlo por ese motivo.
- Base de licitud: su consentimiento y la adopción de medidas previas a un contrato que usted mismo solicita.

En ambos formularios, sus datos se guardan en el sistema y se envían por correo al responsable para que pueda responderle. La respuesta le llega por correo o por teléfono. El sitio no le envía correos automáticos ni publicidad. Su dirección IP no se guarda junto con su solicitud; se usa por un máximo de una hora para limitar los envíos automáticos.

2.3. Cuentas de usuarios de empresas cliente
- Datos: RUT, nombre y correo de la persona; empresa a la que pertenece; contraseña, guardada cifrada de modo que nadie puede leerla; fecha del último acceso, y si la cuenta está activa.
- De dónde vienen: la cuenta la crea el responsable con los datos que entrega la empresa cliente. El sitio no permite registrarse por cuenta propia.
- Para qué: identificar a la persona y darle acceso solo a los documentos de su empresa; enviarle el enlace para activar la cuenta o recuperar la contraseña.
- Base de licitud: la ejecución del contrato de servicios entre el responsable y la empresa cliente.

De cada empresa cliente se guardan también su RUT, razón social, nombre de fantasía y los datos de una persona de contacto (nombre, correo y teléfono).

2.4. Documentos de las empresas cliente
- Datos: los archivos que el responsable prepara o recibe al prestar sus servicios y que deja disponibles para la empresa cliente. Pueden contener datos personales de trabajadores de esa empresa y, según el documento, datos sensibles.
- Para qué: entregar esos documentos a la empresa cliente y mantenerlos a su disposición.
- Base de licitud: la ejecución del contrato de servicios con la empresa cliente, que es quien decide qué datos de sus trabajadores entrega.
- Quién los ve: el responsable y las personas con cuenta de esa empresa. Ninguna empresa ve documentos de otra.

Si usted es trabajador de una empresa cliente y quiere ejercer sus derechos sobre un documento, puede dirigirse a su empleador o al responsable.

2.5. Registros de seguridad y auditoría
- Datos: fecha y hora, cuenta que realizó la acción, tipo de acción, empresa, objeto afectado, dirección IP y un detalle breve, que puede incluir el título de un documento. En un intento de acceso fallido se guarda el RUT que se escribió. No se guardan contraseñas ni el contenido de los documentos.
- Qué acciones: inicios y cierres de sesión, intentos fallidos y bloqueos, activación de cuentas y cambios de contraseña, altas y cambios de empresas y usuarios, y cada subida, vista, descarga, reemplazo o eliminación de un documento.
- Para qué: proteger las cuentas, detectar accesos indebidos y poder demostrar quién accedió a cada documento.
- Base de licitud: el interés legítimo del responsable y de las empresas cliente en la seguridad de la información.

El servidor lleva además un registro técnico de funcionamiento, con la fecha, la dirección de la página pedida y el resultado. No incluye su dirección IP ni lo que usted busque.

2.6. Cookies
El sitio usa solo cookies propias y necesarias para funcionar:
- Una cookie de seguridad de los formularios (csrftoken), que impide que otro sitio envíe formularios en su nombre. Dura hasta un año.
- Una cookie de sesión (sessionid), solo si usted inicia sesión. Se elimina al cerrar el navegador y la sesión vence tras 60 minutos sin uso.
- Una cookie temporal (messages), que guarda un aviso hasta que se le muestra en la página siguiente.

No hay cookies de analítica, de publicidad ni de redes sociales. El sitio no carga programas, tipografías ni imágenes desde otros sitios. Los enlaces a redes sociales son enlaces simples: nada se envía a esas redes mientras usted no los pulse.
Como estas cookies son necesarias, no se le pide consentimiento para usarlas. Si las bloquea, los formularios y el acceso de clientes no funcionan.

3. CUÁNTO TIEMPO SE CONSERVAN

- Consultas y cotizaciones: [DEFINIR: plazo de conservación de las solicitudes. Hoy el sistema no las borra].
- Cuentas de usuarios y datos de la empresa cliente: mientras dure la relación con la empresa cliente y, después, [DEFINIR: plazo tras el término de la relación. Hoy el sistema desactiva las cuentas, no las borra].
- Documentos: hasta que el responsable los elimina o termina la relación con la empresa cliente, y después [DEFINIR: plazo tras el término de la relación].
- Documentos eliminados: pasan 30 días en una papelera, desde la que se pueden restaurar. Luego se borran del sistema, y el proveedor de almacenamiento conserva una copia de respaldo por 30 días más. El borrado completo puede tardar, por lo tanto, algo más de 60 días.
- Respaldos de la base de datos: 14 días. Un dato borrado sigue en esos respaldos hasta que vencen.
- Copias completas del servidor: [DEFINIR: retención de las instantáneas del disco en Google Cloud].
- Registros de auditoría: 24 meses.
- Registro técnico de funcionamiento: no tiene un plazo en días; se sobrescribe al alcanzar un tamaño máximo.
- Sesiones: vencen tras 60 minutos sin uso o al cerrar el navegador. Los registros vencidos se borran cada noche.
- Enlaces de activación: 72 horas. Enlaces para recuperar la contraseña: 60 minutos.
- Direcciones IP usadas para limitar envíos y bloquear intentos de acceso: una hora como máximo.

4. QUIÉNES RECIBEN LOS DATOS

El responsable no vende ni cede sus datos. Para operar el sitio usa proveedores que tratan datos por su encargo:
- Google Cloud (Google LLC, Estados Unidos): servidor, base de datos, documentos y respaldos. Todo se almacena en un centro de datos en Estados Unidos.
- Cloudflare (Cloudflare, Inc., Estados Unidos): red por la que pasa todo el tráfico entre su navegador y el servidor. Protege la conexión y, para hacerlo, puede ver el contenido en tránsito; no lo almacena. Opera con servidores en muchos países. Las descargas de documentos no pasan por Cloudflare: van directo desde Google Cloud a su navegador, con un enlace que vence en 2 minutos.
- Resend (Resend, Inc., Estados Unidos): envío de correos. Recibe el contenido de los avisos de consultas y cotizaciones, y los correos de activación y recuperación de cuentas.
- HetrixTools ([CONFIRMAR: razón social y país]): vigila que el sitio esté en línea. No recibe datos de visitantes ni de clientes.
- [CONFIRMAR: proveedor del correo del responsable y su país]: los avisos de consultas y cotizaciones llegan a la casilla de correo del responsable.

Sus datos se transfieren, por lo tanto, fuera de Chile, principalmente a Estados Unidos. [DEFINIR: garantías de la transferencia internacional, por ejemplo las cláusulas contractuales de cada proveedor].
Fuera de estos casos, sus datos solo se entregan a una autoridad cuando la ley lo exige.

5. CÓMO SE PROTEGEN

- Toda la comunicación con el sitio va cifrada.
- Las contraseñas se guardan cifradas de modo que no se pueden leer. El acceso se bloquea temporalmente tras varios intentos fallidos.
- Las cuentas de administración exigen un segundo factor de autenticación.
- Cada empresa cliente ve únicamente sus documentos. Los documentos se guardan en un almacenamiento privado y solo se entregan a quien tiene la sesión iniciada.
- El servidor no acepta conexiones directas desde internet.
- Se registra quién accede a cada documento.
- Hay respaldos diarios.

Ningún sistema es infalible. Si ocurre un incidente de seguridad que afecte sus datos, el responsable lo informará según lo que exija la ley.

6. SUS DERECHOS

Según la Ley N° 19.628 sobre protección de la vida privada y su reforma por la Ley N° 21.719, usted puede pedir en cualquier momento:
- Acceso: saber si se tratan datos suyos, cuáles, para qué y a quién se han comunicado.
- Rectificación: corregir datos inexactos o incompletos.
- Supresión: que se eliminen sus datos cuando ya no sean necesarios, cuando retire su consentimiento o cuando el tratamiento no tenga base legal.
- Oposición: que sus datos dejen de tratarse para un fin determinado.
- Portabilidad: recibir una copia de sus datos en un formato de uso común.
- Bloqueo: suspender temporalmente el tratamiento mientras se resuelve una solicitud suya.

También puede retirar su consentimiento cuando quiera. Eso no afecta lo que se haya hecho antes de retirarlo.

Cómo ejercerlos: escriba a [CORREO DE CONTACTO] indicando su nombre, el derecho que quiere ejercer y los datos a los que se refiere. No tiene costo. Para proteger sus datos, el responsable puede pedirle que acredite su identidad.

Plazo: recibirá respuesta dentro de 30 días corridos desde que se reciba su solicitud. Ese plazo puede prorrogarse una vez, por hasta 30 días más, si la solicitud es compleja; en ese caso se le avisará.

Al suprimir datos se aplican los plazos técnicos de la sección 3: las copias de respaldo vencen solas en los plazos indicados. Algunos datos pueden conservarse cuando una ley lo exija o mientras sean necesarios para defender un derecho.

Si no queda conforme con la respuesta, puede reclamar ante la Agencia de Protección de Datos Personales, cuando esté en funciones, o ante los tribunales de justicia.

7. MENORES DE EDAD

Este sitio está dirigido a empresas y a personas adultas. No se recogen a sabiendas datos de menores de edad.

8. CAMBIOS A ESTA POLÍTICA

La versión vigente es siempre la publicada en esta página, con su fecha al inicio. Si un cambio afecta la forma en que se tratan datos ya entregados, el responsable avisará por correo a los usuarios con cuenta antes de aplicarlo. Quien haya enviado solo una consulta o una cotización puede revisar esta página o pedir la versión anterior a [CORREO DE CONTACTO].
```

## De dónde sale cada afirmación

| Tema | Fuente |
| --- | --- |
| Campos de los formularios y aceptación con fecha | `solicitudes/models.py`, SOL-01, SOL-02, SEG-12 |
| La IP no se guarda con la solicitud; vive hasta una hora en el contador | `SEGURIDAD.md` §4, `SOLICITUDES_MAXIMO_POR_HORA_IP` |
| Aviso por correo al responsable; sin correo automático al visitante | `solicitudes/templates/solicitudes/correo/notificacion.txt`, SOL-07, SOL-08 |
| Datos de cuentas y de empresas | `cuentas/models.py`, `empresas/models.py` |
| Contenido de la auditoría | `auditoria/models.py`, AUD-01, AUD-02 |
| Registro técnico sin IP ni texto de búsqueda | `config/gunicorn.py`, `core/logs.py`; rotación en `despliegue/compose.prod.yaml` (3 archivos de 10 MB por contenedor) |
| Cookies | `config/settings/base.py` (sesión, CSRF, CSP solo del propio origen); `messages` es el almacenamiento de avisos por omisión de Django |
| Papelera, 30 días | `PAPELERA_DIAS`, ADM-09 |
| Versiones del bucket, 30 días; respaldos, 14 días | `DESPLIEGUE.md` §3.4, §3.5, §7 y §13 |
| Auditoría, 24 meses | `AUDITORIA_RETENCION_MESES`, AUD-03 |
| Sesión, 60 minutos; limpieza nocturna | `SESSION_COOKIE_AGE`, `webseba-sesiones.timer` |
| Enlaces, 72 horas y 60 minutos | `ENLACE_ACTIVACION_HORAS`, `ENLACE_RESTABLECIMIENTO_MINUTOS` |
| Proveedores y ubicación | `DESPLIEGUE.md` §2, §3 y §14; `SEGURIDAD.md` §8 |
| Descargas con enlace de 2 minutos, sin pasar por Cloudflare | `DESCARGA_URL_SEGUNDOS`, `SEGURIDAD.md` §8 |

## Antes de publicar: comprobaciones que no son legales

1. **Cookies de Cloudflare.** El texto afirma que solo hay cookies propias. Cloudflare puede agregar la suya (`__cf_bm`) si tiene activada alguna protección contra bots. Abra el sitio en una ventana privada y revise las cookies en las herramientas del navegador; si aparece alguna de Cloudflare, desactive esa función o agréguela a la sección 2.6.
2. **Instantáneas del disco.** Su retención está en **Compute Engine › Instantáneas** (`DESPLIEGUE.md` §7). Contienen la base de datos completa.
3. **HetrixTools.** Sus términos nombran a "HetrixTools, Inc.", pero el país no se pudo confirmar desde el proyecto.
4. **Casilla de correo del responsable.** Cada consulta y cotización queda también ahí, sin plazo: es un lugar más donde viven esos datos.
5. **Plazos tomados de la configuración.** Si cambia `PAPELERA_DIAS`, `AUDITORIA_RETENCION_MESES`, `SESION_MINUTOS_INACTIVIDAD`, los plazos de los enlaces o las reglas de ciclo de vida de los buckets, hay que actualizar la sección 3.

## Puntos para el abogado

1. **Ley aplicable y fecha.** El texto cita la Ley 19.628 y la Ley 21.719. La entrada en vigor de la segunda está sujeta a un proyecto que la posterga (`DESPLIEGUE.md` §14). Decidir si la política debe distinguir los derechos vigentes hoy de los que rigen después: portabilidad y la Agencia vienen de la Ley 21.719.
2. **Plazo de respuesta.** El borrador promete 30 días corridos, prorrogables por 30, que es el de la Ley 21.719. La Ley 19.628 vigente fija dos días hábiles para pronunciarse antes de que el titular pueda recurrir al tribunal. Confirmar qué plazo comprometer.
3. **Bases de licitud.** Están redactadas con las categorías de la Ley 21.719 (consentimiento, contrato, interés legítimo). Bajo la Ley 19.628 vigente la regla es el consentimiento o una autorización legal. Revisar en especial el interés legítimo para la auditoría y la dirección IP, y el contrato para las cuentas de personas que no firmaron ese contrato.
4. **Responsable o encargado respecto de los documentos.** El borrador presenta al profesional como responsable de todo. Respecto de los datos de trabajadores de la empresa cliente, podría ser encargado de esa empresa, o ambos ser responsables. Define quién atiende los derechos de esos trabajadores y qué contrato lo respalda.
5. **Datos sensibles.** Los documentos de prevención de riesgos pueden traer datos de salud. Confirmar la base de licitud, si la política debe decir más y si su traslado a Estados Unidos exige algo adicional.
6. **Deber de informar a los trabajadores.** Sus datos no los entregan ellos: llegan desde su empleador. Definir quién les informa y si esta política basta.
7. **Transferencia internacional.** Garantías exigibles para Google, Cloudflare y Resend; aceptar y archivar sus acuerdos de tratamiento de datos (DPA), y decidir qué se dice en la sección 4.
8. **Cloudflare ve el tráfico descifrado**, incluidas las contraseñas al iniciar sesión y los documentos mientras se suben. Confirmar que la redacción de la sección 4 es suficiente.
9. **Plazos por definir.** Solicitudes, cuentas y documentos tras el término de la relación. Considerar las obligaciones de conservar documentos de prevención de riesgos y tributarios, y la prescripción de acciones.
10. **Auditoría, 24 meses.** Confirmar que el plazo es proporcional. El detalle de un evento puede traer el título de un documento, y un intento fallido guarda un RUT que puede no ser de un usuario.
11. **Límites de la supresión.** Una eliminación completa tarda más de 60 días por la papelera y los respaldos (`DESPLIEGUE.md` §13). Confirmar que informarlo así es aceptable y cuándo corresponde el borrado manual anticipado.
12. **Consentimiento en los formularios.** La casilla es única y obligatoria. Confirmar que es válida como consentimiento para responder, y que no cubre publicidad.
13. **Brechas de seguridad.** La sección 5 solo promete informar "según lo que exija la ley". Definir el procedimiento y los plazos de aviso.
14. **Cookies.** Confirmar que las tres son necesarias en sentido legal y que no requieren aviso ni consentimiento aparte.
15. **Aviso de cambios.** Confirmar que avisar por correo solo a los usuarios con cuenta es suficiente.
16. **Identificación del responsable.** Si corresponde publicar el RUT y la comuna de una persona natural, o basta con el nombre y un medio de contacto.
17. **Menores de edad.** Confirmar la cláusula; los documentos podrían incluir datos de trabajadores menores de 18 años.
