"""Traslado del contenido del sitio entre bases: exportar_contenido e importar_contenido."""

import fnmatch
import io
import json
import logging
import sys
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from conftest import datos_de_consulta
from sitio import contenido, pendientes, services
from sitio.models import DatosNegocio, Servicio
from solicitudes.models import Solicitud

pytestmark = pytest.mark.django_db

RAIZ = Path(__file__).resolve().parents[2]
EJEMPLO = Path(__file__).parent / "datos" / "contenido-ejemplo.json"
TELEFONO_DEL_EJEMPLO = "5550 0101"
CORREO_DEL_EJEMPLO = "prevencion-ficticia.example"


def _exportar(destino):
    """Ejecuta el comando y devuelve (salida estándar, resumen de la salida de errores)."""
    salida, resumen = io.StringIO(), io.StringIO()
    call_command("exportar_contenido", str(destino), stdout=salida, stderr=resumen)
    return salida.getvalue(), resumen.getvalue()


def _importar(origen):
    salida = io.StringIO()
    call_command("importar_contenido", str(origen), stdout=salida)
    return salida.getvalue()


def _vaciar():
    """Deja el contenido como en una base recién migrada."""
    Servicio.objects.all().delete()
    DatosNegocio.objects.all().delete()
    DatosNegocio.cargar()


def _estado():
    return (
        DatosNegocio.objects.values(*contenido.CAMPOS_NEGOCIO).get(),
        list(Servicio.objects.order_by("orden").values(*contenido.CAMPOS_SERVICIO, "orden")),
    )


def _ejemplo():
    return json.loads(EJEMPLO.read_text(encoding="utf-8"))


def _archivo(tmp_path, datos):
    ruta = tmp_path / "entrada.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


# --- Ida y vuelta -----------------------------------------------------------------------


def test_ida_y_vuelta_exportar_vaciar_importar_y_comparar(negocio, tmp_path):
    negocio.whatsapp = "+56 9 1111 2222"
    negocio.linkedin = "https://www.linkedin.com/company/prevencion-de-prueba"
    negocio.save()
    for orden, (nombre, activo) in enumerate(
        [
            ("Asesoría en prevención", True),
            ("Capacitación", True),
            ("Inspección de faenas", True),
            ("Señalización", True),
            ("Reglamento interno", False),
            ("Matriz de riesgos", True),
        ],
        start=1,
    ):
        Servicio.objects.create(
            nombre=nombre,
            slug=f"servicio-{orden}",
            icono="hard-hat",
            resumen=f"Resumen de {nombre}.",
            descripcion=f"Descripción de {nombre}.\r\nSegunda línea, con ñ.",
            orden=orden,
            activo=activo,
        )
    antes = _estado()
    ida, vuelta = tmp_path / "ida.json", tmp_path / "vuelta.json"

    _, resumen = _exportar(ida)
    assert "Exportado: datos del negocio y 6 servicios." in resumen
    _vaciar()
    assert _estado() != antes and Servicio.objects.count() == 0

    assert "Importado: 11 datos del negocio y 6 servicios." in _importar(ida)
    assert _estado() == antes
    _exportar(vuelta)
    assert vuelta.read_bytes() == ida.read_bytes()


def test_el_ejemplo_entra_en_una_base_nueva_y_sale_identico(tmp_path):
    texto = EJEMPLO.read_text(encoding="utf-8")
    # El ejemplo ya está en la forma exacta en que escribe el comando: la CI lo compara con cmp.
    assert contenido.serializar(json.loads(texto)) == texto

    _importar(EJEMPLO)
    datos, servicios = _estado()
    assert datos == _ejemplo()["datos_negocio"]
    assert [servicio["orden"] for servicio in servicios] == [1, 2, 3, 4, 5, 6]
    assert [servicio["activo"] for servicio in servicios] == [True] * 5 + [False]
    _exportar(tmp_path / "salida.json")
    assert (tmp_path / "salida.json").read_bytes() == EJEMPLO.read_bytes()


def test_repetir_la_importacion_no_duplica_ni_modifica():
    _importar(EJEMPLO)
    marcas = {
        **{servicio.pk: servicio.actualizado_en for servicio in Servicio.objects.all()},
        "negocio": DatosNegocio.objects.get().actualizado_en,
    }
    antes = _estado()

    assert "no se cambió nada" in _importar(EJEMPLO)
    assert _estado() == antes and Servicio.objects.count() == 6
    assert marcas == {
        **{servicio.pk: servicio.actualizado_en for servicio in Servicio.objects.all()},
        "negocio": DatosNegocio.objects.get().actualizado_en,
    }


def test_tras_importar_no_queda_contenido_pendiente_ni_marcado_como_de_prueba():
    _importar(EJEMPLO)
    assert services.contenido_pendiente() == []
    salida = io.StringIO()
    call_command("contenido_pendiente", "--estricto", stdout=salida)
    assert "No hay contenido pendiente." in salida.getvalue()


# --- Qué lleva el archivo ---------------------------------------------------------------


def test_el_archivo_solo_lleva_datos_del_negocio_y_servicios(
    negocio, servicio, cliente_a, documento_a, client, tmp_path
):
    client.post("/contacto/", datos_de_consulta())
    assert Solicitud.objects.count() == 1
    destino = tmp_path / "contenido.json"
    _exportar(destino)

    texto = destino.read_text(encoding="utf-8")
    datos = json.loads(texto)
    assert list(datos) == ["formato", "version", "datos_negocio", "servicios"]
    assert tuple(datos["datos_negocio"]) == contenido.CAMPOS_NEGOCIO
    assert [tuple(fila) for fila in datos["servicios"]] == [contenido.CAMPOS_SERVICIO]
    for ausente in (
        '"pk"',
        '"id"',
        "creado_en",
        "actualizado_en",
        '"orden"',
        "Empresa A de Prueba",
        "761111116",
        "Cliente de A",
        "111111111",
        "Administradora de Prueba",
        "admin@ejemplo.test",
        "Visitante de Prueba",
        "visitante@ejemplo.test",
        documento_a.titulo,
    ):
        assert ausente not in texto, ausente


def test_los_datos_de_cargar_demo_no_viajan(administrador, settings, tmp_path):
    settings.DEMO_PERMITIDO = True
    call_command("cargar_demo", stdout=io.StringIO())
    # Como en staging: contenido real escrito encima de los datos de demostración.
    datos = DatosNegocio.cargar()
    datos.nombre_comercial = "Prevención Real"
    datos.titular = "Titular real"
    datos.bajada = "Bajada real."
    datos.presentacion = "Presentación real."
    datos.telefono = "+56 9 2222 3333"
    datos.email_publico = "contacto@prevencion-real.cl"
    datos.ubicacion = "Talca"
    datos.save()  # El horario y la política siguen siendo los de prueba.
    renombrado = Servicio.objects.get(slug="servicio-demo-1")
    renombrado.nombre = "Asesoría en prevención"
    renombrado.resumen = "Resumen real."
    renombrado.descripcion = "Descripción real."
    renombrado.save()
    Servicio.objects.create(
        nombre="Capacitación",
        slug="capacitacion",
        resumen="Resumen real.",
        descripcion="Descripción real.",
        orden=5,
    )
    destino = tmp_path / "contenido.json"

    _, resumen = _exportar(destino)
    assert "Exportado: datos del negocio y 2 servicios." in resumen
    assert "Datos de prueba que se exportaron vacíos: horario, politica_privacidad." in resumen
    assert "Servicios de prueba omitidos: 3." in resumen
    assert "servicio-demo-1 -> asesoria-en-prevencion" in resumen
    texto = destino.read_text(encoding="utf-8")
    for marca in ("(DEMO)", "TEXTO DE PRUEBA", "ejemplo.test", "servicio-demo", "DEMO"):
        assert marca not in texto, marca
    exportado = json.loads(texto)
    assert exportado["datos_negocio"]["horario"] == ""
    assert exportado["datos_negocio"]["politica_privacidad"] == ""
    assert [fila["slug"] for fila in exportado["servicios"]] == [
        "asesoria-en-prevencion",
        "capacitacion",
    ]

    _vaciar()
    _importar(destino)
    assert list(Servicio.objects.values_list("slug", "orden")) == [
        ("asesoria-en-prevencion", 1),
        ("capacitacion", 2),
    ]
    detalles = {pendiente.nombre: pendiente.detalle for pendiente in services.contenido_pendiente()}
    assert pendientes.ES_DE_PRUEBA not in detalles.values()
    # Lo que no viajó queda pendiente como lo que es: un dato sin completar.
    assert detalles["Horario de atención"] == "Sin completar"
    assert detalles["Texto de la política"].startswith("Sin texto")


def test_un_slug_de_demostracion_no_choca_con_uno_ya_usado(tmp_path):
    Servicio.objects.create(nombre="Capacitación ", slug="capacitacion", orden=1)
    Servicio.objects.create(nombre="Capacitación", slug="servicio-demo-2", orden=2)
    exportado = contenido.exportar()
    assert [fila["slug"] for fila in exportado.datos["servicios"]] == [
        "capacitacion",
        "capacitacion-2",
    ]
    assert exportado.slugs_cambiados == [("servicio-demo-2", "capacitacion-2")]


# --- Lo inesperado se rechaza -----------------------------------------------------------


def _con(ruta, valor):
    def cambiar(datos):
        destino = datos
        for clave in ruta[:-1]:
            destino = destino[clave]
        destino[ruta[-1]] = valor

    return cambiar


def _sin(ruta):
    def cambiar(datos):
        destino = datos
        for clave in ruta[:-1]:
            destino = destino[clave]
        del destino[ruta[-1]]

    return cambiar


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [
        (_con(["usuarios"], []), "Raíz del archivo: claves inesperadas: usuarios."),
        (_sin(["servicios"]), "Raíz del archivo: faltan claves: servicios."),
        (_con(["formato"], "otro"), "formato: se esperaba web-seba/contenido."),
        (_con(["version"], 2), "version: este comando solo lee la versión 1."),
        (_con(["version"], True), "version: este comando solo lee la versión 1."),
        (_con(["datos_negocio", "id"], 1), "datos_negocio: claves inesperadas: id."),
        (_sin(["datos_negocio", "horario"]), "datos_negocio: faltan claves: horario."),
        (_con(["datos_negocio"], []), "datos_negocio: se esperaba un objeto."),
        (_con(["servicios"], {}), "servicios: se esperaba una lista."),
        (_con(["servicios", 1, "pk"], 7), "servicios, elemento 2: claves inesperadas: pk."),
        (_sin(["servicios", 2, "activo"]), "servicios, elemento 3: faltan claves: activo."),
        (_con(["datos_negocio", "telefono"], 56955500101), "datos_negocio.telefono: debe ser"),
        (_con(["servicios", 0, "activo"], "sí"), "elemento 1.activo: debe ser true o false."),
        (_con(["servicios", 0, "icono"], "bomba"), "servicios, elemento 1.icono:"),
        (_con(["servicios", 0, "nombre"], ""), "servicios, elemento 1.nombre:"),
        (_con(["servicios", 0, "slug"], "con espacios"), "servicios, elemento 1.slug:"),
        (
            _con(["servicios", 0, "slug"], "servicio-demo-1"),
            "elemento 1.slug: Es un identificador de demostración.",
        ),
        (
            _con(["servicios", 1, "slug"], "asesoria-ficticia"),
            "servicios, elemento 2.slug: está repetido.",
        ),
        (
            _con(["servicios", 1, "nombre"], "ASESORÍA FICTICIA"),
            "servicios, elemento 2.nombre: está repetido.",
        ),
        (
            _con(["servicios", 0, "nombre"], "Servicio uno (DEMO)"),
            "elemento 1.nombre: lleva una marca de datos de prueba.",
        ),
        (
            _con(["datos_negocio", "politica_privacidad"], "TEXTO DE PRUEBA\n\nPolítica"),
            "datos_negocio.politica_privacidad: lleva una marca de datos de prueba.",
        ),
        (
            _con(["datos_negocio", "instagram"], "http://instagram.com/x"),
            "datos_negocio.instagram: La dirección debe empezar con https://.",
        ),
        (_con(["datos_negocio", "email_publico"], "PRIVADO-sin-arroba"), "email_publico:"),
        (_con(["datos_negocio", "telefono"], "9" * 31), "datos_negocio.telefono:"),
    ],
)
def test_un_archivo_con_algo_inesperado_se_rechaza_sin_tocar_la_base(cambio, mensaje, tmp_path):
    datos = _ejemplo()
    cambio(datos)
    antes = _estado()
    with pytest.raises(CommandError) as error:
        _importar(_archivo(tmp_path, datos))
    texto = str(error.value)
    assert texto.startswith("No se importó nada.") and mensaje in texto
    # El error dice dónde, nunca qué: el archivo trae datos de contacto.
    for valor in (TELEFONO_DEL_EJEMPLO, CORREO_DEL_EJEMPLO, "PRIVADO", "9" * 31):
        assert valor not in texto
    assert _estado() == antes and Servicio.objects.count() == 0


def test_todos_los_errores_del_archivo_se_informan_juntos(tmp_path):
    datos = _ejemplo()
    datos["servicios"][0]["icono"] = "bomba"
    datos["servicios"][3]["slug"] = "Con Mayúsculas y espacios"
    datos["datos_negocio"]["facebook"] = "http://facebook.com/x"
    with pytest.raises(CommandError) as error:
        _importar(_archivo(tmp_path, datos))
    for donde in ("elemento 1.icono", "elemento 4.slug", "datos_negocio.facebook"):
        assert donde in str(error.value)
    assert Servicio.objects.count() == 0


def test_una_copia_de_dumpdata_se_reconoce_y_se_rechaza(negocio, servicio, tmp_path):
    copia = tmp_path / "copia.json"
    with copia.open("w", encoding="utf-8") as archivo:
        call_command("dumpdata", "sitio", stdout=archivo)
    _vaciar()
    with pytest.raises(CommandError, match="formato de dumpdata") as error:
        _importar(copia)
    assert "Vuelva a exportar con exportar_contenido" in str(error.value)
    assert Servicio.objects.count() == 0


@pytest.mark.parametrize(
    ("contenido_del_archivo", "mensaje"),
    [
        (b'{"formato": ', "El archivo no es JSON válido (línea 1"),
        (b"[1, 2]", "La raíz del archivo debe ser un objeto"),
        ('{"formato": "ñ"}'.encode("utf-16"), "El archivo no está en UTF-8."),
    ],
)
def test_un_archivo_ilegible_se_rechaza_con_un_mensaje_claro(
    contenido_del_archivo, mensaje, tmp_path
):
    ruta = tmp_path / "roto.json"
    ruta.write_bytes(contenido_del_archivo)
    with pytest.raises(CommandError) as error:
        _importar(ruta)
    assert mensaje in str(error.value)


def test_un_archivo_que_no_existe_o_un_destino_imposible_fallan_con_claridad(tmp_path):
    with pytest.raises(CommandError, match="No se pudo leer el archivo"):
        _importar(tmp_path / "no-existe.json")
    with pytest.raises(CommandError, match="No se pudo escribir el archivo"):
        _exportar(tmp_path / "no-existe" / "contenido.json")


# --- Solo sobre una base sin contenido --------------------------------------------------


def test_una_base_con_otro_contenido_no_se_pisa(tmp_path):
    _importar(EJEMPLO)
    datos = DatosNegocio.cargar()
    datos.telefono = "+56 9 7777 8888"
    datos.save()
    servicio = Servicio.objects.get(slug="capacitacion-ficticia")
    servicio.resumen = "Resumen editado en el panel."
    servicio.save()
    antes = _estado()

    with pytest.raises(CommandError) as error:
        _importar(EJEMPLO)
    texto = str(error.value)
    assert "La base ya tiene otro contenido" in texto
    assert "datos_negocio.telefono" in texto and "servicio capacitacion-ficticia" in texto
    assert "7777" not in texto and TELEFONO_DEL_EJEMPLO not in texto
    assert _estado() == antes


def test_un_servicio_que_el_archivo_no_trae_o_un_orden_distinto_impiden_importar(servicio):
    with pytest.raises(CommandError, match="Difieren: servicio servicio-de-prueba."):
        _importar(EJEMPLO)
    assert list(Servicio.objects.values_list("slug", flat=True)) == ["servicio-de-prueba"]

    servicio.delete()
    _importar(EJEMPLO)
    Servicio.objects.filter(slug="asesoria-ficticia").update(orden=9)
    with pytest.raises(CommandError, match="Difieren: servicio asesoria-ficticia."):
        _importar(EJEMPLO)


def test_una_base_a_medio_cargar_con_los_mismos_datos_se_completa():
    """Un dato ya escrito igual al del archivo no estorba: se carga lo que falta."""
    ejemplo = _ejemplo()
    datos = DatosNegocio.cargar()
    datos.nombre_comercial = ejemplo["datos_negocio"]["nombre_comercial"]
    datos.save()
    Servicio.objects.create(**ejemplo["servicios"][0], orden=1)

    assert "Importado: 10 datos del negocio y 5 servicios." in _importar(EJEMPLO)
    assert _estado()[0] == ejemplo["datos_negocio"] and Servicio.objects.count() == 6


# --- Entrada y salida estándar, y nada en los logs ---------------------------------------


def test_con_un_guion_lee_de_la_entrada_y_escribe_en_la_salida_estandar(monkeypatch):
    """Como en la VM: `dc exec -T … exportar_contenido - > archivo` y, al revés, con `<`."""
    con_bom = b"\xef\xbb\xbf" + EJEMPLO.read_bytes()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(con_bom)))
    assert "Importado: 11 datos del negocio y 6 servicios." in _importar("-")

    salida, resumen = _exportar("-")
    assert salida == EJEMPLO.read_text(encoding="utf-8")
    assert resumen == "Exportado: datos del negocio y 6 servicios.\n"


def test_ni_los_comandos_ni_sus_mensajes_dejan_datos_de_contacto_en_los_logs(caplog, tmp_path):
    with caplog.at_level(logging.DEBUG):
        salida_importar = _importar(EJEMPLO)
        salida, resumen = _exportar(tmp_path / "contenido.json")
        salida_repetida = _importar(EJEMPLO)
    for texto in (caplog.text, salida_importar, salida, resumen, salida_repetida):
        assert TELEFONO_DEL_EJEMPLO not in texto and CORREO_DEL_EJEMPLO not in texto
    assert TELEFONO_DEL_EJEMPLO in (tmp_path / "contenido.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("archivo", [".gitignore", ".dockerignore"])
def test_el_archivo_exportado_queda_fuera_del_repositorio_y_de_la_imagen(archivo):
    patrones = (RAIZ / archivo).read_text(encoding="utf-8").split()
    for nombre in ("contenido-sitio.json", "contenido-sitio-13-10-2026.json"):
        assert any(fnmatch.fnmatch(nombre, patron) for patron in patrones), nombre
    assert not any(fnmatch.fnmatch(EJEMPLO.name, patron) for patron in patrones)
