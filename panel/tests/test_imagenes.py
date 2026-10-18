"""Imágenes del sitio desde el panel: Contenido del sitio › Imágenes del sitio (DEC-205)."""

import pytest

from auditoria.models import EventoAuditoria
from sitio import imagenes
from sitio.models import ImagenSitio, VarianteImagen
from sitio.procesar_imagen import ImagenRechazada
from sitio.tests import imagenes_prueba as prueba

pytestmark = pytest.mark.django_db

IMAGENES = "/panel/contenido/imagenes/"
PORTADA = IMAGENES + "portada/"
LOGO = IMAGENES + "logo-fondo-oscuro/"


def _subir_portada(cliente_http, contenido=None, alt="Grúa torre sobre una obra"):
    return cliente_http.post(
        PORTADA,
        {
            "portada-archivo": prueba.subida("foto.jpg", contenido or prueba.jpg()),
            "portada-alt": alt,
        },
    )


def test_la_pestana_muestra_las_cinco_imagenes_con_su_vista_previa(cliente_http_admin):
    contenido = cliente_http_admin.get(IMAGENES).content.decode()
    assert f'<a class="pestana" href="{IMAGENES}" aria-current="page">' in contenido
    for ranura in imagenes.Ranura:
        assert f'id="imagen-{ranura.value}"' in contenido
        assert f'action="{IMAGENES}{ranura.value}/"' in contenido
    assert contenido.count('enctype="multipart/form-data"') == 5
    assert 'src="/static/img/portada-960.webp"' in contenido
    assert 'src="/static/img/simbolo-blanco.svg"' in contenido
    assert 'accept="image/jpeg,image/png,image/webp"' in contenido
    assert 'accept="image/png"' in contenido
    # Sin nada subido no hay nada que restaurar.
    assert "data-abre-dialogo=" not in contenido
    assert "sin personas reconocibles ni logos de clientes" in contenido


def test_las_otras_pestanas_de_contenido_enlazan_a_imagenes(cliente_http_admin):
    contenido = cliente_http_admin.get("/panel/contenido/").content.decode()
    assert f'<a class="pestana" href="{IMAGENES}">Imágenes del sitio</a>' in contenido


def test_subir_una_foto_la_publica_y_registra_el_evento(cliente_http_admin, administrador):
    respuesta = _subir_portada(cliente_http_admin)
    assert respuesta.status_code == 302
    assert respuesta["Location"] == IMAGENES + "#imagen-portada"
    fila = ImagenSitio.objects.get(ranura="portada")
    assert fila.alt == "Grúa torre sobre una obra" and fila.variantes.count() == 2
    evento = EventoAuditoria.objects.get(accion=EventoAuditoria.Accion.IMAGEN_CAMBIADA)
    assert evento.actor == administrador
    pagina = cliente_http_admin.get(IMAGENES).content.decode()
    assert "Se guardó: foto de portada." in pagina
    assert "Subida el " in pagina and "Volver a la original" in pagina
    assert imagenes.cargar().foto(imagenes.Ranura.PORTADA).src_movil in pagina


def test_un_svg_renombrado_se_rechaza_con_su_motivo_y_nada_cambia(cliente_http_admin):
    respuesta = _subir_portada(
        cliente_http_admin, contenido=b'<svg xmlns="http://www.w3.org/2000/svg"/>', alt="Otra"
    )
    assert respuesta.status_code == 200
    assert "El archivo no es una imagen JPG, PNG ni WebP." in respuesta.content.decode()
    assert not ImagenSitio.objects.exists() and not EventoAuditoria.objects.exists()


def test_un_archivo_vacio_se_rechaza_y_nada_cambia(cliente_http_admin):
    respuesta = cliente_http_admin.post(
        PORTADA, {"portada-archivo": prueba.subida("vacia.jpg", b""), "portada-alt": "Otra"}
    )
    assert respuesta.status_code == 200
    assert 'aria-invalid="true"' in respuesta.content.decode()
    assert not ImagenSitio.objects.exists() and not EventoAuditoria.objects.exists()


def test_si_el_procesamiento_se_pasa_del_plazo_se_ve_un_mensaje_claro(cliente_http_admin, settings):
    settings.IMAGENES_PLAZO_SEGUNDOS = -1
    respuesta = _subir_portada(cliente_http_admin)
    assert respuesta.status_code == 200
    assert "La imagen es muy grande; súbala más pequeña." in respuesta.content.decode()
    assert not ImagenSitio.objects.exists()


def test_un_error_inesperado_de_pillow_no_da_un_error_500(cliente_http_admin, monkeypatch):
    def falla(*args, **kwargs):
        raise ImagenRechazada("La imagen es muy grande; súbala más pequeña.")

    monkeypatch.setattr(imagenes, "_procesar", falla)
    respuesta = _subir_portada(cliente_http_admin)
    assert respuesta.status_code == 200
    assert "súbala más pequeña" in respuesta.content.decode()


def test_una_foto_nueva_con_el_texto_de_la_original_se_rechaza(cliente_http_admin):
    respuesta = _subir_portada(cliente_http_admin, alt=imagenes.ORIGINALES["portada"].alt)
    assert respuesta.status_code == 200
    assert "Escriba uno que describa la foto nueva" in respuesta.content.decode()
    assert not ImagenSitio.objects.exists()


def test_la_foto_exige_texto_alternativo(cliente_http_admin):
    respuesta = _subir_portada(cliente_http_admin, alt="   ")
    assert respuesta.status_code == 200
    assert not ImagenSitio.objects.exists()


def test_subir_el_logo_genera_los_iconos(cliente_http_admin):
    respuesta = cliente_http_admin.post(
        LOGO, {"logo-fondo-oscuro-archivo": prueba.subida("logo.png", prueba.logo())}
    )
    assert respuesta.status_code == 302
    nombres = set(VarianteImagen.objects.values_list("nombre", flat=True))
    assert nombres == {"simbolo", "favicon32", "apple180", "ico"}


def test_el_logo_exige_un_archivo_png(cliente_http_admin):
    sin_archivo = cliente_http_admin.post(LOGO, {})
    assert sin_archivo.status_code == 200 and not ImagenSitio.objects.exists()
    jpg = cliente_http_admin.post(
        LOGO, {"logo-fondo-oscuro-archivo": prueba.subida("logo.png", prueba.jpg(512, 512))}
    )
    assert "El logo debe ser una imagen PNG." in jpg.content.decode()
    assert not ImagenSitio.objects.exists()


def test_volver_a_la_original_restaura_la_imagen_del_repositorio(cliente_http_admin):
    _subir_portada(cliente_http_admin)
    respuesta = cliente_http_admin.post(PORTADA + "restaurar/")
    assert respuesta.status_code == 302
    assert not ImagenSitio.objects.exists() and not VarianteImagen.objects.exists()
    assert EventoAuditoria.objects.filter(
        accion=EventoAuditoria.Accion.IMAGEN_RESTAURADA, detalle="Foto de portada"
    ).exists()
    pagina = cliente_http_admin.get(IMAGENES).content.decode()
    assert "Se volvió a la original: foto de portada." in pagina
    assert 'src="/static/img/portada-960.webp"' in pagina


def test_una_ranura_desconocida_responde_404(cliente_http_admin):
    assert cliente_http_admin.post(IMAGENES + "otra/").status_code == 404
    assert cliente_http_admin.post(IMAGENES + "otra/restaurar/").status_code == 404


def test_las_vistas_solo_admiten_post_donde_cambian_algo(cliente_http_admin):
    assert cliente_http_admin.get(PORTADA).status_code == 405
    assert cliente_http_admin.get(PORTADA + "restaurar/").status_code == 405


def test_un_cliente_no_cambia_ni_restaura_imagenes(client, cliente_a_activo, administrador):
    imagenes.cambiar(imagenes.Ranura.ACCESO, alt="Texto del administrador", actor=administrador)
    client.force_login(cliente_a_activo)
    assert client.get(IMAGENES).status_code == 404
    assert _subir_portada(client).status_code == 404
    assert client.post(IMAGENES + "acceso/restaurar/").status_code == 404
    assert list(ImagenSitio.objects.values_list("ranura", flat=True)) == ["acceso"]


def test_un_anonimo_es_enviado_al_acceso(client):
    respuesta = _subir_portada(client)
    assert respuesta.status_code == 302 and respuesta["Location"].startswith("/acceso/")
    assert not ImagenSitio.objects.exists()
