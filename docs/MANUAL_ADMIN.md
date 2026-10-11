# Manual del administrador

Guía breve para el uso diario del panel. Se completa a medida que avanza el proyecto: por ahora cubre clientes, carpetas, usuarios y auditoría. Documentos y solicitudes se agregan cuando existan.

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

## Carpetas

En la ficha del cliente, pestaña **Documentos**:

- **Nueva carpeta** agrega una al final.
- Las flechas suben o bajan una carpeta en la lista.
- **Editar** cambia su nombre o su descripción.
- **Eliminar** la borra, tras confirmar.

Dentro de un mismo cliente no puede haber dos carpetas con el mismo nombre.

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

## Auditoría

En **Auditoría** queda registrado quién entró, quién falló al entrar y qué cambios se hicieron: clientes, usuarios, carpetas y enlaces generados. Puede filtrar por cliente, por RUT, por tipo de acción y por fechas.

En la ficha de cada cliente, la pestaña **Actividad** muestra lo mismo, solo para ese cliente.

Los registros no se pueden editar ni borrar desde el panel.

## Si algo no funciona

| Situación | Qué hacer |
| --- | --- |
| Un usuario dice que su enlace "no es válido" | Venció, ya se usó o se generó otro después. Genere uno nuevo |
| Un usuario dice que su enlace "ya fue usado" y no fue él | Desactive la cuenta, revise la pestaña Actividad y avise a quien mantiene el sistema |
| Un usuario no puede entrar y aparece Activo | Probablemente olvidó su contraseña: puede usar "¿Olvidó su contraseña?" en la página de acceso, o usted puede generarle un enlace |
| Usted quedó bloqueado | Espere 15 minutos o pida a quien mantiene el sistema que lo desbloquee |
| Perdió su teléfono con la aplicación de autenticación | Use uno de sus códigos de recuperación. Si no los tiene, pida a quien mantiene el sistema que restablezca su verificación en dos pasos |
