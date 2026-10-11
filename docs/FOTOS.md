# Fotografías

Registro de las fotografías del sitio (PUB-08). Mientras no existan fotos propias del profesional, se usan fotos de bancos gratuitos con licencia de uso comercial.

**Son fotos provisionales de banco. Ninguna muestra al profesional, a sus clientes ni sus obras, y el sitio no las presenta como tales.** Sus textos alternativos describen la escena sin atribuirla al negocio.

## Fotos en uso

Descargadas el 11-10-2026 y aprobadas por el responsable el mismo día. Cada foto tiene dos archivos: 1.920 px de ancho y una versión de 960 px para pantallas chicas (`-960`).

| Archivo | Uso | Origen | Autor | Licencia | Dimensiones y peso | sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| `static/img/portada.webp` (y `portada-960.webp`) | Portada del inicio y vista previa al compartir el sitio | https://unsplash.com/photos/g9A2llpDObU | Samuel Regan-Asante (@reganography) | Unsplash License | 1.920 × 1.351 px, 232 KB; 960 × 676 px, 68 KB | `6dab9e2fe93ae94e6c97cd7cd8b7a89c4972616c2607bed068ee7d642440be55`; `c75eb10012fa210a07888932ff4b99be1fed33542e36ab6f142630df37fb9ef4` |
| `static/img/contacto.webp` (y `contacto-960.webp`) | Bloque de contacto del inicio | https://unsplash.com/photos/Ass0DusYDk4 | Ümit Yıldırım (@umityildirim) | Unsplash License | 1.920 × 1.280 px, 50 KB; 960 × 640 px, 21 KB | `137c1574b2d5746f9660027653a031af37c1cde077df3a2aa5e7df1951a34e34`; `5ed2e4843a889f9a012618d0a03695ed5f070934ef92ec121abd2a65a7c12592` |
| `static/img/acceso.webp` (y `acceso-960.webp`) | Franja inferior de las pantallas de acceso | https://unsplash.com/photos/WfeKQT3Wf0A | Ricardo Gomez Angel (@rgaleriacom) | Unsplash License | 1.920 × 650 px, 12 KB; 960 × 325 px, 5 KB | `20209b102d0e0e7213e7ffdbf8a2e0a6503e4d59a9d74c3ae8670a2fc9fc4748`; `17e868871b4750a6b0bb98394ffe148ca4619f1c730a913ba5c8312498e5fcee` |

Qué muestra cada una y su texto alternativo (`sitio/fotos.py`):

- **Portada:** una obra en construcción al atardecer, con una grúa torre, fundaciones y edificios al fondo. Sin personas ni humo. Se recortó el borde izquierdo de la foto original para dejar fuera un letrero de obra.
- **Contacto:** un casco de seguridad blanco colgado de un gancho, con una planta industrial desenfocada al fondo. Sin personas ni marcas.
- **Acceso:** un casco de seguridad amarillo sobre un fondo negro. Sin personas ni marcas. Es un recorte horizontal de la foto original, que es vertical.

## Licencia

Unsplash License, revisada el 11-10-2026 en https://unsplash.com/license: las fotos se pueden descargar y usar gratis, con fines comerciales y no comerciales, sin pedir permiso y sin atribución obligatoria. No permite vender las fotos sin una modificación significativa ni reunirlas para replicar un servicio similar. En la página de cada foto se comprobó la leyenda "Free to use under the Unsplash License": ninguna es de Unsplash+, que tiene otra licencia.

La licencia cubre el derecho de autor de la foto, no la imagen de las personas ni las marcas que aparezcan. Por eso el criterio de selección, aprobado por el responsable: **sin rostros reconocibles y sin logos ni marcas de terceros**. Se suma lo que la revisión enseñó: tampoco escenas de trabajo inseguro ni humo industrial, que contradicen el mensaje de un servicio de prevención.

## Candidatas descartadas

| Foto | Motivo |
| --- | --- |
| https://unsplash.com/photos/9kYa--GkBPs | Rostro reconocible y logo de una empresa en el chaleco |
| https://unsplash.com/photos/X1P1_EDNnok | Trabajador en altura sin protección contra caídas a la vista: mala referencia para un servicio de prevención de riesgos |
| https://unsplash.com/photos/zZza888FSKg | Rostro de perfil, posiblemente reconocible |
| https://unsplash.com/photos/aSf1kXzG5A4 | Marca visible en la ropa |
| https://unsplash.com/photos/L-RSVfhluGw | Refinería de noche, sin personas. Fue la primera portada; el responsable prefirió una obra en construcción |
| https://unsplash.com/photos/H1hgLWyEX6g | Planta industrial con columnas de humo. Fue la primera foto de acceso; el responsable la descartó porque el humo se lee como contaminación, lo opuesto a la prevención |
| https://unsplash.com/photos/sNVkn3507Oo | Dos personas de espaldas con casco, sin chaleco, frente a una obra desordenada y con andamios sin baranda a la vista |
| https://unsplash.com/photos/2ASQyjafflo | Casco blanco sobre paneles solares, con una marca del fabricante en relieve |
| https://unsplash.com/photos/80zZ1s24Nag | Rostro de perfil y marca en el casco |

## Cómo se prepararon

1. Descarga desde Unsplash a 2.400 px de ancho.
2. Conversión a WebP con Pillow, ejecutado una sola vez en un contenedor (`uv run --no-project --with pillow`): Pillow no es dependencia del proyecto ni está en `uv.lock`.
3. Reducción a 1.920 px y a 960 px de ancho, bajando la calidad hasta quedar bajo 300 KB (la grande) y bajo 100 KB (la de 960 px). La portada quedó en calidad 76 y las demás en 80; todas van bajo un velo azul marino al 80 %.

Una prueba comprueba que cada archivo sea WebP, pese menos de 300 KB y figure en este registro (`sitio/tests/test_sitio.py`).

## Cómo reemplazar una foto

1. Prepare la foto nueva en WebP, de 1.920 px de ancho y menos de 300 KB, y su versión de 960 px.
2. Reemplace los dos archivos en `static/img/` conservando sus nombres.
3. Si cambian sus proporciones o lo que muestra, actualice el ancho, el alto y el texto alternativo en `sitio/fotos.py`.
4. Actualice la fila de esta tabla: origen, autor, licencia, peso y sha256 (`Get-FileHash static\img\portada.webp -Algorithm SHA256`).

Al reemplazarlas por fotos reales del profesional, el texto alternativo puede decir lo que muestran; antes de publicar a una persona reconocible, se necesita su autorización.
