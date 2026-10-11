from django.urls import path

from solicitudes import views

app_name = "solicitudes"

urlpatterns = [
    path("contacto/", views.Contacto.as_view(), name="contacto"),
    path("cotizacion/", views.Cotizacion.as_view(), name="cotizacion"),
    path("solicitud-recibida/", views.Recibida.as_view(), name="recibida"),
]
