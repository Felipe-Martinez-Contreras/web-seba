from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("salud/", views.salud, name="salud"),
    path("favicon.ico", views.favicon, name="favicon"),
]
