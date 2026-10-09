# Decisiones

Decisiones técnicas y dependencias, con su motivo. Cada dependencia indica para qué sirve y qué alternativa se descartó (sección 1, punto 6 de `ESPECIFICACION.md`).

## Decisiones

| # | Fecha | Decisión | Motivo |
| --- | --- | --- | --- |
| DEC-01 | 09-10-2026 | Django 6.1 | Es la serie estable más reciente con soporte (sección 5) y trae CSP nativo. Aprobada por el responsable. **Pendiente: migrar a 6.2 LTS cuando se publique** |
| DEC-02 | 09-10-2026 | CSP con el soporte nativo de Django (`SECURE_CSP`), sin `django-csp` | SEG-02 pide usar el soporte nativo si existe |
| DEC-03 | 09-10-2026 | `uv` con `pyproject.toml` y `uv.lock` | Archivo de bloqueo con versiones fijadas (SEG-09); ya está instalado en el equipo |
| DEC-04 | 09-10-2026 | La aplicación, las pruebas y los comandos corren dentro de Docker | El equipo es Windows; así los comandos son iguales en desarrollo y en CI |
| DEC-05 | 09-10-2026 | El PostgreSQL de Compose no publica el puerto 5432 en el host (D3) | Lo ocupa un PostgreSQL 16 local instalado como servicio de Windows |
| DEC-06 | 09-10-2026 | Tokens de diseño definidos en CSS con `@theme` de Tailwind (D1) | Es la forma de configurar las versiones actuales del CLI; evita duplicar los tokens |
| DEC-07 | 09-10-2026 | Modelos `Usuario` y `Empresa` y utilidades de RUT en la Etapa 1 (D2) | El usuario personalizado debe existir antes de la primera migración y depende de ambos |
| DEC-08 | 09-10-2026 | Barra de progreso con `<progress>` nativo y HTMX sin estilos de indicador en línea (D4) | Cumplir la CSP sin estilos en línea |
| DEC-09 | 09-10-2026 | Apps como paquetes en la raíz del repositorio (`core/`, `cuentas/`, …) | Opción más simple; coincide con las rutas que usa la especificación |
| DEC-10 | 09-10-2026 | Las apps se crean en la etapa que las implementa | R1: nada vacío ni simulado |
| DEC-11 | 09-10-2026 | Lectura de variables de entorno con un módulo propio (`config/env.py`) | Son pocas variables; evita `django-environ` y `dj-database-url` |
| DEC-12 | 09-10-2026 | Detección del tipo real de archivo con firmas de bytes propias y `zipfile` | Solo hay 6 formatos permitidos; evita `python-magic` y la librería del sistema `libmagic` |
| DEC-13 | 09-10-2026 | Bloqueo de acceso y límites de envío implementados sobre la caché en base de datos | Lo indica la sección 5; evita `django-axes` y `django-ratelimit` |
| DEC-14 | 09-10-2026 | CI en GitHub Actions | El remoto es GitHub. Autorizada por el responsable |
| DEC-15 | 09-10-2026 | El RUT de acceso es siempre el de la persona; un RUT pertenece a una sola empresa | Definido por el responsable |
| DEC-16 | 09-10-2026 | RUT guardado normalizado: sin puntos ni guion y con K mayúscula | Una sola forma canónica para la unicidad y la búsqueda |
| DEC-17 | 09-10-2026 | Email obligatorio para administradores y opcional para clientes | AUT-07 contempla cuentas sin email; el enlace de activación se puede copiar |
| DEC-18 | 09-10-2026 | Hosting, correo y almacenamiento se deciden en la Etapa 8 | No hay nada elegido. Se evaluará la opción de una VM única (e2-micro) frente a los supuestos de la sección 0 |

## Dependencias de ejecución

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| Django 6.1 | Framework | 5.2 LTS: exigiría `django-csp` y no es la serie más reciente |
| psycopg 3 | Driver de PostgreSQL | Django no incluye driver |
| argon2-cffi | Argon2id como hasher principal (AUT-05) | PBKDF2 nativo: no cumple el requisito |
| django-otp | TOTP, códigos de recuperación y 2FA en el admin de Django (AUT-10, ADM-12) | TOTP propio: riesgo de seguridad innecesario. `django-two-factor-auth`: trae vistas, plantillas y más dependencias |
| segno | Código QR del enrolamiento TOTP, generado en el servidor como SVG | Sin QR: enrolamiento poco usable. Servicio externo de QR: expondría el secreto |
| django-storages + boto3 | Almacenamiento S3 privado y URL firmadas (desde la Etapa 4) | Backend S3 propio. Queda como alternativa si no funciona con Django 6.1 |
| WhiteNoise | Estáticos en producción | Servirlos con Django: no apto para producción |
| Gunicorn | Servidor WSGI | `runserver`: no es de producción |

## Dependencias de desarrollo y CI

| Dependencia | Para qué sirve | Alternativa descartada |
| --- | --- | --- |
| pytest, pytest-django | Pruebas (sección 12.1) | `unittest` nativo: la especificación pide `pytest-django` |
| pytest-cov | Cobertura mínima del 85 % | Ninguna nativa |
| ruff | Lint y formato (RNF-04) | Ninguna nativa |
| pip-audit | Vulnerabilidades de dependencias en CI (SEG-09) | Ninguna nativa |

## Archivos estáticos de terceros

Se sirven desde la propia aplicación, sin CDN, con versión fijada en la Etapa 1.

| Recurso | Para qué sirve |
| --- | --- |
| Tailwind CLI standalone | Compilar el CSS en el build, sin Node |
| HTMX | Interacciones parciales |
| IBM Plex Sans (woff2, pesos 400, 500 y 600) | Tipografía |
| Lucide (SVG) | Íconos |

## Dependencias descartadas

`django-environ`, `dj-database-url`, `python-magic`, `filetype`, `django-axes`, `django-ratelimit`, `django-csp`, `django-htmx`, `factory-boy`, `python-json-logger`, `mypy` y `django-debug-toolbar`: lo que aportan se resuelve con Django o con la biblioteca estándar. El servicio de errores opcional (RNF-05) se decide en la Etapa 7.
