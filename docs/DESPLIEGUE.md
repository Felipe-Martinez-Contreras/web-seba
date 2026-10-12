# Despliegue y operación

Cómo se publica y se mantiene la aplicación. Las decisiones están en `DECISIONES.md` (DEC-164 en adelante) y sus riesgos en `SEGURIDAD.md` §8.

**Estado al 12-10-2026.** La aplicación corre en staging, en `https://seba.fmartinez.xyz`. El primer despliegue real (commit `da83509`) dejó seis fallos; el commit `a46c641` los corrigió y, ya desplegado, las correcciones quedaron comprobadas en la VM. Lo verificado y lo que sigue pendiente (el simulacro de restauración, entre otros) están en la sección 12, con su bitácora.

Convenciones de esta guía:

- El nombre provisional del sitio es `seba.fmartinez.xyz` (definido por el responsable el 11-10-2026).
- `CORREO-DEL-RESPONSABLE` es un marcador: el correo real no se escribe en este repositorio, que es público. Va solo en `/etc/web-seba/web.env`, en la VM, y en las consolas.
- Los comandos marcados **VM** se escriben en la sesión SSH de la máquina (Linux). Los marcados **PowerShell**, en el equipo de desarrollo.
- `dc` es `/opt/web-seba/despliegue/vm/dc`: Docker Compose con la configuración de producción. Siempre con `sudo`.
- Los nombres de los menús de las consolas cambian con el tiempo; si uno no coincide, busque el concepto.

## 1. Arquitectura

```
Visitante ──HTTPS──> Cloudflare (TLS, caché de /static/) ══túnel saliente══> VM e2-micro (sin puertos de entrada)
                                                                             ├─ cloudflared ──http──> web (Gunicorn :8000)
                                                                             └─ db (PostgreSQL 18, volumen en disco)
web ──API S3 + clave HMAC──> bucket de documentos (privado, versionado)
Navegador ──URL firmada, 120 s──> bucket de documentos     (las descargas no pasan por la VM ni por Cloudflare)
VM ──pg_dump diario──> bucket de respaldos                 web ──SMTP 587──> Resend
```

| Pieza | Dónde | Plan |
| --- | --- | --- |
| Aplicación y base de datos | VM e2-micro de Google Cloud, `us-east1`, Docker Compose | Nivel gratuito, salvo la IP externa: unos 3,65 USD al mes |
| Entrada y HTTPS | Cloudflare Tunnel (`cloudflared`) | Gratuito |
| Documentos | Google Cloud Storage, API compatible con S3 | Nivel gratuito (5 GB) |
| Respaldos | Otro bucket de Google Cloud Storage | El mismo cupo |
| Correo | Resend, por SMTP | Gratuito (100 al día, 3.000 al mes, hasta 3 dominios) |
| Imagen | GitHub Container Registry, pública | Gratuito |
| Monitor | HetrixTools (o StatusCake) | Gratuito |

Memoria de la VM (1 GB de RAM y 2 GB de swap):

| Contenedor | Ajuste | Límite |
| --- | --- | --- |
| `web` | Gunicorn con 2 procesos y 2 hilos cada uno | 450 MB |
| `db` | `shared_buffers=64MB`, `max_connections=20` | 300 MB |
| `cloudflared` | sin actualización automática | 96 MB |

Medido en la VM el 12-10-2026, con todo corriendo y sin carga: `web` unos 104 MB, `cloudflared` unos 25 MB y `db` unos 9 MB. Cada verificación de contraseña (Argon2) usa unos 100 MB mientras dura; para eso está el swap. Falta medirlo bajo uso (sección 12).

**Costo esperado: unos 3,65 USD al mes, no cero.** La IP externa en uso de la VM se cobra a 0,005 USD por hora; el nivel gratuito cubre solo una hora al mes (verificado por el responsable en la página de precios de VPC el 11-10-2026, y aceptado: DEC-184). Lo demás se mantiene en planes gratuitos mientras no se superen sus límites.

**Staging y producción son la misma VM.** Primero corre como staging, con datos DEMO. Cuando se cumple la lista de la sección 11, se vacía y pasa a producción. No hay staging después.

## 2. Qué hay en el repositorio

| Archivo | Para qué |
| --- | --- |
| `Dockerfile` (target `prod`) | Imagen de producción: sin dependencias de desarrollo, estáticos recolectados, usuario sin privilegios, configuración de producción fija |
| `config/gunicorn.py` | Servidor: TCP, hilos, aplicación cargada antes de crear los procesos, logs en JSON sin el token de los enlaces |
| `docker/salud.py`, `docker/head.py` | Comprobaciones desde dentro del contenedor: `/salud/` responde 200, y HEAD responde sin cuerpo |
| `despliegue/compose.prod.yaml` | Los tres contenedores, sin puertos publicados |
| `despliegue/compose.env.example`, `web.env.example` | Plantillas de los dos archivos de variables del servidor |
| `despliegue/vm/preparar.sh` | Prepara la VM: swap, Docker, parches automáticos |
| `despliegue/vm/desplegar.sh` | Despliega la imagen de un commit |
| `despliegue/vm/respaldar.sh`, `restaurar.sh` | Respaldo y restauración de la base |
| `despliegue/vm/tarea.sh`, `despliegue/systemd/` | Tareas programadas |
| `.github/workflows/ci.yml` (trabajo `imagen`) | Construye, prueba y publica la imagen |

## 3. Pasos en las consolas (los hace el responsable)

Hágalos en este orden. Anote los valores que se piden: van a los archivos de la sección 4.

### 3.1 Google Cloud: proyecto y alerta de presupuesto

1. En [console.cloud.google.com](https://console.cloud.google.com), cree un proyecto (por ejemplo `web-seba`) y asócielo a una cuenta de facturación. El nivel gratuito exige tener una, aunque no se cobre.
2. **Facturación › Presupuestos y alertas › Crear presupuesto.** Alcance: ese proyecto. Importe: **5 USD** al mes (el costo esperado es de unos 3,65 USD, por la IP externa). Umbrales: 50 %, 90 % y 100 %. Marque el aviso por correo a los administradores de facturación. *Un presupuesto avisa; no detiene el gasto.*
3. **APIs y servicios › Biblioteca**: habilite *Compute Engine API* y *Cloud Identity-Aware Proxy API*.

### 3.2 Google Cloud: la máquina

**Compute Engine › Instancias de VM › Crear instancia.**

| Campo | Valor | Por qué |
| --- | --- | --- |
| Región y zona | `us-east1`, cualquier zona | Región del nivel gratuito |
| Tipo de máquina | `e2-micro` | Es la única gratuita |
| Disco de arranque | Debian 13, **disco persistente estándar**, 30 GB | El "balanceado" que viene elegido por defecto se cobra |
| Cuenta de servicio | Cree una nueva: `vm-web-seba` | Para subir respaldos sin claves guardadas |
| Permisos de acceso | "Permitir el acceso completo a todas las APIs de Cloud" | Lo que puede hacer lo limitan los roles del paso 3.5 |
| Firewall | **No** marque "Permitir tráfico HTTP" ni "HTTPS" | La VM no recibe conexiones |
| Metadatos | clave `enable-oslogin`, valor `TRUE` | Entrada con su cuenta de Google, sin llaves SSH repartidas |

Deje la IP externa efímera que viene por defecto: la VM la necesita para **salir** a internet (Cloudflare, Resend, GitHub). No abre ninguna entrada.

> **Esto tiene costo.** La IP externa en uso se cobra a 0,005 USD por hora, unos 3,65 USD al mes. Quitarla exigiría Cloud NAT para que la VM pueda salir a internet, que cuesta más. El responsable aceptó ese costo (DEC-184).

### 3.3 Google Cloud: cerrar la entrada y dejar solo IAP

**Red de VPC › Firewall.**

1. Elimine las reglas `default-allow-ssh`, `default-allow-rdp` y `default-allow-icmp`. Son las que abren la máquina a internet.
2. Cree una regla: nombre `permitir-ssh-solo-iap`, dirección *Entrada*, acción *Permitir*, destinos *Todas las instancias de la red*, rangos de origen **`35.235.240.0/20`**, protocolo y puerto **TCP 22**. Ese rango es el de Identity-Aware Proxy: nadie más llega al puerto 22.
3. **IAM y administración › IAM**: a su cuenta, agregue el rol *Usuario de túnel protegido con IAP*. Si usted no es propietario del proyecto, agregue también *Acceso de administrador de SO de Compute*.

Para entrar: botón **SSH** de la instancia en la consola (usa IAP solo). O, con `gcloud` instalado, en **PowerShell**:

```powershell
gcloud compute ssh NOMBRE-DE-LA-VM --zone ZONA --tunnel-through-iap
```

### 3.4 Google Cloud: bucket de documentos

**Cloud Storage › Buckets › Crear.**

| Campo | Valor |
| --- | --- |
| Nombre | Uno único, sin datos del negocio (por ejemplo `ws-docs-` más letras al azar) |
| Ubicación | Región, `us-east1` |
| Clase | Standard |
| Control de acceso | Uniforme; **"Aplicar la prevención de acceso público"** marcado |
| Protección | **Control de versiones de objetos** activado |

Después, en el bucket, pestaña **Ciclo de vida › Agregar una regla**: acción *Borrar objeto*; condición *Días desde que dejó de ser la versión actual*: **30**. Es la expiración de versiones antiguas que pide SEG-11.

Luego la credencial, con permisos mínimos (SEG-08):

1. **IAM y administración › Cuentas de servicio › Crear**: `documentos-web-seba`, sin roles de proyecto.
2. En el bucket, pestaña **Permisos › Otorgar acceso**: principal, esa cuenta de servicio; rol **Usuario de objetos de Storage**. Solo sobre este bucket.
3. **Cloud Storage › Configuración › Interoperabilidad › Crear una clave para una cuenta de servicio**: elija `documentos-web-seba`. Anote la *clave de acceso* y el *secreto*: el secreto se muestra una sola vez.

### 3.5 Google Cloud: bucket de respaldos

Cree otro bucket (`us-east1`, Standard, acceso uniforme, prevención de acceso público), **sin** control de versiones.

- **Ciclo de vida**: *Borrar objeto* cuando la *antigüedad* sea de **14** días.
- **Permisos**: a la cuenta `vm-web-seba`, los roles **Creador de objetos de Storage** y **Visualizador de objetos de Storage**, solo sobre este bucket. Puede subir y leer respaldos; no puede borrarlos ni reemplazarlos, ni siquiera si alguien toma el control de la VM.

### 3.6 Cloudflare: el túnel

1. **Zero Trust › Redes › Túneles › Crear un túnel**, tipo *Cloudflared*, nombre `web-seba`.
2. La pantalla muestra un comando de instalación que termina en una cadena larga: ese es el **token**. Cópielo; no ejecute el comando.
3. **Nombre de host público**: subdominio `seba`, dominio `fmartinez.xyz`, tipo **HTTP**, URL **`web:8000`**. Cloudflare crea solo el registro DNS.

### 3.7 Cloudflare: ajustes para ese nombre

Los ajustes van en reglas acotadas al nombre del sitio, para no tocar el resto de `fmartinez.xyz`.

1. **Reglas › Reglas de configuración › Crear**: *Nombre de host* es igual a `seba.fmartinez.xyz`. Desactive **Ofuscación de direcciones de correo**, **Rocket Loader** y **Web Analytics (RUM)**. Los tres reescriben el HTML o inyectan scripts, y la política de seguridad de contenido de la aplicación los bloquea.
2. **Reglas › Reglas de caché › Crear**: *Nombre de host* es igual a `seba.fmartinez.xyz` **y** *Ruta URI* empieza con `/static/`. Acción: *Apto para caché*, TTL perimetral *Respetar el origen*. La aplicación ya envía un año de caché en esos archivos, que llevan un hash en el nombre. **No** cree reglas de caché para otras rutas: el HTML y las páginas privadas no se cachean.
3. **SSL/TLS › Certificados perimetrales**: versión mínima de TLS 1.2. La redirección de HTTP a HTTPS la hace la propia aplicación.

### 3.8 Resend y los registros de correo

1. Cree la cuenta en [resend.com](https://resend.com). **Dominios › Agregar dominio**: `seba.fmartinez.xyz` completo (el correo saldrá de `no-responder@seba.fmartinez.xyz`). Región: la de EE. UU.
2. Resend muestra los registros que debe crear. En **Cloudflare › DNS** de `fmartinez.xyz`, créelos tal como aparecen, todos en modo *Solo DNS*:
   - un TXT de **DKIM** (`resend._domainkey.…`),
   - un MX y un TXT de **SPF** para el retorno (`send.…`).
3. Agregue además **DMARC**: registro TXT con nombre `_dmarc.seba.fmartinez.xyz` y contenido `v=DMARC1; p=none; rua=mailto:CORREO-DEL-RESPONSABLE`. Parte en `none` para observar; tras dos semanas sin fallos en los reportes, cámbielo a `p=quarantine`.
4. En Resend, pulse **Verificar** y espere el estado *Verificado*.
5. **Claves de API › Crear**: permiso **Solo envío**, limitada a ese dominio. Anótela: se muestra una sola vez.

### 3.9 GitHub: la imagen

Tras la primera ejecución en verde de la CI en `main`: en GitHub, **su perfil › Packages › web-seba › Package settings › Change visibility › Public**. El código ya es público y la imagen no lleva secretos; así la VM la descarga sin credenciales.

### 3.10 Monitor de disponibilidad

En HetrixTools (plan gratuito), cree un monitor HTTP sobre `https://seba.fmartinez.xyz/salud/`, cada 5 minutos, que espere el código 200, con aviso a `CORREO-DEL-RESPONSABLE`. Confirme al registrarse que el plan gratuito admite uso comercial; si no, StatusCake ofrece lo mismo.

## 4. Primera instalación en la VM

**VM**, en la sesión SSH:

```bash
sudo apt-get update && sudo apt-get install -y git
sudo git clone https://github.com/Felipe-Martinez-Contreras/web-seba.git /opt/web-seba
sudo /opt/web-seba/despliegue/vm/preparar.sh
```

`preparar.sh` deja la zona horaria de Chile, 2 GB de swap, Docker, los parches automáticos y dos archivos por completar en `/etc/web-seba/` (solo los lee `root`).

Complételos con `sudo nano /etc/web-seba/compose.env` y `sudo nano /etc/web-seba/web.env`. Cada variable trae su explicación. Las que salen de la sección 3:

| Variable | Archivo | De dónde sale |
| --- | --- | --- |
| `POSTGRES_PASSWORD` | `compose.env` | `openssl rand -hex 24` |
| `TUNNEL_TOKEN` | `compose.env` | Paso 3.6 |
| `RESPALDOS_BUCKET` | `compose.env` | Paso 3.5 |
| `SECRET_KEY` | `web.env` | `openssl rand -base64 48` |
| `ALLOWED_HOSTS`, `SITIO_URL` | `web.env` | `seba.fmartinez.xyz` y `https://seba.fmartinez.xyz` |
| `DJANGO_ADMIN_RUTA` | `web.env` | `openssl rand -hex 8` |
| `DATABASE_URL` | `web.env` | Con la misma clave de `POSTGRES_PASSWORD` |
| `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | `web.env` | Paso 3.4 |
| `CORREO_CLAVE`, `CORREO_REMITENTE` | `web.env` | Paso 3.8 |
| `NOTIFICACIONES_DESTINATARIOS`, `ERRORES_DESTINATARIOS` | `web.env` | `CORREO-DEL-RESPONSABLE` en ambas: escriba ahí su correo real, que no figura en el repositorio |

No cambie `PROXY_CONFIANZA_REDES`, `PROXY_CONFIANZA_ENCABEZADO` ni `PROXY_HTTPS_ENCABEZADO`: hacen que la aplicación acepte la IP del visitante solo del contenedor del túnel (comprobado en local el 11-10-2026: desde esa dirección la auditoría registra la IP de `CF-Connecting-IP`; desde otro contenedor de la misma red, la ignora).

Después, el primer despliegue (sección 5) y, ya con la aplicación arriba, **en este orden**:

```bash
sudo /opt/web-seba/despliegue/vm/dc exec web python manage.py comprobar_almacenamiento --firma
sudo /opt/web-seba/despliegue/vm/dc exec web python manage.py crear_administrador
# Solo en staging, y después de crear_administrador:
sudo /opt/web-seba/despliegue/vm/dc exec -e DEMO_PERMITIDO=true web python manage.py cargar_demo
```

`cargar_demo` necesita que ya exista un administrador: los documentos de demostración quedan a su nombre. El permiso `DEMO_PERMITIDO=true` se pasa solo a ese comando, con `-e`; **no se escribe en `web.env`**, así el servidor nunca queda habilitado para cargar datos de demostración.

Antes de `crear_administrador`, el inicio del sitio muestra "Sitio en preparación" con el botón de acceso: es el estado previsto para una base sin contenido, no un error.

## 5. Desplegar una versión

1. Suba los cambios a `main` y espere la CI en verde. El trabajo *Imagen de producción* publica `ghcr.io/felipe-martinez-contreras/web-seba:<commit>`.
2. Copie el identificador completo del commit (40 caracteres). En **PowerShell**: `git rev-parse HEAD`.
3. **VM**:

```bash
sudo /opt/web-seba/despliegue/vm/desplegar.sh <commit>
```

El guion deja el código de despliegue en ese commit, baja la imagen, respalda la base en la máquina, aplica las migraciones, reinicia, comprueba `/salud/` y `check --deploy`, y programa las tareas. Si la imagen no existe, no cambia nada.

**El sitio no responde mientras `web` arranca**: el túnel espera a que la aplicación esté sana. Cuánto dura:

| Dónde | Cuánto tardó `web` en quedar sano |
| --- | --- |
| VM, commit `da83509` (12-10-2026) | Unos 106 s la primera vez y unos 144 s después |
| Local, imagen de producción limitada a 0,25 CPU y 450 MB, antes del cambio | Unos 30 s |
| Local, misma prueba, con el cambio (DEC-189) | Unos 20 s |
| VM, commit `a46c641`, con el cambio (12-10-2026) | **Unos 5 s**: el contenedor partió a las 21:06:05 UTC y el primer sondeo sano fue a las 21:06:10 |

La prueba local no reproduce el disco ni la memoria de la e2-micro: sirvió para comparar antes y después, no para predecir la VM, donde la mejora fue mayor. Es una sola medición en la VM; si un arranque posterior tarda mucho más, anótelo aquí. Qué cambió: Gunicorn carga la aplicación una sola vez, antes de crear sus dos procesos (antes cada proceso importaba todo por su cuenta), y el plazo de arranque del healthcheck pasó de 120 a 300 s. Ese plazo no retrasa nada: mientras dura, Docker sondea cada 5 s y marca el contenedor sano con la primera respuesta 200 de `/salud/`, que consulta la base. Con 120 s, el segundo arranque lo superó y el sondeo pasó a ser cada 30 s. Si a los 300 s sigue sin responder, tres fallos seguidos lo marcan como no sano y `desplegar.sh` termina con error.

Para medirlo en la **VM**, justo después de desplegar:

```bash
sudo docker inspect --format '{{.State.StartedAt}}{{range .State.Health.Log}}{{"\n"}}{{.Start}} salida={{.ExitCode}}{{end}}' web-seba-web-1
sudo /opt/web-seba/despliegue/vm/dc logs web | head -n 12
```

La primera línea es la hora de inicio del contenedor; las siguientes, los últimos sondeos (`salida=0` es sano). El tiempo de arranque es la diferencia entre el inicio y el primer sondeo con `salida=0`. Docker guarda solo los cinco últimos, así que hay que mirarlo antes de que pasen unos minutos.

**Volver atrás:** el mismo comando con el commit anterior (el guion lo muestra al terminar: "antes: …"). Si la versión nueva aplicó una migración que la anterior no entiende, además hay que restaurar el respaldo que el guion dejó en `/var/backups/web-seba/` (sección 7).

Comandos útiles, **VM**:

```bash
sudo /opt/web-seba/despliegue/vm/dc ps
sudo /opt/web-seba/despliegue/vm/dc logs --tail 100 web
sudo /opt/web-seba/despliegue/vm/dc exec -T web python docker/salud.py     # /salud/ responde 200
sudo /opt/web-seba/despliegue/vm/dc exec -T web python docker/head.py /    # HEAD: 200 y sin cuerpo
free -m ; sudo docker stats --no-stream
```

## 6. Tareas programadas

Las instala `desplegar.sh` como temporizadores de systemd, en hora de Chile.

| Temporizador | Qué ejecuta | Cuándo |
| --- | --- | --- |
| `webseba-reintentar.timer` | `reintentar_notificaciones` | Cada 15 minutos |
| `webseba-respaldo.timer` | `respaldar.sh` | 02:30 |
| `webseba-papelera.timer` | `purgar_papelera` | 03:20 |
| `webseba-sesiones.timer` | `clearsessions` | 03:40 |
| `webseba-auditoria.timer` | `depurar_auditoria` | Día 1 de cada mes, 04:10 |

Si una tarea termina con error, systemd llama a `avisar_fallo` y llega un correo a `ERRORES_DESTINATARIOS`. Si lo caído es la aplicación entera, ese correo no sale: para eso está el monitor.

```bash
systemctl list-timers 'webseba-*'                       # próximas ejecuciones
journalctl -u 'webseba-*' --since '-1 day'              # qué pasó
sudo /opt/web-seba/despliegue/vm/tarea.sh purgar_papelera   # ejecutar una a mano
```

Los parches del sistema se instalan solos cada día (`unattended-upgrades`). Si uno pide reiniciar, la máquina se reinicia a las 05:00 y los contenedores vuelven solos; el sitio se corta uno o dos minutos.

## 7. Respaldos y restauración (SEG-11)

| Qué | Cómo | Retención |
| --- | --- | --- |
| Base de datos | `pg_dump` diario a `/var/backups/web-seba/` y al bucket de respaldos. Se comprueba que el archivo se pueda leer antes de darlo por bueno | 14 días en el bucket; los 3 últimos en la VM |
| Documentos | Versionado del bucket de documentos | 30 días para versiones antiguas o borradas |

Pérdida máxima de datos: 24 horas en la base (RPO). Recuperación: un día hábil (RTO), a medir en el simulacro.

**Respaldar ahora**, **VM**: `sudo /opt/web-seba/despliegue/vm/respaldar.sh`

**Restaurar**, **VM**:

```bash
gcloud storage ls gs://BUCKET-DE-RESPALDOS/                                   # elegir el respaldo
sudo /opt/web-seba/despliegue/vm/restaurar.sh gs://BUCKET-DE-RESPALDOS/webseba-AAAAMMDDTHHMMSSZ.dump
```

El guion pide escribir el nombre de la base para confirmar, detiene el túnel y la aplicación, reemplaza la base, vuelve a levantar todo y comprueba `/salud/`.

**Recuperar un documento borrado o reemplazado**, desde su equipo con `gcloud` o desde Cloud Shell:

```bash
gcloud storage ls --all-versions gs://BUCKET-DE-DOCUMENTOS/docs/UUID-EMPRESA/
gcloud storage cp "gs://BUCKET-DE-DOCUMENTOS/docs/UUID-EMPRESA/UUID-VERSION#GENERACION" gs://BUCKET-DE-DOCUMENTOS/docs/UUID-EMPRESA/UUID-VERSION
```

**Si se pierde la VM entera:** cree otra (pasos 3.2 y 3.3), repita la sección 4 con los mismos valores (el token del túnel y las claves siguen sirviendo; guárdelos en un gestor de contraseñas), despliegue el último commit y restaure el último respaldo. Los documentos no se pierden: están en el bucket.

### Simulacro de restauración

Se hace en staging, antes de cargar documentos reales, y se anota aquí.

1. `cargar_demo`; suba un PDF propio por el panel y anote su SHA-256 (**PowerShell**: `Get-FileHash archivo.pdf`).
2. Anote los conteos: `sudo dc exec web python manage.py shell -c "from empresas.models import Empresa; from documentos.models import Documento; from auditoria.models import EventoAuditoria; print(Empresa.objects.count(), Documento.objects.count(), EventoAuditoria.objects.count())"`
3. `sudo respaldar.sh`.
4. Destruya la base: `sudo dc down` y `sudo docker volume rm web-seba_db_datos`.
5. `sudo desplegar.sh <commit>` (base vacía) y `sudo restaurar.sh gs://…`, tomando el tiempo.
6. Compruebe: mismos conteos, inicio de sesión con 2FA, descarga del PDF con el mismo SHA-256.
7. En el panel, elimine ese documento y púrguelo; recupérelo del bucket con los comandos de arriba.

| Fecha | Quién | Respaldo usado | Conteos antes / después | SHA-256 coincide | Tiempo total | Resultado |
| --- | --- | --- | --- | --- | --- | --- |
| *Pendiente* | | | | | | |

Lo comprobado hasta ahora, en local el 11-10-2026 con la imagen de producción: `pg_dump`, borrado de la base, `pg_restore`, migraciones al día y la extensión `unaccent` presente tras restaurar. **No reemplaza al simulacro**: faltan el bucket, los guiones en la VM y los documentos.

## 8. Operación del día a día

Todos en la **VM**, con `sudo /opt/web-seba/despliegue/vm/dc exec web python manage.py …`:

| Para | Comando |
| --- | --- |
| Crear un administrador | `crear_administrador` |
| Crear el superusuario técnico | `crear_administrador --tecnico` |
| Restablecer el 2FA de un administrador | `restablecer_2fa <rut>` |
| Desbloquear un RUT o una IP | `desbloquear_acceso --rut <rut>` o `--ip <ip>` |
| Ver qué contenido falta | `contenido_pendiente` (con `--estricto` falla si falta algo) |
| Comprobar el bucket | `comprobar_almacenamiento --firma` |

Los tres primeros imprimen un enlace de un solo uso: no lo pegue en canales que guarden historial. El desbloqueo de un usuario cliente se hace desde el panel.

### Parches mensuales (sección 13 de la especificación)

Una vez al mes, en el equipo de desarrollo (**PowerShell**):

1. Revise las versiones nuevas de Django y de las dependencias de `pyproject.toml`, y de las imágenes de `Dockerfile` y `despliegue/compose.prod.yaml` (Python, PostgreSQL, cloudflared).
2. Cambie las versiones y regenere el bloqueo: `docker compose run --rm --user root --no-deps web uv lock`, luego `docker compose build web`.
3. `docker compose run --rm web pytest`, commit y `git push`. La CI repite las pruebas y `pip-audit`.
4. Despliegue (sección 5).

Un aviso de seguridad de Django no espera al mes: se aplica al publicarse.

## 9. Rotación de secretos

| Secreto | Cómo se rota | Efecto |
| --- | --- | --- |
| `SECRET_KEY` | Valor nuevo en `web.env`; `sudo dc up -d web` | Cierra todas las sesiones |
| Clave HMAC del bucket | Cree otra clave (paso 3.4), cámbiela en `web.env`, `sudo dc up -d web`, ejecute `comprobar_almacenamiento` y recién entonces borre la antigua | Ninguno si se hace en ese orden |
| API key de Resend | Cree otra, cámbiela en `web.env`, `sudo dc up -d web`, revoque la antigua | Ninguno |
| Token del túnel | En Cloudflare, *Actualizar token* del túnel; cámbielo en `compose.env`; `sudo dc up -d cloudflared` | El sitio se corta hasta que el túnel reconecta |
| Clave de la base | `sudo dc exec db psql -U webseba -c "ALTER USER webseba PASSWORD 'NUEVA'"`, luego cámbiela en `compose.env` y en `DATABASE_URL`; `sudo dc up -d` | Corte de segundos |

Rote de inmediato cualquier secreto que haya quedado en un chat, un correo o una captura.

## 10. Cambio al dominio definitivo del cliente

1. Agregue el dominio del cliente a la misma cuenta de Cloudflare (cambio de servidores de nombres en su registrador).
2. En el túnel, agregue un segundo **nombre de host público** con el dominio nuevo, hacia `web:8000`. Repita para él las reglas del paso 3.7.
3. En Resend, **agregue** el dominio nuevo (el plan gratuito admite hasta 3 dominios: el provisional sigue funcionando mientras tanto) y cree sus registros DKIM, SPF y DMARC.
4. En `web.env`: `ALLOWED_HOSTS` con **ambos** nombres, `SITIO_URL` con el nuevo y `CORREO_REMITENTE` con una dirección del dominio nuevo. `sudo dc up -d web`.
5. Compruebe el sitio, un correo de prueba (una cotización) y el monitor, apuntado al nombre nuevo.
6. Pasadas 72 horas (lo que vive un enlace de activación ya enviado), quite el nombre provisional de `ALLOWED_HOSTS` y cree en Cloudflare una regla de redirección del nombre antiguo al nuevo. Después puede quitar el dominio provisional de Resend.
7. Suba HSTS (`SECURE_HSTS_SECONDS=31536000`) cuando el dominio nuevo lleve unos días estable.

Las sesiones abiertas no pasan de un nombre al otro: cada persona vuelve a entrar.

## 11. Paso a producción

Lo decide el responsable cuando se cumple esta lista (también en el README):

1. `contenido_pendiente --estricto` termina sin pendientes, con una política de privacidad real que mencione el almacenamiento en EE. UU.
2. El simulacro de restauración está hecho y anotado en la sección 7.
3. HSTS a un año: `SECURE_HSTS_SECONDS=31536000` en `web.env`. Hoy, en staging, la respuesta lleva `max-age=3600`.
4. Decidido qué hacer con `SECURE_HSTS_INCLUDE_SUBDOMAINS`, según el dominio real del cliente: se activa solo si todos sus subdominios sirven únicamente HTTPS, porque no se deshace rápido. Mientras siga apagado, `check --deploy` muestra `security.W005` y `security.W021`: en staging son las dos advertencias esperadas (`SEGURIDAD.md` §5).
5. El responsable lo aprueba de forma explícita.

La revisión legal (sección 13) es una recomendación documentada, no un requisito de esta lista.

Procedimiento, **VM**:

1. Respalde por última vez el staging: `sudo respaldar.sh`.
2. Borre los datos DEMO: `sudo dc down`, `sudo docker volume rm web-seba_db_datos` y vacíe el bucket de documentos con todas sus versiones (`gcloud storage rm --all-versions "gs://BUCKET-DE-DOCUMENTOS/**"`, desde su cuenta, en Cloud Shell o con `gcloud` en su equipo).
3. Compruebe que `web.env` no tiene la línea `DEMO_PERMITIDO` (`sudo grep -c DEMO_PERMITIDO /etc/web-seba/web.env` debe dar 0). Las instalaciones hechas con la plantilla anterior al 12-10-2026 la traen: bórrela.
4. `sudo desplegar.sh <commit>`, `comprobar_almacenamiento --firma` y `crear_administrador`.
5. Cargue el contenido real en el panel y ejecute `contenido_pendiente --estricto`.
6. Suba HSTS a un año (puntos 3 y 4 de la lista) cuando el sitio lleve unos días estable, y aplíquelo con `sudo dc up -d web`.

## 12. Verificación en staging

Estado tras el primer despliegue real (commit `da83509`), según lo informado por el responsable el 12-10-2026. Lo que no se informó sigue pendiente. La bitácora está al final de la sección.

| Qué | Cómo | Requisito | Estado |
| --- | --- | --- | --- |
| El sitio responde por HTTPS y HTTP redirige | `curl -sI` a ambas | SEG-01 | Pendiente |
| Encabezados de seguridad en la respuesta real | `curl -sI https://seba.fmartinez.xyz/acceso/` | SEG-01, SEG-02 | Verificado el 12-10-2026: CSP, `X-Frame-Options`, `Permissions-Policy` y `Referrer-Policy`. HSTS llega con `max-age=3600` (sección 11) |
| `check --deploy` | Lo ejecuta `desplegar.sh` | SEG-01 | Verificado el 12-10-2026: `desplegar.sh` terminó bien. `security.W005` y `W021` son las esperadas |
| La VM no acepta conexiones | Lista de reglas de firewall; prueba de conexión al puerto 22 y al 443 de su IP | — | Pendiente |
| La auditoría registra la IP real | Un acceso fallido desde su red; mirar el evento en el panel | AUT-04 | Pendiente |
| Bucket: sin firma 403, firma alterada y URL vencida rechazadas | `comprobar_almacenamiento --firma` | DOC-03, DOC-04, prueba 11 | Verificado el 12-10-2026 con el commit `a46c641`, sin las variables `AWS_*` en `web.env`: terminó con "El almacenamiento funciona." La URL vencida respondió 400. El primer intento, con `da83509`, había fallado (bitácora) |
| Subida de 24,9 MB y descarga con el mismo SHA-256 | Por el panel | RNF-02, SEG-07 | Pendiente |
| Correo: llega una cotización con `Reply-To`; SPF, DKIM y DMARC en "pass" | Ver el original del mensaje recibido | SOL-08 | Parcial, 12-10-2026: el aviso de una consulta pública llegó por Resend y la solicitud quedó como enviada. Pendiente: `Reply-To` y SPF, DKIM y DMARC en "pass" |
| Aviso de error 500 y de tarea fallida | `avisar_fallo prueba`; un error provocado | RNF-05 | Pendiente |
| Tareas programadas | `systemctl list-timers 'webseba-*'`, `journalctl -u 'webseba-*'` | SOL-11, ADM-09, AUD-03 | Parcial, 12-10-2026: los cinco temporizadores `webseba-*` están activos, también tras el segundo despliegue. Pendiente: revisar en el journal una ejecución de cada uno |
| Simulacro de restauración | Sección 7 | SEG-11 | Pendiente. Sí se hizo un respaldo manual, que quedó en el bucket de respaldos (12-10-2026) |
| Estáticos desde la caché de Cloudflare | `cf-cache-status: HIT` en la segunda petición | — | Verificado el 12-10-2026: el CSS con `HIT` y el HTML con `DYNAMIC` |
| Lighthouse móvil y tiempos de respuesta | Contra la URL pública | RNF-06, RNF-02 | Pendiente |
| Memoria y swap bajo uso | `free -m`, `docker stats` | RNF-02 | Parcial, 12-10-2026, sin carga: `web` 104 MB, `cloudflared` 25 MB, `db` 9 MB. Pendiente: bajo uso |
| Logs sin el token de los enlaces | `dc logs web` tras usar un enlace de activación | SEG-10 | Pendiente |

Filas nuevas de la Fase B:

| Qué | Cómo | Requisito | Estado |
| --- | --- | --- | --- |
| HEAD responde como GET, sin cuerpo | `curl -sI` a `/`, `/servicios/`, `/contacto/`, `/salud/` y `/privacidad/`: 200. `dc exec -T web python docker/head.py /` | — | Verificado en la VM el 12-10-2026: 200 en `/`, `/servicios/`, `/contacto/`, `/salud/`, `/privacidad/` y `/acceso/`; `/portal/` redirige a `/acceso/?next=/portal/`; `OPTIONS /salud/` y `HEAD /solicitud-recibida/` dan 405; `docker/head.py` informa "200 OK (0 bytes de cuerpo)" |
| Tiempo de arranque de `web` | Sección 5 | RNF-02 | Verificado en la VM el 12-10-2026: unos 5 s (antes, 106 y 144 s) |
| Inicio con la base vacía | Antes de `cargar_demo`: "Sitio en preparación" y el botón Acceso clientes | PUB-05 | Pendiente en la VM: se ve durante el simulacro de restauración (sección 7). En local: verificado el 12-10-2026 |

### Problemas conocidos

- **Sumas de verificación de `boto3` con Google Cloud Storage.** Desde su versión 1.36, `boto3` agrega a cada subida una suma de verificación que la API compatible con S3 de Google rechaza: `PutObject` falla con `SignatureDoesNotMatch: Invalid argument`. La aplicación crea su cliente con las sumas "solo cuando se requieran" (`documentos/almacenamiento.py`, DEC-186). Las variables `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` y `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required`, que se agregaron a mano a `web.env` para salir del paso, **ya no hacen falta**: pueden quedarse, porque dicen lo mismo, o borrarse.
- **URL vencida: 400 en Google, 403 en Amazon.** Con la URL firmada vencida, Google Cloud Storage responde 400 ("Request has expired"). `comprobar_almacenamiento --firma` acepta 400 o 403; cualquier respuesta que entregue el archivo sigue siendo un fallo (DEC-187).
- **Borrar un objeto que no existe: 404 en Google, 204 en Amazon.** El almacenamiento lo trata igual en ambos: no es un error. Antes, si la subida de prueba fallaba, la limpieza respondía `NoSuchKey` y tapaba el error real.
- **`curl -X POST` a una página devuelve 403, no 405.** La comprobación de CSRF va antes que la del método. Para ver un 405 use un método que no modifica nada, por ejemplo `curl -s -o /dev/null -w '%{http_code}\n' -X OPTIONS https://seba.fmartinez.xyz/salud/`.
- **Rutas que no responden a HEAD (405), a propósito** (DEC-188): ver y descargar un documento (dejarían un evento de descarga que no ocurrió), `/acceso/2fa/configurar/` (crea el dispositivo del segundo factor) y `/solicitud-recibida/` (consume el mensaje de confirmación).
- **Dos sesiones de enrolamiento del 2FA a la vez.** Abrir `/acceso/2fa/configurar/` crea el dispositivo pendiente de esa sesión y descarta el que hubiera quedado a medias en otra. Si un administrador tiene abierta esa pantalla en dos navegadores, el código QR del primero deja de valer al abrir el segundo: basta recargar la pantalla y escanear el código nuevo. Solo ocurre durante el enrolamiento, que exige haber usado un enlace de activación o de restablecimiento. Se deja así por decisión del responsable (DEC-192).

### Bitácora de la Fase B

**12-10-2026. Primer despliegue real**, commit `da83509`: VM e2-micro de Google Cloud, Cloud Storage con clave HMAC, Cloudflare Tunnel, `https://seba.fmartinez.xyz`. Informado por el responsable.

Funcionó:

- `preparar.sh` y `desplegar.sh`: migraciones, `/salud/` con 200 y respaldo previo.
- Los cinco temporizadores `webseba-*` activos, y un respaldo manual subido al bucket de respaldos.
- Caché de Cloudflare: el CSS con `HIT` y el HTML con `DYNAMIC`.
- Encabezados: CSP, `X-Frame-Options`, `Permissions-Policy` y `Referrer-Policy`.
- `crear_administrador`, `cargar_demo`, acceso con 2FA del administrador y acceso del cliente, y activación por enlace.
- Validación de archivos: los válidos se aceptaron y los seis inválidos de la prueba 10 se rechazaron, cada uno con su mensaje.
- Consulta pública con el aviso recibido por Resend; la bandeja de Solicitudes la muestra como enviada.
- Descargar y ver en pantalla.
- Aislamiento entre empresas: la dirección de un documento de la empresa 1 responde 404 al usuario de la empresa 2.
- Memoria con todo corriendo: `web` unos 104 MB, `cloudflared` unos 25 MB y `db` unos 9 MB.

Falló, y se corrigió en el commit siguiente:

| # | Qué falló | Corrección | Decisión |
| --- | --- | --- | --- |
| 1 | `PutObject` contra Google Cloud Storage: `SignatureDoesNotMatch: Invalid argument`. En la VM se resolvió con dos variables `AWS_*` en `web.env` | El cliente S3 se crea con las sumas de verificación "solo cuando se requieran" | DEC-186 |
| 2 | `comprobar_almacenamiento --firma`: la URL vencida respondió 400 y el comando esperaba 403; y cuando la subida falló, la limpieza lanzó `NoSuchKey` en vez de mostrar el error real | Acepta 400 o 403; borrar lo que no existe no es un error; el objeto de prueba se borra siempre y se informa el error original | DEC-187 |
| 3 | `curl -I` respondía 405 en `/`, `/servicios/`, `/contacto/`, `/salud/` y `/privacidad/` | Las vistas declaraban solo GET. Ahora toda vista con GET responde a HEAD, salvo las que tienen efectos | DEC-188 |
| 4 | `web` tardó unos 106 s y después unos 144 s en quedar sano, y el sitio no respondió en ese lapso | Gunicorn carga la aplicación una vez; el plazo de arranque del healthcheck pasa a 300 s (sección 5) | DEC-189 |
| 5 | Con la base vacía, el inicio quedaba en blanco entre el encabezado y el pie | Estado "Sitio en preparación", con la fotografía y el botón Acceso clientes | DEC-190 |
| 6 | Esta guía: no decía que `crear_administrador` va antes de `cargar_demo`, y dejaba `DEMO_PERMITIDO` en `web.env` | Secciones 4 y 11; `cargar_demo` recibe el permiso con `-e` | DEC-191 |

Los nombres de los temporizadores y sus comandos se repasaron contra `despliegue/systemd/`: son `webseba-*` en todos los comandos de esta guía. `web-seba` (con guion) es el nombre del proyecto de Compose, de las carpetas `/opt/web-seba`, `/etc/web-seba` y `/var/backups/web-seba`, del volumen `web-seba_db_datos` y del contenedor `web-seba-web-1`: esos no cambian.

**12-10-2026. Segundo despliegue**, commit `a46c641`, con las seis correcciones. Informado por el responsable: todo bien.

- **Arranque de `web`:** el contenedor partió a las 21:06:05 UTC y el primer sondeo sano fue a las 21:06:10: unos 5 s, contra 106 y 144 s.
- **Bucket:** con `web.env` ya sin las variables `AWS_*` ni `DEMO_PERMITIDO`, `comprobar_almacenamiento --firma` terminó con "El almacenamiento funciona.": la URL vencida respondió 400, aceptado, y el paso Borrar salió correcto. La corrección de las sumas de verificación queda confirmada contra Google Cloud Storage real.
- **HEAD:** 200 en `/`, `/servicios/`, `/contacto/`, `/salud/`, `/privacidad/` y `/acceso/`; `/portal/` responde 302 hacia `/acceso/?next=/portal/`; `OPTIONS /salud/` da 405 y `HEAD /solicitud-recibida/` da 405; `docker/head.py` informa "200 OK (0 bytes de cuerpo)".
- **Temporizadores:** los cinco `webseba-*` siguen activos.

Con esto quedan cerrados en la VM los puntos 1 a 4 y el 6 de la tabla de arriba. El punto 5 (inicio con la base vacía) se ve durante el simulacro de restauración.

Pendiente de la etapa, sin ejecutar todavía: el simulacro de restauración, una vuelta atrás a la versión anterior, la subida de 24,9 MB, los logs sin el token, la IP real en la auditoría, los avisos de error, SPF, DKIM y DMARC en un correo recibido, y Lighthouse.

## 13. Solicitud de eliminación de datos

Plazo real de borrado de un documento: hasta 30 días en la papelera, más la purga diaria, más 30 días de versiones antiguas en el bucket. En la base, las filas borradas siguen en los respaldos hasta 14 días.

Si una solicitud exige borrar antes:

1. En el panel, anote el cliente y abra el historial del documento. Antes de eliminarlo, obtenga las claves de sus versiones: `sudo dc exec web python manage.py shell -c "from documentos.models import VersionDocumento; print(*VersionDocumento.objects.filter(documento__uuid='UUID-DEL-DOCUMENTO').values_list('clave', flat=True), sep='\n')"`
2. Elimine el documento en el panel. Para purgarlo ya, el plazo de la papelera no se puede saltar desde la aplicación: es una operación manual en la base, que debe quedar anotada con fecha y motivo.
3. Borre todas las versiones de cada clave en el bucket: `gcloud storage rm --all-versions gs://BUCKET-DE-DOCUMENTOS/CLAVE`.
4. Informe al solicitante que los respaldos de la base vencen solos en 14 días.

## 14. Pendientes legales por el traslado de datos a EE. UU.

Recomendación para la asesoría legal; no bloquea el paso a producción (decisión del responsable, DEC-172). Marco: Ley 19.628 y su reforma por la Ley 21.719. La entrada en vigor de la Ley 21.719 estaba fijada para el 01-12-2026; según informó el responsable, el 01-09-2026 el Gobierno ingresó un proyecto que la posterga al 01-12-2027. **La fecha queda sujeta a ese proyecto**; la recomendación de cumplirla se mantiene.

1. **Transferencia internacional.** Los datos salen de Chile hacia EE. UU.: Google (documentos, base de datos y respaldos), Cloudflare (todo el tráfico) y Resend (correos). Definir la base de licitud y las garantías exigibles.
2. **Datos sensibles.** Los documentos pueden traer datos de salud de trabajadores. Confirmar si su tratamiento por encargo y su traslado requieren algo más.
3. **Contratos de encargo.** Aceptar y archivar los acuerdos de tratamiento de datos (DPA) de Google Cloud, Cloudflare y Resend.
4. **Cloudflare ve el tráfico descifrado**: contraseñas al iniciar sesión y documentos mientras se suben. No los almacena, pero es un encargado más (`SEGURIDAD.md` §8).
5. **Política de privacidad.** Debe informar el almacenamiento en EE. UU. y los encargados. La redacta el responsable del negocio.
6. **Plazos de conservación.** Solicitudes del sitio (hoy sin plazo), auditoría (24 meses), respaldos (14 días), versiones del bucket (30 días) y el plazo real de una eliminación (sección 13).
7. **Derechos de las personas y brechas.** Procedimiento para acceso, rectificación, supresión y portabilidad, y para avisar una brecha de seguridad.
8. **Relación con las empresas cliente.** Quién es responsable y quién encargado de los datos de sus trabajadores, y qué contrato lo respalda.
