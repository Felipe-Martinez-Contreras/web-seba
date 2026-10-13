# Manual del administrador

Guía breve para el uso diario del panel. Se completa a medida que avanza el proyecto: por ahora cubre clientes, carpetas, documentos, usuarios y auditoría. Las solicitudes se agregan cuando existan.

## Entrar al panel

1. Abra la página de acceso e ingrese su RUT y su contraseña.
2. Ingrese el código de 6 dígitos de su aplicación de autenticación.

La sesión se cierra sola tras 60 minutos sin uso. Para salir antes, use "Cerrar sesión", al pie del menú.

## Clientes

En el panel, "Clientes" son las empresas a las que usted presta servicios.

### Crear un cliente

1. Vaya a **Clientes** y pulse **Nuevo cliente**.
2. Ingrese el RUT de la empresa y su razón social. Lo demás es opcional.
3. Deje marcada **Crear las carpetas base** para que la empresa nazca con sus cinco carpetas: Matrices de riesgos, Protocolos MINSAL, Reglamento interno, Formatos de inspección y Documentos preventivos.
4. Pulse **Crear cliente**. Se abre la ficha del cliente, lista para crear sus usuarios.

Las **notas internas** son solo para usted y su equipo: el cliente nunca las ve.

### Buscar un cliente

Escriba el RUT o parte de la razón social en el buscador de arriba. En la lista puede ver todos, solo los activos o solo los inactivos.

### Desactivar un cliente

En la ficha del cliente, pulse **Desactivar** y confirme.

- Sus usuarios pierden el acceso de inmediato, aunque tengan el portal abierto.
- Nada se borra: los datos y las carpetas se conservan.
- Para devolverle el acceso, pulse **Reactivar**. Cada persona tendrá que volver a ingresar.

Los clientes no se pueden eliminar desde el panel.

### Cuando termina la relación con un cliente

La política de privacidad promete plazos que el sistema todavía no cumple solo. Hasta que exista la función, hágalo a mano, en este orden:

1. **Entregue la copia.** En la ficha del cliente, pestaña Documentos, abra cada carpeta y descargue cada documento. Entréguele todo a la empresa por un medio seguro. No hay todavía una descarga de todo junto.
2. **Desactive el cliente** (sección anterior). Sus usuarios pierden el acceso de inmediato y los documentos dejan de estar disponibles para ellos. Nada se borra: usted los sigue viendo en el panel.
3. **Anote tres fechas** en las notas internas del cliente: el término, el término más 6 meses y el término más 5 años.
4. **A los 6 meses,** las cuentas de sus usuarios deben eliminarse. **El panel no permite borrar usuarios:** avise a quien mantiene el sistema.
5. **A los 5 años,** se eliminan los documentos y los datos de la empresa. Los documentos puede eliminarlos usted, uno por uno, desde su ficha; quedan 30 días en la papelera y después se borran. La empresa y su contacto no se pueden borrar desde el panel: avise a quien mantiene el sistema.

Mientras tanto, no reactive el cliente salvo que la relación se retome.

## Carpetas

En la ficha del cliente, pestaña **Documentos**:

- **Nueva carpeta** agrega una al final.
- Las flechas suben o bajan una carpeta en la lista.
- **Editar** cambia su nombre o su descripción.
- **Eliminar** la borra, tras confirmar. Solo aparece en las carpetas sin documentos.

Dentro de un mismo cliente no puede haber dos carpetas con el mismo nombre.

Una carpeta con documentos no se puede eliminar, y los de la papelera también cuentan. Mueva sus documentos a otra carpeta o espere a que la papelera se vacíe.

## Documentos

Pulse el nombre de una carpeta para ver sus documentos.

### Subir documentos

1. Abra la carpeta. Antes de elegir archivos, lea el recuadro **Subiendo documentos para:** y compruebe que la razón social y el RUT sean los del cliente correcto.
2. En **Subir documentos**, elija uno o varios archivos.
3. Pulse **Subir documentos**. Cada archivo muestra su avance y, al terminar, su resultado: **Aceptado**, con el cliente para el que quedó publicado, o **Rechazado**, con el motivo.

Lo que debe saber:

- Se admiten PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), JPG y PNG, de hasta 25 MB cada uno.
- Un archivo aceptado queda **publicado de inmediato**: el cliente ya puede verlo.
- El título del documento es el nombre del archivo. Puede cambiarlo después.
- No cierre la página mientras haya archivos subiendo.

Motivos de rechazo frecuentes:

| Motivo | Qué hacer |
| --- | --- |
| Formato antiguo de Office (.doc, .xls, .ppt) o archivo con contraseña | Ábralo y guárdelo como .docx, .xlsx o .pptx, sin contraseña |
| El archivo contiene macros | Guárdelo sin macros |
| El contenido no corresponde a su extensión | El archivo fue renombrado o está dañado. Vuelva a exportarlo desde el programa original |
| Supera el tamaño máximo | Reduzca el archivo o divídalo |

### Ficha del documento

Pulse un documento para abrir su ficha. Desde ahí puede:

- **Descargar** el archivo, o **Ver en pantalla** si es PDF, JPG o PNG (se abre en una pestaña nueva).
- **Editar título y descripción.** El cliente ve ambos.
- **Reemplazar el archivo**: sube una versión nueva, que pasa a ser la que ve el cliente. Mientras sube se ve una barra de progreso y, al terminar, el resultado: aceptado, o rechazado con su motivo. Las anteriores quedan en el **Historial de versiones**, que solo ven los administradores.
- En el portal, el cliente ve el documento reemplazado como "Nuevo" durante 14 días y primero en "Documentos recientes".
- **Mover a otra carpeta** del mismo cliente. Un documento no se puede pasar a otro cliente.
- **Eliminar**: lo envía a la papelera.

### Papelera

En la pestaña **Documentos** del cliente, pulse **Papelera**.

- El cliente deja de ver un documento apenas usted lo elimina.
- Durante 30 días puede **Restaurar** el documento: vuelve a su carpeta y el cliente vuelve a verlo.
- Pasado ese plazo, el documento y todas sus versiones se borran de forma definitiva y no se pueden recuperar.
- Para revisar un documento eliminado, primero restáurelo: mientras está en la papelera no se puede abrir ni descargar.

Si un cliente le pide eliminar sus datos por completo, avise a quien mantiene el sistema: el borrado definitivo no es instantáneo en los respaldos del almacenamiento.

## Usuarios

Cada usuario es una persona de la empresa cliente. Entra al portal con su propio RUT y una contraseña que solo ella conoce.

### Crear un usuario

1. En la ficha del cliente, pestaña **Usuarios**, pulse **Crear usuario**.
2. Ingrese el RUT y el nombre de la persona. El correo es opcional, pero sin él la persona no podrá recuperar su contraseña por sí sola.
3. Pulse **Crear usuario y generar enlace**.
4. Aparece el **enlace de activación**. Pulse **Copiar enlace** y entrégueselo a la persona.

Sobre el enlace:

- Se muestra **una sola vez**. Si lo pierde, genere uno nuevo.
- Sirve una sola vez y vence a las 72 horas.
- Con él, la persona define su contraseña. Usted nunca la conoce ni la necesita.
- Quien tenga el enlace puede activar la cuenta. Entréguelo directamente a la persona, no a un grupo.

Si el correo de la plataforma está configurado, puede marcar **Enviar también el enlace por correo**. La página le dirá si el correo salió o no; si no salió, copie el enlace y entréguelo por otro medio.

### Estados de un usuario

| Estado | Qué significa | Qué puede hacer usted |
| --- | --- | --- |
| Pendiente | Aún no define su contraseña | Si el enlace venció o se perdió: **Acciones → Generar enlace de activación** |
| Activo | Puede ingresar | — |
| Bloqueado | Falló la contraseña varias veces | Pulse **Desbloquear**. Si no lo hace, el bloqueo termina solo en 15 minutos |
| Inactivo | Usted desactivó la cuenta | **Acciones → Reactivar** |

### Otras acciones

En el menú **Acciones** de cada usuario:

- **Editar**: corrige el nombre o el correo. El RUT solo se puede corregir mientras la cuenta está pendiente.
- **Generar enlace de restablecimiento**: para quien olvidó su contraseña y no puede recuperarla por correo. Vence en 1 hora.
- **Desactivar**: la persona pierde el acceso de inmediato. Úselo cuando alguien deja de trabajar en la empresa cliente.

Generar un enlace nuevo deja sin efecto el anterior.

## Solicitudes

En **Solicitudes** llegan las consultas y las solicitudes de cotización que se envían desde el sitio. Hay una pestaña para cada tipo.

- Puede buscar por nombre, correo o empresa, y filtrar por estado y por fechas.
- Abra una solicitud para ver todos sus datos.
- **Para responder, escriba al correo o llame al teléfono de la solicitud.** La plataforma no envía mensajes al visitante.
- Cambie el **estado** para llevar el seguimiento: Pendiente, En proceso, Resuelta o Descartada.
- Las **notas internas** son solo para usted y su equipo.

Cada solicitud muestra además qué pasó con el correo de aviso que el sistema le envía a usted:

| Notificación | Qué significa |
| --- | --- |
| Enviada | El aviso salió hacia su correo |
| Por enviar | Se está enviando; espere unos segundos y recargue |
| Fallida | El aviso no se pudo enviar. La solicitud está guardada completa. Pulse **Reintentar notificación** |
| Correo no configurado | El sistema aún no tiene un correo para avisarle. La solicitud está guardada completa |

**Las solicitudes se eliminan solas a los 12 meses de recibidas,** con sus notas internas, en cualquier estado. Es el plazo de la política de privacidad.

- Si la persona pasó a ser cliente, lo que necesite conservar debe estar en la ficha del cliente, no en la solicitud.
- El aviso que le llegó a usted por correo no se borra solo: elimínelo de su casilla con el mismo plazo.
- Si alguien pide que se borre antes su consulta, avise a quien mantiene el sistema.

La solicitud se guarda siempre, aunque el aviso falle. Si recibe pocos avisos, revise igual la bandeja: el inicio del panel muestra cuántas están pendientes.

## Contenido del sitio

En **Configuración › Contenido del sitio** se edita lo que muestra el sitio público.

- **Datos del negocio:** nombre comercial, titular y bajada de la portada, presentación, contacto, redes sociales y texto de la política de privacidad.
- **Servicios:** cree, edite, ordene con las flechas, y active o desactive. Un servicio no se elimina: al desactivarlo deja de mostrarse.

Reglas que conviene conocer:

- **Lo que deja vacío no se muestra.** Sin titular no hay portada; sin servicios activos no hay sección de servicios. El sitio nunca muestra un espacio en blanco ni un texto de relleno.
- Cada dato que falta aparece con la marca **[COMPLETAR]**, y el inicio del panel dice cuántos quedan.
- **Sin el texto de la política de privacidad, los formularios del sitio no se muestran.** En su lugar van su teléfono y su correo, si los registró.
- Los textos son simples: se respetan los saltos de línea, sin negritas ni enlaces.
- WhatsApp y las redes sociales son opcionales.

En **Auditoría** queda registrado quién entró, quién falló al entrar y qué cambios se hicieron: clientes, usuarios, carpetas, enlaces generados y documentos (subidas, reemplazos, movimientos, eliminaciones y restauraciones). También queda cada vez que alguien ve o descarga un documento, y quién fue. Puede filtrar por cliente, por RUT, por tipo de acción y por fechas.

En la ficha de cada cliente, la pestaña **Actividad** muestra lo mismo, solo para ese cliente.

Los registros no se pueden editar ni borrar desde el panel.

## Si algo no funciona

| Situación | Qué hacer |
| --- | --- |
| Un usuario dice que su enlace "no es válido" | Venció, ya se usó o se generó otro después. Genere uno nuevo |
| Un usuario dice que su enlace "ya fue usado" y no fue él | Desactive la cuenta, revise la pestaña Actividad y avise a quien mantiene el sistema |
| Un usuario no puede entrar y aparece Activo | Probablemente olvidó su contraseña: puede usar "¿Olvidó su contraseña?" en la página de acceso, o usted puede generarle un enlace |
| Un archivo se rechaza y no entiende el motivo | Lea el motivo junto al nombre del archivo; la tabla de "Subir documentos" dice qué hacer en cada caso |
| Necesita eliminar una carpeta y no aparece el botón | Tiene documentos, quizá en la papelera. Muévalos o restáurelos y muévalos |
| Subió un documento al cliente equivocado | Elimínelo de inmediato desde su ficha: ese cliente deja de verlo. En Auditoría puede revisar si alguien alcanzó a verlo o descargarlo. Luego súbalo al cliente correcto |
| Eliminó un documento por error | Vaya a la Papelera del cliente y pulse Restaurar, dentro de los 30 días |
| El sitio público se ve casi vacío | Faltan datos en Contenido del sitio. El aviso del inicio del panel dice cuántos |
| El sitio no muestra los formularios | Falta el texto de la política de privacidad, en Contenido del sitio |
| Una solicitud dice "Fallida" | El aviso por correo no salió, pero la solicitud está completa. Ábrala y pulse Reintentar notificación. Si sigue fallando, avise a quien mantiene el sistema |
| Usted quedó bloqueado | Espere 15 minutos o pida a quien mantiene el sistema que lo desbloquee |
| Perdió su teléfono con la aplicación de autenticación | Use uno de sus códigos de recuperación. Si no los tiene, pida a quien mantiene el sistema que restablezca su verificación en dos pasos |
