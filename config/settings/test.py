"""Pruebas automáticas."""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver"]

# Las pruebas no dependen del .env de quien las ejecuta.
SITIO_URL = "http://testserver"
DJANGO_ADMIN_RUTA = "admin-tecnico"
PROXY_CONFIANZA_REDES = []
MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
DEFAULT_FROM_EMAIL = "pruebas@ejemplo.test"
NOTIFICACIONES_DESTINATARIOS = ["profesional@ejemplo.test"]
NOTIFICACIONES_INTENTOS_MAXIMOS = 5
SOLICITUDES_MAXIMO_POR_HORA_IP = 5
SOLICITUDES_TIEMPO_MINIMO_SEGUNDOS = 3
SOLICITUDES_CAPTCHA = ""
DEMO_PERMITIDO = False
ERRORES_DESTINATARIOS = []
ERRORES_AVISOS_POR_HORA = 5
# El envío de correo se ejecuta en el mismo hilo, dentro de la transacción de la prueba.
TAREAS_SINCRONAS = True
# Cada prueba usa su propia carpeta temporal (conftest.py); el S3 de las pruebas es moto.
DOCUMENTOS_ALMACENAMIENTO = "local"
DOCUMENTOS_FORMATOS = ["pdf", "docx", "xlsx", "pptx", "jpg", "jpeg", "png"]
DOCUMENTOS_TAMANO_MAXIMO_MB = 25
DESCARGA_URL_SEGUNDOS = 120
PAPELERA_DIAS = 30
