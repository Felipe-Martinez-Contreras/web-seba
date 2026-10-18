from django.urls import path

from sitio import views

app_name = "sitio"

urlpatterns = [
    path("", views.Inicio.as_view(), name="inicio"),
    path("servicios/", views.Servicios.as_view(), name="servicios"),
    path("privacidad/", views.Privacidad.as_view(), name="privacidad"),
    path("sitemap.xml", views.sitemap, name="sitemap"),
    path("robots.txt", views.robots, name="robots"),
    path("imagenes/<str:nombre>", views.imagen, name="imagen"),
]
