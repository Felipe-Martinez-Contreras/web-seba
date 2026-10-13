# Referencia visual

El mockup `docs/diseno/mockup-referencia.jpg` define el estilo de la aplicación. Esta guía dice qué tomar de cada pantalla y en qué se aparta la especificación. Los tokens exactos (colores, tipografía, radios) están en la sección 9 de `docs/ESPECIFICACION.md`.

Regla general: del mockup se copia el estilo y la estructura, nunca el contenido. Nombres de empresas, RUT, fechas, cifras, servicios y textos son de ejemplo.

## Pantallas

| # | Pantalla | Qué tomar | Requisitos |
| --- | --- | --- | --- |
| 1 | Sitio público, inicio | Encabezado sobre la portada; portada con fotografía, velo azul marino, titular grande en blanco y dos botones (primario lleno y secundario con borde blanco); "Nuestros servicios" con tarjetas de borde fino, ícono de línea, nombre y resumen; bloque de contacto con foto a la izquierda y formulario a la derecha; pie azul marino | PUB-02, PUB-03, PUB-04, PUB-08, SOL-02 |
| 2 | Acceso de clientes | Logo y título centrados, campos RUT y contraseña con botón de mostrar, enlace "¿Olvidó su contraseña?", botón primario a todo el ancho, nota "Acceso restringido solo para clientes autorizados" con ícono de candado, fotografía con velo en la parte inferior | AUT-01, AUT-07 |
| 3 | Portal del cliente, inicio | Barra lateral azul marino con el ítem activo en blanco; barra superior con buscador y menú del usuario; saludo; tarjeta de la empresa; buscador; carpetas como lista con ícono, contador, fecha y chevron; documentos recientes con ícono por tipo | CLI-01 a CLI-03 |
| 4 | Panel, inicio | Misma estructura de barra lateral; tarjetas de indicadores con número grande e ícono en un cuadro de color suave; tabla de solicitudes recientes con insignias; lista de clientes recientes con RUT | ADM-01, ADM-02 |
| 5 | Ficha del documento | Migas de pan, ícono por tipo, título, tamaño y fecha, botones Descargar (primario) y Ver en pantalla | CLI-08, DOC-04, DOC-05 |
| 6 | Solicitudes | Pestañas Consultas y Cotizaciones, tabla con nombre, mensaje resumido, fecha e insignia de estado | SOL-09, SOL-10 |
| 7 | Acceso en móvil | La pantalla 2 en una sola columna, con la fotografía al pie | AUT-01, sección 9 |

## Diferencias con el mockup

Donde el mockup muestre algo de esta lista, manda la especificación:

1. **Sin visor de documentos incrustado.** La pantalla 5 muestra el PDF dentro de la página. Aquí, "Ver en pantalla" abre el archivo en una pestaña nueva con el visor del navegador; la ficha muestra los datos y los botones.
2. **Sin "Recordarme".** El acceso no tiene esa casilla; la sesión vence tras 60 minutos sin uso (AUT-09).
3. **Menú del portal:** Inicio, Carpetas y Mi cuenta. No existen "Documentos" (se llega por las carpetas y el buscador) ni "Descargas".
4. **Menú del panel:** Inicio, Clientes, Solicitudes, Auditoría y Configuración. Documentos y usuarios se gestionan dentro de la ficha de cada cliente, no en secciones generales.
5. **"Mensajería y cotizaciones" se llama "Solicitudes".** No hay mensajería interna: las respuestas se envían por correo fuera de la plataforma. Los estados son Pendiente, En proceso, Resuelta y Descartada.
6. **El buscador del panel** se limita a los clientes (por RUT o razón social); no hay búsqueda global.
7. **Navegación pública:** Inicio, Servicios, Contacto y "Acceso clientes", sin menús desplegables. El mockup muestra "Documentos" en el menú público: no existe.
8. **Servicios y textos** salen de la base de datos (Servicio y DatosNegocio). Los del mockup, como "Capacitación", son de ejemplo.
9. **Redes sociales** ("Síguenos") solo se muestran si están registradas en DatosNegocio.
10. **Logo:** el escudo del mockup es de ejemplo. Desde el 13-10-2026 el sitio usa el logo propio del negocio (sección "Logo", DEC-202): el símbolo como imagen y el nombre comercial como texto, que sale de DatosNegocio.
11. **Fotografías:** de bancos gratuitos con licencia, registradas en `docs/FOTOS.md`, hasta tener fotos reales (PUB-08).
12. **Trato de "usted"** en todos los textos, aunque el mockup tutee.
13. **Ejemplo de RUT:** usa uno con dígito verificador válido, como 12.345.678-5.

## Logo

Original, creado para este sitio y entregado por el responsable el 13-10-2026. Sin licencia de terceros. Los archivos están en `static/img/` (DEC-202). A los tres SVG se les quitó el título accesible, que traía el nombre del profesional: **ese nombre no va en el repositorio**, que es público.

| Archivo | Qué es | Dónde se usa |
| --- | --- | --- |
| `simbolo-blanco.svg` | El escudo, blanco con el visto azul marino | Encabezado y pie públicos, barras laterales del portal y del panel. 32 px |
| `simbolo.svg` | El escudo, azul marino con el visto blanco | Pantallas de acceso, sobre blanco. 40 px |
| `favicon.svg`, `favicon-32.png`, `favicon.ico` | El escudo blanco sobre un cuadro azul marino | Ícono de la pestaña, en todas las páginas |
| `apple-touch-icon.png` | Lo mismo, a 180 px | Ícono al guardar el sitio en la pantalla de inicio |

Reglas:

- **El nombre es texto.** Junto al símbolo va el nombre comercial de DatosNegocio, como texto HTML: se edita en el panel y lo leen los lectores de pantalla.
- **El logo horizontal existe fuera del repositorio.** Son dos archivos, `logo-horizontal.svg` y `logo-horizontal-blanco.svg`: escudo, nombre y "PREVENCIÓN DE RIESGOS", con el texto convertido a trazos. Los guarda el responsable para usos externos, como la firma de correo y los documentos. El sitio no los usa, y `.gitignore` y `.dockerignore` impiden subirlos por error.
- **El símbolo es decorativo.** Va siempre al lado del nombre, así que lleva `alt=""`, y el archivo no trae `<title>`, `aria-label` ni `role`. Sin nombre comercial no se muestra ni el símbolo.
- **Un solo componente:** `templates/componentes/marca.html`. `marca_tono="oscuro"` elige el símbolo azul marino para fondos blancos.
- **Contraste**, según WCAG 2.1: blanco sobre azul marino `#1B2D4F`, 13,68:1, en ambas versiones del símbolo y en el favicon. Supera el 4,5:1 del nivel AA.
- **Reemplazarlo** solo requiere cambiar los archivos, con los mismos nombres. `favicon.ico` es `favicon-32.png` dentro de un contenedor ICO; si cambia el PNG, hay que rehacerlo.

