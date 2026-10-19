"""Rubros desde el panel: Contenido del sitio › Rubros (PUB-09, ADM-10, DEC-208)."""

import pytest

from auditoria.models import EventoAuditoria
from conftest import entrar
from sitio.models import Rubro, VarianteImagen
from sitio.tests import imagenes_prueba as prueba

pytestmark = pytest.mark.django_db

Accion = EventoAuditoria.Accion
RUBROS = "/panel/contenido/rubros/"
NUEVO = RUBROS + "nuevo/"
ALT = "Grúa torre sobre una obra"


def _ruta(rubro, accion):
    return f"{RUBROS}{rubro.pk}/{accion}/"


def _crear(cliente_http, nombre="Construcción", contenido=None, alt=ALT):
    datos = {"nombre": nombre, "alt": alt}
    if contenido is not False:
        datos["archivo"] = prueba.subida("foto.jpg", contenido or prueba.jpg(1600, 1000))
    return cliente_http.post(NUEVO, datos)


def _eventos(accion):
    return list(EventoAuditoria.objects.filter(accion=accion))


def test_la_pestana_rubros_aparece_en_contenido_del_sitio(cliente_http_admin):
    contenido = cliente_http_admin.get("/panel/contenido/").content.decode()
    assert f'<a class="pestana" href="{RUBROS}">Rubros</a>' in contenido
    pagina = cliente_http_admin.get(RUBROS).content.decode()
    assert f'<a class="pestana" href="{RUBROS}" aria-current="page">' in pagina
    assert "Aún no hay rubros" in pagina


def test_crear_un_rubro_con_foto_la_procesa_y_registra_el_evento(cliente_http_admin, administrador):
    respuesta = _crear(cliente_http_admin)
    assert respuesta.status_code == 302 and respuesta["Location"] == RUBROS
    rubro = Rubro.objects.get()
    assert (rubro.nombre, rubro.alt, rubro.orden, rubro.activo) == ("Construcción", ALT, 1, True)
    assert set(rubro.variantes.values_list("nombre", "ancho", "alto")) == {
        ("800", 800, 600),
        ("400", 400, 300),
    }
    (evento,) = _eventos(Accion.RUBRO_CREADO)
    assert evento.actor == administrador and evento.objeto_tipo == "rubro"
    assert evento.detalle == "Construcción: con foto"
    pagina = cliente_http_admin.get(RUBROS).content.decode()
    assert "Se creó el rubro Construcción." in pagina and "Con foto" in pagina


def test_crear_un_rubro_sin_foto_no_exige_texto_alternativo(cliente_http_admin):
    respuesta = _crear(cliente_http_admin, nombre="Industria", contenido=False, alt="")
    assert respuesta.status_code == 302
    rubro = Rubro.objects.get()
    assert not rubro.variantes.exists()
    assert _eventos(Accion.RUBRO_CREADO)[0].detalle == "Industria: sin foto"


def test_con_foto_el_texto_alternativo_es_obligatorio(cliente_http_admin):
    respuesta = _crear(cliente_http_admin, alt="  ")
    assert respuesta.status_code == 200
    assert "Escriba el texto alternativo de la foto." in respuesta.content.decode()
    assert not Rubro.objects.exists() and not VarianteImagen.objects.exists()


@pytest.mark.parametrize(
    ("nombre", "mensaje"),
    [
        ("construcción", "Ya existe un rubro con ese nombre."),
        ("x" * 31, "30 caracteres"),
        ("", "Este campo es obligatorio."),
    ],
)
def test_un_nombre_repetido_largo_o_vacio_se_rechaza(cliente_http_admin, nombre, mensaje):
    Rubro.objects.create(nombre="Construcción", orden=1)
    respuesta = _crear(cliente_http_admin, nombre=nombre, contenido=False)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.content.decode()
    assert Rubro.objects.count() == 1 and not EventoAuditoria.objects.exists()


def test_un_svg_renombrado_se_rechaza_con_su_motivo_y_nada_se_guarda(cliente_http_admin):
    respuesta = _crear(cliente_http_admin, contenido=b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    assert respuesta.status_code == 200
    assert "El archivo no es una imagen JPG, PNG ni WebP." in respuesta.content.decode()
    assert not Rubro.objects.exists() and not EventoAuditoria.objects.exists()


def test_una_foto_sobre_el_limite_de_peso_se_rechaza_antes_de_abrirla(cliente_http_admin, settings):
    settings.IMAGENES_TAMANO_MAXIMO_MB = 0
    respuesta = _crear(cliente_http_admin)
    assert "La imagen pesa más de 0 MB" in respuesta.content.decode()
    assert not Rubro.objects.exists()


def test_editar_el_nombre_y_cambiar_la_foto_deja_dos_eventos_sin_el_texto_alternativo(
    cliente_http_admin,
):
    _crear(cliente_http_admin)
    rubro = Rubro.objects.get()
    anteriores = set(rubro.variantes.values_list("sha256", flat=True))
    pagina = cliente_http_admin.get(_ruta(rubro, "editar")).content.decode()
    assert "Así se ve en el sitio" in pagina and "Quitar la foto" in pagina

    respuesta = cliente_http_admin.post(
        _ruta(rubro, "editar"),
        {
            "nombre": "Construcción y obras",
            "alt": "Otra descripción",
            "archivo": prueba.subida("otra.png", prueba.png(1200, 900)),
        },
    )
    assert respuesta.status_code == 302
    rubro.refresh_from_db()
    assert rubro.nombre == "Construcción y obras" and rubro.alt == "Otra descripción"
    assert set(rubro.variantes.values_list("sha256", flat=True)).isdisjoint(anteriores)
    assert rubro.variantes.count() == 2
    (editado,) = _eventos(Accion.RUBRO_EDITADO)
    assert editado.detalle == "Construcción y obras: nombre, texto alternativo"
    (foto,) = _eventos(Accion.RUBRO_FOTO_CAMBIADA)
    assert foto.detalle == "Construcción y obras: foto nueva"
    for evento in EventoAuditoria.objects.all():
        assert "Otra descripción" not in evento.detalle and ALT not in evento.detalle


def test_editar_sin_cambios_no_deja_eventos(cliente_http_admin):
    _crear(cliente_http_admin)
    rubro = Rubro.objects.get()
    cliente_http_admin.post(_ruta(rubro, "editar"), {"nombre": rubro.nombre, "alt": ALT})
    assert not _eventos(Accion.RUBRO_EDITADO) and not _eventos(Accion.RUBRO_FOTO_CAMBIADA)


def test_un_rubro_con_foto_no_puede_quedar_sin_texto_alternativo(cliente_http_admin):
    _crear(cliente_http_admin)
    rubro = Rubro.objects.get()
    respuesta = cliente_http_admin.post(_ruta(rubro, "editar"), {"nombre": rubro.nombre, "alt": ""})
    assert "Escriba el texto alternativo de la foto." in respuesta.content.decode()
    rubro.refresh_from_db()
    assert rubro.alt == ALT


def test_quitar_la_foto_deja_el_rubro_sin_variantes(cliente_http_admin):
    _crear(cliente_http_admin)
    rubro = Rubro.objects.get()
    respuesta = cliente_http_admin.post(_ruta(rubro, "foto/quitar"))
    assert respuesta.status_code == 302 and respuesta["Location"] == _ruta(rubro, "editar")
    assert not rubro.variantes.exists() and Rubro.objects.filter(pk=rubro.pk).exists()
    assert _eventos(Accion.RUBRO_FOTO_CAMBIADA)[0].detalle == "Construcción: foto quitada"
    # Sin foto, quitarla de nuevo no deja otro evento.
    cliente_http_admin.post(_ruta(rubro, "foto/quitar"))
    assert len(_eventos(Accion.RUBRO_FOTO_CAMBIADA)) == 1


def test_ordenar_y_desactivar(cliente_http_admin):
    for nombre in ("Uno", "Dos", "Tres"):
        _crear(cliente_http_admin, nombre=nombre, contenido=False)
    tres = Rubro.objects.get(nombre="Tres")
    cliente_http_admin.post(_ruta(tres, "mover"), {"direccion": "subir"})
    assert list(Rubro.objects.values_list("nombre", flat=True)) == ["Uno", "Tres", "Dos"]
    cliente_http_admin.post(_ruta(tres, "mover"), {"direccion": "otra"})
    assert list(Rubro.objects.values_list("orden", flat=True)) == [1, 2, 3]

    cliente_http_admin.post(_ruta(tres, "estado"), {"activo": "no"})
    tres.refresh_from_db()
    assert not tres.activo
    assert _eventos(Accion.RUBRO_EDITADO)[0].detalle == "Tres: desactivado"
    pagina = cliente_http_admin.get(RUBROS).content.decode()
    assert "Tres dejó de mostrarse en el sitio." in pagina and "Inactivo" in pagina


def test_eliminar_borra_el_rubro_y_su_foto_y_lo_registra(cliente_http_admin, administrador):
    _crear(cliente_http_admin)
    _crear(cliente_http_admin, nombre="Industria", contenido=False)
    rubro = Rubro.objects.get(nombre="Construcción")
    pagina = cliente_http_admin.get(RUBROS).content.decode()
    assert f'data-abre-dialogo="eliminar-rubro-{rubro.pk}"' in pagina
    assert f'<dialog class="dialogo" id="eliminar-rubro-{rubro.pk}"' in pagina
    assert f'action="{_ruta(rubro, "eliminar")}"' in pagina

    respuesta = cliente_http_admin.post(_ruta(rubro, "eliminar"))
    assert respuesta.status_code == 302
    assert not Rubro.objects.filter(pk=rubro.pk).exists()
    assert not VarianteImagen.objects.exists()
    assert Rubro.objects.get().orden == 1
    (evento,) = _eventos(Accion.RUBRO_ELIMINADO)
    assert evento.detalle == "Construcción" and evento.actor == administrador
    assert "Se eliminó el rubro Construcción." in cliente_http_admin.get(RUBROS).content.decode()


def test_un_rubro_inexistente_responde_404(cliente_http_admin):
    assert cliente_http_admin.get(f"{RUBROS}999/editar/").status_code == 404
    assert cliente_http_admin.post(f"{RUBROS}999/eliminar/").status_code == 404


def test_las_acciones_solo_aceptan_post(cliente_http_admin):
    rubro = Rubro.objects.create(nombre="Industria", orden=1)
    for accion in ("eliminar", "estado", "mover", "foto/quitar"):
        assert cliente_http_admin.get(_ruta(rubro, accion)).status_code == 405
    assert Rubro.objects.filter(pk=rubro.pk).exists()


def test_un_cliente_no_crea_ni_elimina_rubros(client, cliente_a_activo):
    rubro = Rubro.objects.create(nombre="Industria", orden=1)
    entrar(client, cliente_a_activo.rut)
    assert client.get(RUBROS).status_code in (403, 404)
    assert _crear(client).status_code in (403, 404)
    assert client.post(_ruta(rubro, "eliminar")).status_code in (403, 404)
    assert list(Rubro.objects.values_list("nombre", flat=True)) == ["Industria"]
    assert not EventoAuditoria.objects.filter(accion__startswith="rubro_").exists()
