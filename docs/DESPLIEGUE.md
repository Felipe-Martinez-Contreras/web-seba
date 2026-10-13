# Despliegue y operación

Cómo se publica y se mantiene la aplicación. Las decisiones están en `DECISIONES.md` (DEC-164 en adelante) y sus riesgos en `SEGURIDAD.md` §8.

**Estado al 12-10-2026.** La aplicación corre en staging, en `https://seba.fmartinez.xyz`. El primer despliegue real (commit `da83509`) dejó seis fallos; el commit `a46c641` los corrigió y, ya desplegado, las correcciones quedaron comprobadas en la VM. El simulacro de restauración y la vuelta atrás también se hicieron ese día. Quedó a la vista un problema de rendimiento, la máquina muy lenta después de cada despliegue, que el commit `3851c7b` resolvió: medido en la VM, el inicio pasó de 28 y 44 s a menos de 0,2 s (bitácora de la sección 12).

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
| Instantáneas del disco de la VM | Programación `default-schedule-1` de Google Cloud | **Con costo**: no entra en el nivel gratuito (sección 7) |

Memoria de la VM (1 GB de RAM; swap comprimida en la propia memoria, zram, y 2 GB de swap en el disco como rebalse):

| Contenedor | Ajuste | Límite |
| --- | --- | --- |
| `web` | Gunicorn con 1 proceso de 4 hilos | 450 MB |
| `db` | `shared_buffers=64MB`, `max_connections=20` | 300 MB |
| `cloudflared` | sin actualización automática | 96 MB |

Medido en la VM el 12-10-2026, con todo corriendo y sin carga: `web` unos 104 MB, `cloudflared` unos 25 MB y `db` unos 9 MB. Más tarde ese día, en reposo: `web` unos 98 MB, `db` unos 26 MB, `cloudflared` unos 28 MB, unos 350 MB disponibles y unos 200 MB de swap en uso.

Cada verificación de contraseña (Argon2id) usa unos 19 MB mientras dura (DEC-198). Con los valores por omisión de Django eran unos 100 MB: cuatro accesos a la vez pedían casi todo el contenedor.

**El disco es el punto débil.** Es un disco persistente estándar de 30 GB, el único gratuito, y rinde muy pocas lecturas por segundo. Cuando la memoria se llena, lo que la máquina tiene que volver a leer del disco tarda minutos. Por eso la configuración busca que eso ocurra lo menos posible; si no alcanza, el plan B está en la sección 7.

**Costo esperado: unos 3,65 USD al mes, no cero.** La IP externa en uso de la VM se cobra a 0,005 USD por hora; el nivel gratuito cubre solo una hora al mes (verificado por el responsable en la página de precios de VPC el 11-10-2026, y aceptado: DEC-184). Lo demás se mantiene en planes gratuitos mientras no se superen sus límites.

**Staging y producción son la misma VM.** Primero corre como staging, con datos DEMO. Cuando se cumple la lista de la sección 11, se vacía y pasa a producción. No hay staging después.

## 2. Qué hay en el repositorio

| Archivo | Para qué |
| --- | --- |
| `Dockerfile` (target `prod`) | Imagen de producción: sin dependencias de desarrollo, estáticos recolectados, usuario sin privilegios, configuración de producción fija |
| `config/gunicorn.py` | Servidor: TCP, hilos, aplicación cargada antes de crear los procesos, logs en JSON sin el token de los enlaces |
| `docker/salud.py`, `docker/head.py` | Comprobaciones desde dentro del contenedor: `/salud/` responde 200 (es el healthcheck, y también precalienta páginas), y HEAD responde sin cuerpo |
| `docker/pendientes.py` | Dice si hay notificaciones por reintentar sin cargar la aplicación |
| `despliegue/compose.prod.yaml` | Los tres contenedores, sin puertos publicados |
| `despliegue/compose.env.example`, `web.env.example` | Plantillas de los dos archivos de variables del servidor |
| `despliegue/vm/preparar.sh` | Prepara la VM: swap (zram y disco), ajustes de memoria, Docker, parches automáticos. Se puede repetir |
| `despliegue/vm/desplegar.sh` | Despliega la imagen de un commit |
| `despliegue/vm/medir.sh` | Mide cuánto resiente la máquina un despliegue |
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

En HetrixTools (plan gratuito), cree un monitor HTTP sobre `https://seba.fmartinez.xyz/salud/` que busque la palabra clave `ok` en la respuesta, con aviso a `CORREO-DEL-RESPONSABLE`. Confirme al registrarse que el plan gratuito admite uso comercial; si no, StatusCake ofrece lo mismo.

Hecho el 12-10-2026: monitor cada 1 minuto, desde 4 ubicaciones. Durante el simulacro de restauración envió el aviso de caída y el de recuperación.

## 4. Primera instalación en la VM

**VM**, en la sesión SSH:

```bash
sudo apt-get update && sudo apt-get install -y git
sudo git clone https://github.com/Felipe-Martinez-Contreras/web-seba.git /opt/web-seba
sudo /opt/web-seba/despliegue/vm/preparar.sh
```

`preparar.sh` deja la zona horaria de Chile, la swap (comprimida en memoria y 2 GB en el disco), los ajustes de memoria del núcleo, Docker, los parches automáticos y dos archivos por completar en `/etc/web-seba/` (solo los lee `root`).

**Se puede volver a ejecutar en una VM ya instalada**, con el sitio en marcha: así se aplican los cambios de este guion. No toca `compose.env` ni `web.env` si ya existen, ni los contenedores, ni las tareas programadas, ni los datos. Para comprobar cómo quedó la memoria:

```bash
sudo zramctl                                # el dispositivo /dev/zram0, con zstd
sudo swapon --show                          # /dev/zram0 con prioridad 100 y /swapfile con prioridad negativa
sudo sysctl vm.swappiness vm.page-cluster   # 100 y 0 con zram; 60 y 3 si el núcleo no la trae
```

Van con `sudo`: esos comandos están en `/usr/sbin`, fuera de la ruta de un usuario normal, y sin él responden "command not found".

Verificado en la VM el 12-10-2026: zram de 482 MB con `zstd` y prioridad 100, `/swapfile` con prioridad -2, `vm.swappiness` en 100 y `vm.page-cluster` en 0.

Si el núcleo de la VM no trae el módulo `zram`, el guion lo avisa y deja solo la swap del disco.

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

El guion deja el código de despliegue en ese commit, baja la imagen, respalda la base en la máquina y ejecuta `preparar_despliegue`: migraciones, tabla de caché y `check --deploy` en un solo proceso. Después reinicia la aplicación, espera a que `/salud/` responda, visita las páginas principales para que la primera carga no la pague un visitante, y programa las tareas. Si la imagen no existe, no cambia nada. Si `check --deploy` encuentra un error, se detiene antes de reiniciar: sigue corriendo la versión anterior.

**El sitio no responde mientras `web` arranca**: el túnel espera a que la aplicación esté sana. Cuánto dura:

| Dónde | Cuánto tardó `web` en quedar sano |
| --- | --- |
| VM, commit `da83509` (12-10-2026) | Unos 106 s la primera vez y unos 144 s después |
| Local, imagen de producción limitada a 0,25 CPU y 450 MB, antes del cambio | Unos 30 s |
| Local, misma prueba, con el cambio (DEC-189) | Unos 20 s |
| VM, commit `a46c641`, con el cambio (12-10-2026) | **Unos 5 s**: el contenedor partió a las 21:06:05 UTC y el primer sondeo sano fue a las 21:06:10 |
| VM, misma versión, justo después de restaurar la base o de cambiar de versión (12-10-2026) | **De 80 a 85 s**: la máquina venía de leer y escribir mucho en el disco |
| VM, commit `3851c7b`, con las mejoras de memoria (12-10-2026) | Redespliegue de la misma versión con `medir.sh`: `desplegar.sh` completo en 34 s y los cinco sondeos sanos. El arranque tras cambiar de versión no se anotó |

La prueba local no reproduce el disco ni la memoria de la e2-micro: sirvió para comparar antes y después, no para predecir la VM, donde la mejora fue mayor. Los 5 s son con la máquina tranquila; con la memoria y el disco ocupados vuelve a ser más de un minuto (última fila). Qué cambió con DEC-189: Gunicorn carga la aplicación una sola vez, antes de crear sus dos procesos (antes cada proceso importaba todo por su cuenta), y el plazo de arranque del healthcheck pasó de 120 a 300 s. Ese plazo no retrasa nada: mientras dura, Docker sondea cada 5 s y marca el contenedor sano con la primera respuesta 200 de `/salud/`, que consulta la base. Con 120 s, el segundo arranque lo superó y el sondeo pasó a ser cada 30 s. Si a los 300 s sigue sin responder, tres fallos seguidos lo marcan como no sano y `desplegar.sh` termina con error.

Pasado el arranque, el sondeo es cada 60 s con un plazo de 30 s, y solo usa un socket (DEC-195). Con el plazo anterior, de 10 s, una máquina ocupada dejaba sondeos sin terminar (`salida=-1`) y el contenedor aparecía como no sano aunque la aplicación solo estaba lenta.

Para medirlo en la **VM**, justo después de desplegar:

```bash
sudo docker inspect --format '{{.State.StartedAt}}{{range .State.Health.Log}}{{"\n"}}{{.Start}} salida={{.ExitCode}}{{end}}' web-seba-web-1
sudo /opt/web-seba/despliegue/vm/dc logs web | head -n 12
```

La primera línea es la hora de inicio del contenedor; las siguientes, los últimos sondeos (`salida=0` es sano). El tiempo de arranque es la diferencia entre el inicio y el primer sondeo con `salida=0`. Docker guarda solo los cinco últimos, así que hay que mirarlo antes de que pasen unos minutos.

**Medir cuánto resiente la máquina un despliegue**, **VM** (unos cinco minutos; el sitio sigue arriba):

```bash
sudo /opt/web-seba/despliegue/vm/medir.sh
```

Vuelve a desplegar la versión que ya está en uso, sin recrear la aplicación, mientras `vmstat` anota la memoria y el disco cada 2 s durante 3 minutos. Después muestra los sondeos del healthcheck, espera 120 s y visita tres veces el inicio por la dirección pública. Termina con un resumen: `wa` máximo (espera de disco), cuántas muestras pasaron de 40 %, lo que entró y salió de la swap (`si`, `so`) y el mínimo de `buff`. Son siempre los mismos pasos: sirve para comparar un antes y un después. Los resultados van en la bitácora de la sección 12.

Referencia del 12-10-2026 con el commit `3851c7b`: `desplegar.sh` en 34 s; precalentamiento de 32 a 67 ms por página; tres visitas al inicio en 0,179, 0,135 y 0,121 s; `wa` máximo de 55 %, con 10 de 90 muestras sobre 40 %, todas durante el despliegue. Antes de las mejoras, las tres visitas tardaron 28,0, 44,3 y 2,0 s.

**Volver atrás:** el mismo comando con el commit anterior (el guion lo muestra al terminar: "antes: …"). Si la versión nueva aplicó una migración que la anterior no entiende, además hay que restaurar el respaldo que el guion dejó en `/var/backups/web-seba/` (sección 7).

Comandos útiles, **VM**:

```bash
sudo /opt/web-seba/despliegue/vm/dc ps
sudo /opt/web-seba/despliegue/vm/dc logs --tail 100 web
sudo /opt/web-seba/despliegue/vm/dc exec -T web python -I -S docker/salud.py   # /salud/ responde 200
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

Las tareas corren dentro del contenedor `web` que ya está en marcha (`dc exec`), no en uno nuevo. `reintentar_notificaciones` corre 96 veces al día y casi nunca tiene trabajo: antes de cargar la aplicación, `tarea.sh` pregunta con `docker/pendientes.py` si hay algo por reintentar, y si no hay, termina ahí (DEC-196).

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
| La VM entera | Programación de instantáneas del disco, `default-schedule-1` (existe en el proyecto; el responsable la informó el 12-10-2026) | La que diga la programación. **Se cobra** por lo almacenado: no es parte del nivel gratuito |

Pérdida máxima de datos: 24 horas en la base (RPO). Recuperación: un día hábil (RTO); en el simulacro del 12-10-2026 la restauración tomó 236 s.

Las instantáneas del disco son un respaldo adicional, no el procedimiento: lo que se prueba y se usa para restaurar es el `pg_dump` del bucket. Revise su costo y su retención en **Compute Engine › Instantáneas**; si no se quieren pagar, se quita la programación del disco.

**Respaldar ahora**, **VM**: `sudo /opt/web-seba/despliegue/vm/respaldar.sh`

**Restaurar**, **VM**:

```bash
gcloud storage ls gs://BUCKET-DE-RESPALDOS/                                   # elegir el respaldo
sudo /opt/web-seba/despliegue/vm/restaurar.sh gs://BUCKET-DE-RESPALDOS/webseba-AAAAMMDDTHHMMSSZ.dump
```

El guion pide escribir el nombre de la base para confirmar, detiene el túnel y la aplicación, reemplaza la base, vuelve a levantar todo y comprueba `/salud/`.

**Recuperar un documento purgado.** Un documento eliminado pasa 30 días en la papelera y se restaura desde el panel. Después, `purgar_papelera` borra su archivo del bucket y sus filas de la base. El bucket conserva el archivo otros 30 días como versión antigua. La VM no puede leer esas versiones: se hace con su cuenta, en Cloud Shell o con `gcloud` en su equipo.

```bash
# La clave es docs/UUID-EMPRESA/UUID-VERSION. Si no la tiene: el evento "documento purgado" de la
# auditoría da la empresa y la fecha, y el listado muestra cuándo se borró cada archivo.
gcloud storage ls --all-versions --long gs://BUCKET-DE-DOCUMENTOS/docs/UUID-EMPRESA/
# Bajar esa generación a un archivo (el número va después del signo #):
gcloud storage cp "gs://BUCKET-DE-DOCUMENTOS/docs/UUID-EMPRESA/UUID-VERSION#GENERACION" recuperado.bin
sha256sum recuperado.bin
```

Con el archivo en la mano hay dos caminos:

- **Lo normal: volver a subirlo por el panel.** La fila del documento ya no existe, así que es un documento nuevo. El archivo no lleva extensión: póngale la que corresponda antes de subirlo.
- **Si además hay que recuperar la fila** (título, historial de versiones): restaure un respaldo de la base anterior a la purga (arriba) y copie la generación sobre su misma clave, para que la base y el bucket vuelvan a coincidir: `gcloud storage cp "gs://…/UUID-VERSION#GENERACION" gs://…/UUID-VERSION`. Restaurar la base devuelve todo lo demás a esa fecha.

Lo mismo sirve para un archivo borrado o reemplazado por error directamente en el bucket.

**Si se pierde la VM entera:** cree otra (pasos 3.2 y 3.3), repita la sección 4 con los mismos valores (el token del túnel y las claves siguen sirviendo; guárdelos en un gestor de contraseñas), despliegue el último commit y restaure el último respaldo. Los documentos no se pierden: están en el bucket.

### Simulacro de restauración

Se hace en staging, antes de cargar documentos reales, y se anota aquí.

El sitio queda caído entre los pasos 4 y 6: el monitor avisará. Todo en la **VM**, salvo donde se indica.

Pegue esto **en cada sesión SSH nueva**: `dc` y `contar` son atajos de la sesión y se pierden al cerrarla. Sin ellos, los comandos de abajo responden "command not found". `contar` imprime los conteos y comprueba que cada versión de documento tenga su archivo en el bucket:

```bash
dc() { sudo /opt/web-seba/despliegue/vm/dc "$@"; }
B=$(sudo grep -oP '^RESPALDOS_BUCKET=\K.*' /etc/web-seba/compose.env)
contar() { dc exec -T web python manage.py shell -c "
from cuentas.models import Usuario
from empresas.models import Empresa
from documentos.models import Documento, VersionDocumento
from documentos.almacenamiento import almacen
from solicitudes.models import Solicitud
from auditoria.models import EventoAuditoria
from django_otp.plugins.otp_totp.models import TOTPDevice
print('empresas', Empresa.objects.count(), '| usuarios', Usuario.objects.count(), '| 2FA', TOTPDevice.objects.filter(confirmed=True).count(), '| documentos', Documento.objects.count(), '| versiones', VersionDocumento.objects.count(), '| solicitudes', Solicitud.objects.count(), '| eventos', EventoAuditoria.objects.count())
a = almacen()
faltan = [v.clave for v in VersionDocumento.objects.all() if not a.existe(v.clave)]
print('versiones sin su archivo en el bucket:', len(faltan), faltan[:5])"; }
```

1. Con los datos DEMO cargados, suba un PDF propio por el panel y anote su SHA-256 (**PowerShell**: `(Get-FileHash archivo.pdf -Algorithm SHA256).Hash`). Deje al menos una solicitud en la bandeja.
2. `contar`, y guarde la salida. Desde aquí no use el sitio hasta el paso 4: cada acceso suma eventos.
3. Respalde y deje una copia aparte. La carpeta de respaldos solo la lee `root`, por eso el comodín va dentro de `sudo sh -c`:

   ```bash
   sudo /opt/web-seba/despliegue/vm/respaldar.sh
   gcloud storage ls --long "gs://$B/" | tail -n 3
   sudo sh -c 'cp "$(ls -t /var/backups/web-seba/webseba-*.dump | head -n 1)" /root/simulacro.dump'
   dc exec -T db pg_restore --list < <(sudo cat /root/simulacro.dump) > /dev/null && echo "respaldo legible"
   ```

   La copia en `/root` importa: el paso 5 crea otro respaldo local, de la base vacía, y en la VM solo quedan los tres más recientes.
4. **Destruya la base. No se puede deshacer:** se pierde lo escrito después del respaldo. El bucket de documentos no se toca. `dc down` y `sudo docker volume rm web-seba_db_datos`.
5. `sudo /opt/web-seba/despliegue/vm/desplegar.sh <commit>` sobre la base vacía. `contar` debe dar todo en 0 y el inicio debe mostrar "Sitio en preparación". No ejecute `crear_administrador` ni `cargar_demo`.
6. `sudo /opt/web-seba/despliegue/vm/restaurar.sh "gs://$B/webseba-AAAAMMDDTHHMMSSZ.dump"`. Anote los segundos que informa.
7. Compruebe: `contar` con los mismos números y `0 []` en el bucket; el administrador entra con el código de la misma aplicación, sin enrolar de nuevo; los clientes DEMO y la solicitud están; el PDF del paso 1 se descarga con el mismo SHA-256; un cliente descarga desde el portal.
8. **Eliminar, purgar y recuperar del bucket** (abajo).

Si algo sale mal a medio camino: `desplegar.sh` se puede repetir. Si `restaurar.sh` falla después de borrar la base, la aplicación y el túnel quedan detenidos: repítalo con la copia local, `sudo /opt/web-seba/despliegue/vm/restaurar.sh /root/simulacro.dump`.

**Paso 8: purgar sin esperar 30 días.** La purga solo borra lo que lleva más de `PAPELERA_DIAS` en la papelera, y eso no se cambia. En el simulacro se adelanta, a mano, la fecha de eliminación de **ese** documento. Es una edición directa de la base que no deja evento de auditoría: **solo en staging, con datos DEMO**.

```bash
# 1. Antes de eliminarlo: el listado de documentos, con su identificador, empresa, título,
#    clave en el bucket y SHA-256. Elija uno y anote su línea completa.
dc exec -T web python manage.py shell -c "
from documentos.models import Documento
for d in Documento.objects.filter(eliminado_en__isnull=True).select_related('empresa', 'version_vigente').order_by('empresa__razon_social', 'titulo'):
    print(d.pk, '|', d.empresa, '|', d.titulo, '|', d.version_vigente.clave, '|', d.version_vigente.sha256)"

# El identificador del elegido (la primera columna). Se usa el identificador y no el título:
# dos empresas pueden tener documentos con el mismo título.
PK=IDENTIFICADOR-DEL-DOCUMENTO

# 2. Elimínelo en el panel (queda en la papelera).

# 3. Adelantar su fecha de eliminación. Debe imprimir 1; un 0 dice que el identificador está
#    mal o que el documento no está en la papelera.
dc exec -T web python manage.py shell -c "
import datetime
from django.utils import timezone
from documentos.models import Documento
print(Documento.objects.filter(pk='$PK', eliminado_en__isnull=False).update(eliminado_en=timezone.now() - datetime.timedelta(days=31)))"

# 4. La purga de todos los días. Debe decir: Se borraron definitivamente 1 documentos…
sudo /opt/web-seba/despliegue/vm/tarea.sh purgar_papelera
contar
```

Tras el punto 4, `contar` muestra un documento y una versión menos, y un evento más (la purga). El punto 5 es recuperar el archivo con los comandos de "Recuperar un documento purgado", usando la clave del punto 1, y comparar su SHA-256 con el anotado.

**Hecho en staging el 12-10-2026:** un documento de Empresa Dos. La actualización de la fecha devolvió 1; `purgar_papelera` informó "Se borraron definitivamente 1 documentos"; `contar` pasó de 8 documentos y 8 versiones a 7 y 7, de 31 a 33 eventos, con `0 []` en el bucket. En Cloud Shell, `ls --all-versions` mostró la generación no vigente, de 1.677 bytes, y el `sha256sum` del archivo recuperado fue idéntico al anotado. Ese día los comandos 1 y 3 buscaban por título; después se cambiaron al identificador, y esa forma está probada en local contra la base de desarrollo.

| Fecha | Quién | Respaldo usado | Conteos antes / después | SHA-256 coincide | Tiempo | Resultado |
| --- | --- | --- | --- | --- | --- | --- |
| 12-10-2026 | Responsable | `gs://BUCKET-DE-RESPALDOS/webseba-20261012T213004Z.dump` | Antes: 2 empresas, 3 usuarios, 1 con 2FA, 8 documentos, 8 versiones, 1 solicitud, 26 eventos. Con la base vacía: todo en 0. Después: lo mismo que antes, con 27 eventos. Versiones sin su archivo en el bucket: 0 antes y después | Sí: el PDF subido y el descargado tras restaurar son idénticos | `restaurar.sh`: 236 s | **Correcto.** El administrador entró con su 2FA sin enrolar de nuevo; el portal del cliente y su descarga funcionaron; el monitor avisó la caída y la recuperación. El paso 8 (purga y recuperación del bucket) se hizo más tarde ese día, ya rediseñado: correcto, con el mismo SHA-256 en el archivo recuperado |

El evento de diferencia (26 antes, 27 después) no se investigó: es coherente con una acción en el sitio entre el conteo y el respaldo, pero no está comprobado. El nombre real del bucket no se escribe en este repositorio.

Lo comprobado hasta ahora, en local el 11-10-2026 con la imagen de producción: `pg_dump`, borrado de la base, `pg_restore`, migraciones al día y la extensión `unaccent` presente tras restaurar. **No reemplaza al simulacro**: faltan el bucket, los guiones en la VM y los documentos.

### Plan B: una VM nueva con disco equilibrado

**Documentado, no ejecutado, y por ahora no hace falta:** con las mejoras de memoria aplicadas, la medición del 12-10-2026 quedó bien (sección 12).

**Cuándo activarlo.** Si cualquiera de estas cosas se repite varios días, con la zram activa (`sudo swapon --show`):

- una visita al inicio tarda más de 2 s **fuera de un despliegue**, una restauración o el respaldo de las 02:30;
- `vmstat 2 30` muestra `wa` sobre 40 % de forma sostenida fuera de esos momentos;
- el monitor avisa caídas que coinciden con sondeos del healthcheck fallidos (`salida` distinta de 0 en `docker inspect`);
- `medir.sh` vuelve a dar visitas de varios segundos 120 s después del despliegue.

Una espera de disco alta **durante** un despliegue es normal en este disco y no es motivo.

El disco estándar es gratuito, pero rinde muy pocas operaciones por segundo. Un disco persistente **equilibrado** (`pd-balanced`) de 10 GB rinde muchas más y cuesta cerca de **1 USD al mes** (unos 0,10 USD por GB; confirme el precio vigente de `us-east1` antes de crearlo). El tipo de un disco de arranque no se cambia en el lugar: lo más simple es una VM nueva. El costo mensual pasaría de unos 3,65 a unos 4,65 USD; ajuste la alerta de presupuesto (paso 3.1).

Antes de empezar, en la VM actual: `df -h /` debe mostrar menos de unos 7 GB usados, para que todo quepa en 10 GB.

1. **VM actual:** guarde en su gestor de contraseñas el contenido de `/etc/web-seba/compose.env` y de `/etc/web-seba/web.env` (`sudo cat`). Anote el commit en uso: `sudo grep WEB_SEBA_VERSION /etc/web-seba/compose.env`.
2. **Consola:** cree la VM nueva como en el paso 3.2, con un cambio: disco de arranque **Disco persistente equilibrado, 10 GB**. La misma cuenta de servicio `vm-web-seba`. La regla de firewall del paso 3.3 ya la cubre.
3. **VM nueva:** la sección 4 hasta completar los dos archivos, con los mismos valores. **No despliegue todavía.**
4. **VM actual:** corte la entrada y respalde. Desde aquí el sitio está caído.

   ```bash
   sudo /opt/web-seba/despliegue/vm/dc stop cloudflared
   sudo /opt/web-seba/despliegue/vm/respaldar.sh
   ```

   **El orden importa.** Las dos máquinas usan el mismo token del túnel: si el `cloudflared` de la actual sigue corriendo cuando arranque el de la nueva, Cloudflare reparte las visitas entre las dos, cada una con su base.
5. **VM nueva:** `sudo /opt/web-seba/despliegue/vm/desplegar.sh <commit>` y después `sudo /opt/web-seba/despliegue/vm/restaurar.sh gs://BUCKET-DE-RESPALDOS/<el respaldo del paso 4>`.
6. **VM nueva:** compruebe con `contar` (simulacro, arriba) que los conteos coinciden y que no falta ningún archivo, entre con 2FA, descargue un documento, ejecute `comprobar_almacenamiento` y `systemctl list-timers 'webseba-*'`. El monitor debe volver a "arriba".
7. **Consola:** **detenga** la VM antigua en cuanto la nueva esté comprobada. Encendida, seguiría subiendo cada noche respaldos de una base que ya no es la vigente. Bórrela unos días después, junto con su disco, y quite o mueva la programación de instantáneas.

**Volver atrás** antes del paso 7: `dc stop cloudflared` en la nueva y `dc start cloudflared` en la antigua. Lo escrito en la nueva entre medio se pierde.

El corte esperado es de unos 10 a 15 minutos: en el simulacro, sobre el disco estándar, la restauración tomó 236 s.

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
| Sacar a un archivo el contenido del sitio | `exportar_contenido -` con `-T` y `> archivo` (sección 11) |
| Cargar ese archivo en una base sin contenido | `importar_contenido -` con `-T` y `< archivo` (sección 11) |

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
2. **Exporte el contenido del sitio**, si lo cargó en el panel de staging (más abajo, "Llevar el contenido de staging a producción"). Hágalo **antes** del paso siguiente: borrar la base se lleva también ese contenido.
3. Borre los datos DEMO: `sudo dc down`, `sudo docker volume rm web-seba_db_datos` y vacíe el bucket de documentos con todas sus versiones (`gcloud storage rm --all-versions "gs://BUCKET-DE-DOCUMENTOS/**"`, desde su cuenta, en Cloud Shell o con `gcloud` en su equipo).
4. Compruebe que `web.env` no tiene la línea `DEMO_PERMITIDO` (`sudo grep -c DEMO_PERMITIDO /etc/web-seba/web.env` debe dar 0). Las instalaciones hechas con la plantilla anterior al 12-10-2026 la traen: bórrela.
5. `sudo desplegar.sh <commit>`, `comprobar_almacenamiento --firma` y `crear_administrador`.
6. **Importe el contenido** exportado en el paso 2 (más abajo). Si no lo exportó, cárguelo a mano en Panel › Configuración › Contenido del sitio.
7. Ejecute `contenido_pendiente --estricto`: debe terminar sin pendientes.
8. Suba HSTS a un año (puntos 3 y 4 de la lista) cuando el sitio lleve unos días estable, y aplíquelo con `sudo dc up -d web`.

### Llevar el contenido de staging a producción

`exportar_contenido` escribe en un archivo JSON los datos del negocio y los servicios, y nada más: ni usuarios, ni empresas, ni documentos, ni solicitudes, ni auditoría. `importar_contenido` lo carga en la base nueva (DEC-200, DEC-201).

**El archivo trae datos de contacto** (teléfono, correo, WhatsApp). No lo guarde en la carpeta del proyecto ni lo pegue en un chat. Si alguna vez queda dentro del proyecto, el nombre `contenido-sitio*.json` está en `.gitignore` y en `.dockerignore`.

Los dos comandos existen desde la versión del 13-10-2026: despliéguela en staging antes de exportar (sección 5).

**Paso 2: exportar.** **VM**, en la sesión SSH:

```bash
cd ~ && umask 077
sudo /opt/web-seba/despliegue/vm/dc exec -T web python manage.py exportar_contenido - > contenido-sitio.json
sha256sum contenido-sitio.json
realpath contenido-sitio.json
```

El comando responde `Exportado: datos del negocio y N servicios.` Lea también lo que diga debajo, porque los datos de `cargar_demo` **no viajan**:

- `Datos de prueba que se exportaron vacíos: …`: esos campos todavía tenían el texto DEMO. Complételos en el panel y exporte de nuevo, o complételos en producción después de importar.
- `Servicios de prueba omitidos: N`: los servicios DEMO que quedaron, activos o no.
- `Identificador de demostración reemplazado: servicio-demo-1 -> …`: un servicio real escrito encima de uno DEMO conservaba la dirección `servicio-demo-N`; en el archivo lleva una derivada de su nombre.

Para **bajar el archivo a su equipo**: en la ventana SSH del navegador, botón **Descargar archivo** (*Download file*), y escriba la ruta que mostró `realpath`. En **PowerShell**, `Get-FileHash .\contenido-sitio.json -Algorithm SHA256` debe dar la misma suma que `sha256sum` (PowerShell la muestra en mayúsculas). Guárdelo fuera de la carpeta del proyecto.

El archivo puede quedarse también en su carpeta de la VM: el paso 3 borra la base y el bucket, no su carpeta personal. La copia en su equipo es el resguardo.

**Paso 6: importar.** Si el archivo ya no está en la VM, súbalo con el botón **Subir archivo** (*Upload file*) de la ventana SSH: queda en su carpeta personal. **VM**:

```bash
cd ~
sha256sum contenido-sitio.json      # la misma suma del paso 2
sudo /opt/web-seba/despliegue/vm/dc exec -T web python manage.py importar_contenido - < contenido-sitio.json
# Comparar: lo que quedó en la base, exportado de nuevo, debe ser idéntico al archivo.
sudo /opt/web-seba/despliegue/vm/dc exec -T web python manage.py exportar_contenido - | cmp - contenido-sitio.json && echo IGUALES
rm contenido-sitio.json
```

`importar_contenido` responde `Importado: N datos del negocio y N servicios.` Repetirlo no duplica nada: responde `El contenido ya estaba cargado: no se cambió nada.` Si falla, no modifica la base y dice por qué:

| Mensaje | Qué pasó |
| --- | --- |
| `claves inesperadas`, `faltan claves`, `lleva una marca de datos de prueba`, o un campo con su error | El archivo no es el que escribió `exportar_contenido`, o se editó a mano. El mensaje dice dónde, nunca el valor |
| `El archivo tiene el formato de dumpdata` | Es una copia hecha con `dumpdata`, que trae claves internas y los servicios DEMO. No se importa: exporte de nuevo |
| `La base ya tiene otro contenido` | La base no está vacía y lo que tiene no coincide con el archivo. El comando solo carga sobre una base sin contenido; nunca pisa lo que se escribió en el panel |

Los botones de la ventana SSH no se probaron al escribir esta guía. Alternativa desde su equipo, con `gcloud` instalado: `gcloud compute scp --tunnel-through-iap VM:contenido-sitio.json .` para bajar, y con los argumentos al revés para subir.

## 12. Verificación en staging

Estado tras el primer despliegue real (commit `da83509`), según lo informado por el responsable el 12-10-2026. Lo que no se informó sigue pendiente. La bitácora está al final de la sección.

| Qué | Cómo | Requisito | Estado |
| --- | --- | --- | --- |
| El sitio responde por HTTPS y HTTP redirige | `curl -sI` a ambas | SEG-01 | Verificado el 13-10-2026: `curl -sI http://seba.fmartinez.xyz/` respondió 301 con `location: https://seba.fmartinez.xyz/`. La respuesta por HTTPS ya estaba verificada el 12-10-2026 (fila siguiente) |
| Encabezados de seguridad en la respuesta real | `curl -sI https://seba.fmartinez.xyz/acceso/` | SEG-01, SEG-02 | Verificado el 12-10-2026: CSP, `X-Frame-Options`, `Permissions-Policy` y `Referrer-Policy`. HSTS llega con `max-age=3600` (sección 11) |
| `check --deploy` | Lo ejecuta `desplegar.sh` | SEG-01 | Verificado el 12-10-2026: `desplegar.sh` terminó bien. `security.W005` y `W021` son las esperadas |
| La VM no acepta conexiones | Lista de reglas de firewall; prueba de conexión al puerto 22 y al 443 de su IP | — | Verificado el 13-10-2026 desde la red del responsable (**PowerShell**, `Test-NetConnection` a la IP pública de la VM): puertos 22 y 443 con `TcpTestSucceeded: False`, y el ping sin respuesta. La IP no se anota aquí: el repositorio es público. No se informó la lista de reglas de firewall |
| La auditoría registra la IP real | Un acceso fallido desde su red; mirar el evento en el panel | AUT-04 | Cubierta por pruebas automáticas; no verificada a mano en staging (decisión del responsable, 12-10-2026): `core/tests/test_ip.py` (`test_detras_de_cloudflared_la_ip_sale_de_cf_connecting_ip`, `test_un_encabezado_enviado_por_un_origen_que_no_es_de_confianza_se_ignora`) y `cuentas/tests/test_acceso_bloqueo.py` (`test_en_produccion_la_auditoria_anota_la_ip_del_visitante_solo_si_viene_del_tunel`). Comprobado además con la imagen de producción en local el 11 y el 12-10-2026 |
| Bucket: sin firma 403, firma alterada y URL vencida rechazadas | `comprobar_almacenamiento --firma` | DOC-03, DOC-04, prueba 11 | Verificado el 12-10-2026 con el commit `a46c641`, sin las variables `AWS_*` en `web.env`: terminó con "El almacenamiento funciona." La URL vencida respondió 400. El primer intento, con `da83509`, había fallado (bitácora) |
| Subida de 24,9 MB y descarga con el mismo SHA-256 | Por el panel | RNF-02, SEG-07 | Pendiente, opcional: no se ejecutó en staging. En local, verificado el 11-10-2026 |
| Correo: llega una cotización con `Reply-To`; SPF, DKIM y DMARC en "pass" | Ver el original del mensaje recibido | SOL-08 | Verificado el 12-10-2026 en Gmail, en el aviso de una consulta: SPF, DKIM y DMARC en PASS, y la solicitud quedó como enviada. `Reply-To` no se informó: lo cubre `test_sol_08_el_correo_al_profesional_lleva_los_datos_el_enlace_y_el_reply_to` |
| Aviso de error 500 y de tarea fallida | `avisar_fallo prueba`; un error provocado | RNF-05 | Verificado el 12-10-2026 el aviso de tarea fallida: `avisar_fallo prueba` respondió "Aviso enviado." y el correo "[seba.fmartinez.xyz] Falló la tarea programada prueba" llegó al instante a la bandeja de entrada, sin datos sensibles. No se provocó en staging un error 500 real ni el fallo de una tarea por systemd: el primero lo cubre `core/tests/test_avisos.py` (`test_un_error_real_en_una_vista_llega_por_el_log_de_django`) |
| Tareas programadas | `systemctl list-timers 'webseba-*'`, `journalctl -u 'webseba-*'` | SOL-11, ADM-09, AUD-03 | Verificado en el journal de la VM, salvo la tarea mensual. `webseba-reintentar`: 15 ejecuciones seguidas con "Finished" el 12-10-2026, entre las 17:31 y las 21:01, sin fallos. Primera ejecución automática de las nocturnas, el 13-10-2026, todas con "Finished": respaldo a las 02:30:38, `purgar_papelera` a las 03:20:38 y `clearsessions` a las 03:40:33. **Pendiente hasta el 01-11-2026:** `webseba-auditoria`, que corre el día 1 de cada mes |
| Simulacro de restauración | Sección 7 | SEG-11 | Verificado en la VM el 12-10-2026, desde el bucket de respaldos: mismos conteos, base y bucket coherentes, mismo SHA-256, 2FA sin enrolar de nuevo, 236 s (tabla de la sección 7). El paso 8 también: un documento purgado se recuperó de las versiones del bucket con el mismo SHA-256 |
| Estáticos desde la caché de Cloudflare | `cf-cache-status: HIT` en la segunda petición | — | Verificado el 12-10-2026: el CSS con `HIT` y el HTML con `DYNAMIC` |
| Lighthouse móvil y tiempos de respuesta | Contra la URL pública | RNF-06, RNF-02 | Pendiente, opcional: no se ejecutó en staging. En local dio de 98 a 100. Los tiempos de respuesta tras un despliegue sí están medidos (bitácora) |
| Memoria y swap bajo uso | `free -m`, `docker stats`, `medir.sh` | RNF-02 | Verificado en la VM el 12-10-2026 con el commit `3851c7b`: tras un despliegue, el inicio responde en 0,12 a 0,18 s (antes 28 y 44 s), los sondeos salen sanos y quedan 381 MB disponibles, con la zram activa (DEC-193 a DEC-196 y DEC-198; bitácora). Pendiente: medirlo con varios usuarios a la vez |
| Logs sin el token de los enlaces | `dc logs web` tras usar un enlace de activación | SEG-10 | Cubierta por pruebas automáticas; no verificada a mano en staging (decisión del responsable, 12-10-2026): `core/tests/test_vistas.py` (`test_los_logs_no_registran_el_token_de_los_enlaces`), `config/tests/test_gunicorn.py` (`test_el_log_de_acceso_de_gunicorn_no_registra_el_token_de_los_enlaces`, `test_el_log_de_acceso_no_lleva_la_consulta_ni_la_ip`, `test_el_log_de_acceso_no_lleva_la_url_firmada_de_una_descarga`), `documentos/tests/test_entrega.py` (`test_con_s3_la_url_firmada_no_queda_en_los_logs_ni_en_la_auditoria`) y `cuentas/tests/test_enlaces.py` (`test_ni_el_token_ni_la_contrasena_quedan_en_la_auditoria`) |

Filas nuevas de la Fase B:

| Qué | Cómo | Requisito | Estado |
| --- | --- | --- | --- |
| HEAD responde como GET, sin cuerpo | `curl -sI` a `/`, `/servicios/`, `/contacto/`, `/salud/` y `/privacidad/`: 200. `dc exec -T web python docker/head.py /` | — | Verificado en la VM el 12-10-2026: 200 en `/`, `/servicios/`, `/contacto/`, `/salud/`, `/privacidad/` y `/acceso/`; `/portal/` redirige a `/acceso/?next=/portal/`; `OPTIONS /salud/` y `HEAD /solicitud-recibida/` dan 405; `docker/head.py` informa "200 OK (0 bytes de cuerpo)" |
| Tiempo de arranque de `web` | Sección 5 | RNF-02 | Verificado en la VM el 12-10-2026: unos 5 s (antes, 106 y 144 s) |
| Inicio con la base vacía | Antes de `cargar_demo`: "Sitio en preparación" y el botón Acceso clientes | PUB-05 | Verificado en la VM el 12-10-2026, durante el simulacro: con la base vacía el inicio mostró "Sitio en preparación" |
| Vuelta atrás y regreso | `desplegar.sh` con el commit anterior y de nuevo con el actual | — | Verificado en la VM el 12-10-2026: a `da83509` (`web` sano en 83 s, HEAD con 405, como se esperaba de esa versión) y de regreso a `a46c641` (80 s, HEAD con 200, `comprobar_almacenamiento` correcto). Sin migraciones de por medio |
| Monitor de disponibilidad | Paso 3.10 | RNF-05 | Verificado el 12-10-2026: avisó la caída y la recuperación durante el simulacro |

### Problemas conocidos

- **Sumas de verificación de `boto3` con Google Cloud Storage.** Desde su versión 1.36, `boto3` agrega a cada subida una suma de verificación que la API compatible con S3 de Google rechaza: `PutObject` falla con `SignatureDoesNotMatch: Invalid argument`. La aplicación crea su cliente con las sumas "solo cuando se requieran" (`documentos/almacenamiento.py`, DEC-186). Las variables `AWS_REQUEST_CHECKSUM_CALCULATION=when_required` y `AWS_RESPONSE_CHECKSUM_VALIDATION=when_required`, que se agregaron a mano a `web.env` para salir del paso, **ya no hacen falta**: pueden quedarse, porque dicen lo mismo, o borrarse.
- **URL vencida: 400 en Google, 403 en Amazon.** Con la URL firmada vencida, Google Cloud Storage responde 400 ("Request has expired"). `comprobar_almacenamiento --firma` acepta 400 o 403; cualquier respuesta que entregue el archivo sigue siendo un fallo (DEC-187).
- **Borrar un objeto que no existe: 404 en Google, 204 en Amazon.** El almacenamiento lo trata igual en ambos: no es un error. Antes, si la subida de prueba fallaba, la limpieza respondía `NoSuchKey` y tapaba el error real.
- **`curl -X POST` a una página devuelve 403, no 405.** La comprobación de CSRF va antes que la del método. Para ver un 405 use un método que no modifica nada, por ejemplo `curl -s -o /dev/null -w '%{http_code}\n' -X OPTIONS https://seba.fmartinez.xyz/salud/`.
- **Rutas que no responden a HEAD (405), a propósito** (DEC-188): ver y descargar un documento (dejarían un evento de descarga que no ocurrió), `/acceso/2fa/configurar/` (crea el dispositivo del segundo factor) y `/solicitud-recibida/` (consume el mensaje de confirmación).
- **Dos sesiones de enrolamiento del 2FA a la vez.** Abrir `/acceso/2fa/configurar/` crea el dispositivo pendiente de esa sesión y descarta el que hubiera quedado a medias en otra. Si un administrador tiene abierta esa pantalla en dos navegadores, el código QR del primero deja de valer al abrir el segundo: basta recargar la pantalla y escanear el código nuevo. Solo ocurre durante el enrolamiento, que exige haber usado un enlace de activación o de restablecimiento. Se deja así por decisión del responsable (DEC-192).

- **La VM quedaba muy lenta después de un despliegue. Resuelto el 12-10-2026** con el commit `3851c7b` (bitácora). Era falta de memoria sobre un disco de muy pocas operaciones por segundo, con la swap en ese mismo disco. Lo que queda: **durante** un despliegue la CPU todavía espera al disco (`wa` hasta 55 %), unos segundos cada vez. Si la lentitud vuelve fuera de los despliegues, el criterio y el plan B están en la sección 7.
- **`preparar.sh` podía avisar que la zram no se activó, y sí estaba activa.** En su primera ejecución en la VM (12-10-2026) revisó antes de que systemd terminara de crear el dispositivo, y dejó `swappiness=60` y `page-cluster=3`. Al repetirlo quedó bien. Desde el commit siguiente espera hasta 30 s antes de decidir.

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

**12-10-2026. Simulacro de restauración, vuelta atrás y rendimiento.** Informado por el responsable, con el commit `a46c641`.

- **Simulacro de restauración: correcto.** Detalle en la tabla de la sección 7. Con la base vacía, el inicio mostró "Sitio en preparación": queda cerrado el punto 5 de la tabla de arriba.
- **Vuelta atrás: correcta.** A `da83509` (`web` sano en 83 s; HEAD con 405, propio de esa versión) y de regreso a `a46c641` (80 s; HEAD con 200; `comprobar_almacenamiento` correcto).
- **Monitor:** HetrixTools sobre `/salud/`, cada minuto y desde 4 ubicaciones; avisó la caída y la recuperación.
- **Instantáneas:** el disco tiene la programación `default-schedule-1` de Google Cloud. Es un respaldo adicional, con costo.
- **Dos pasos de la guía no se podían ejecutar** y se corrigieron: listar la carpeta de respaldos sin ser `root`, y purgar un documento sin esperar 30 días (sección 7).

**Rendimiento: línea base, antes de las mejoras.** VM e2-micro con 964 MB de RAM, 2 GB de swap en el mismo disco, `swappiness=10`, Gunicorn 2 × 2.

| Qué | Medido |
| --- | --- |
| Inicio con la VM tranquila | 6,77 s la primera visita; 0,11 a 0,14 s las siguientes |
| Inicio dos minutos después de redesplegar la misma versión (sin recrear `web`) | 28,0 s, 44,3 s y 2,0 s |
| `vmstat` durante ese lapso | `st` 0 todo el tiempo; `wa` de 40 a 76 % durante minutos; `buff` de 8.820 a 244; `si`/`so` hasta 534/1.036; cola `r` hasta 23 |
| Un minuto aparte | `us` de 87 a 91 % con `r` de 11. Origen sin identificar |
| Healthcheck | Cuatro sondeos seguidos con `salida=-1` tras un despliegue; "unhealthy" pasajero en otra ocasión |
| Arranque de `web` | 5 s con la VM tranquila; 80 a 85 s después de restaurar o de cambiar de versión |
| Memoria en reposo | `web` 98 MB, `db` 26 MB, `cloudflared` 28 MB; 350 MB disponibles; 200 MB de swap en uso |

Lectura: no hay robo de CPU (`st` en 0). La memoria se llena, el núcleo bota el caché de archivos y manda memoria de los procesos a la swap, y todo eso vuelve desde un disco estándar que rinde muy pocas lecturas por segundo.

Lo que se cambió (un commit, sin desplegar al escribir esto):

| Cambio | Medido en local (imagen de producción, 0,25 CPU y 450 MB) | Decisión |
| --- | --- | --- |
| Swap comprimida en memoria (zram) antes que la del disco; `swappiness` de 10 a 100 con zram, o a 60 sin ella | **No se puede probar en local.** En Debian 13 el paquete existe y respeta la configuración del guion | DEC-193 |
| Gunicorn: 1 proceso de 4 hilos en vez de 2 de 2 | Unos 25 MB menos tras la misma carga (154 contra 180 MB), con la misma latencia en páginas y en accesos | DEC-194 |
| Healthcheck solo con un socket, cada 60 s, con plazo de 30 s | El sondeo pasa de unos 2,0 s a unos 0,8 s y carga 59 módulos en vez de 116 | DEC-195 |
| Despliegue: `migrate`, `createcachetable` y `check --deploy` en un proceso; precalentamiento de 5 páginas. Tarea de reintentos: consulta liviana antes de cargar la aplicación | Un arranque de la aplicación en vez de tres por despliegue. La tarea sin pendientes: 1,3 s de CPU y 38 MB, contra 2,4 s y 68 MB | DEC-196 |
| Argon2id con 19 MiB, 2 pasadas y 1 hilo | Un acceso: de 4,2 s y 118 MB a 0,31 s y 38 MB. Cuatro a la vez: de 37 s y 415 MB a 1,7 s y 87 MB | DEC-198 |

**12-10-2026. Las mejoras, medidas en la VM: resuelto.** Commit `3851c7b`, aplicado con `preparar.sh`, `desplegar.sh` y `medir.sh`. Informado por el responsable.

- **Memoria:** zram de 482 MB con `zstd` y prioridad 100; `/swapfile` con prioridad -2; `vm.swappiness` 100 y `vm.page-cluster` 0; 381 MB disponibles después de la medición.
- **Precalentamiento:** de 32 a 67 ms por página.
- **Healthcheck:** los cinco sondeos con `salida=0`.
- **El minuto de CPU al 90 % no volvió a aparecer:** ninguna muestra con `us` de 80 % o más. El diagnóstico previo no se ejecutó porque dejó de hacer falta; su origen quedó sin identificar.
- **`si` y `so` suman más que antes y no es un problema:** ahora la swap es memoria comprimida, no disco. Lo que importa es `wa` y el tiempo de respuesta.
- **Plan B:** no es necesario por ahora. Queda documentado, con el criterio para activarlo, en la sección 7.

| Fecha | Versión | `desplegar.sh` | `wa` máximo y muestras sobre 40 % | Suma `si` / `so` | `buff` mínimo | Sondeos fallidos | Tres visitas al inicio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12-10-2026, antes | `a46c641` | Sin anotar | 76 %; "durante minutos" | Máximos de 534 / 1.036 por muestra | 244 | 4 | 28,0 s, 44,3 s y 2,0 s |
| 12-10-2026, después | `3851c7b` | 34 s | 55 %; 10 de 90 muestras, todas durante el despliegue | Sumas de 8.693 / 25.128, hacia la zram | 1.840 | 0 | 0,179 s, 0,135 s y 0,121 s |

Las dos filas no son comparables columna por columna en `si` y `so`: la primera anota máximos por muestra y la segunda, sumas. En la segunda, la cola `r` llegó a 8 (antes 23) y `st` siguió en 0.

**12-10-2026. Cierre de las verificaciones de la Fase B.** Informado por el responsable.

- **Paso 8 del simulacro: correcto.** Un documento de Empresa Dos se eliminó, se purgó con la tarea normal y se recuperó en Cloud Shell desde las versiones del bucket: generación no vigente de 1.677 bytes, mismo SHA-256. Detalle en la sección 7.
- **Correo:** SPF, DKIM y DMARC en PASS en Gmail, en el aviso de una consulta.
- **Aviso de tarea fallida:** `avisar_fallo prueba` respondió "Aviso enviado." y el correo llegó al instante a la bandeja de entrada, sin datos sensibles.
- **Logs sin tokens e IP real en la auditoría:** el responsable decidió no probarlas a mano en la VM. Quedan cubiertas por pruebas automáticas; no verificadas a mano en staging. Los nombres de las pruebas están en la tabla de arriba. Tres se agregaron ese día, porque faltaba cubrir la URL firmada de las descargas en los logs y la IP en la auditoría con la configuración exacta del servidor.

Pendientes opcionales, sin ejecutar en staging: la subida de 24,9 MB a través del túnel y Lighthouse. Ese día no se informaron la redirección de HTTP a HTTPS, que la VM no acepta conexiones, ni una ejecución de cada temporizador en el journal: quedaron verificadas el 13-10-2026 (entrada siguiente).

**13-10-2026. Tres verificaciones que faltaban.** Informado por el responsable.

- **HTTP a HTTPS:** `curl -sI http://seba.fmartinez.xyz/` respondió 301 con `location: https://seba.fmartinez.xyz/`.
- **Sin conexiones entrantes:** `Test-NetConnection` a la IP pública de la VM, en los puertos 22 y 443, dio `TcpTestSucceeded: False`, y el ping no respondió. La IP no se escribe en el repositorio.
- **Temporizadores:** `webseba-reintentar` con 15 ejecuciones seguidas "Finished" el 12-10-2026, entre las 17:31 y las 21:01, sin fallos. Las nocturnas corrieron solas por primera vez el 13-10-2026, todas "Finished": respaldo a las 02:30:38, `purgar_papelera` a las 03:20:38 y `clearsessions` a las 03:40:33. La de auditoría es mensual: queda pendiente hasta el 01-11-2026.

Ese mismo día se agregaron `exportar_contenido` e `importar_contenido`, para llevar a producción el contenido real que el responsable cargó en el panel de staging (sección 11, DEC-200 y DEC-201). Probados en local y en la CI con la imagen de producción, por la entrada y la salida estándar; **sin ejecutar todavía en la VM**.

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
5. **Política de privacidad.** Debe informar el almacenamiento en EE. UU. y los encargados. La redacta el responsable del negocio. Hay un borrador para revisión legal, solo con marcadores, en `POLITICA_PRIVACIDAD_BORRADOR.md`.
6. **Plazos de conservación.** Solicitudes del sitio (hoy sin plazo), auditoría (24 meses), respaldos (14 días), versiones del bucket (30 días) y el plazo real de una eliminación (sección 13).
7. **Derechos de las personas y brechas.** Procedimiento para acceso, rectificación, supresión y portabilidad, y para avisar una brecha de seguridad.
8. **Relación con las empresas cliente.** Quién es responsable y quién encargado de los datos de sus trabajadores, y qué contrato lo respalda.
