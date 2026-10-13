"""Traslado del contenido del sitio de una base a otra (docs/DESPLIEGUE.md, sección 11).

Solo los datos del negocio y los servicios: nada de usuarios, empresas, documentos, solicitudes
ni auditoría. El archivo no lleva claves primarias ni fechas, y los datos de prueba de
`cargar_demo` no viajan. Lo usan los comandos `exportar_contenido` e `importar_contenido`.

El archivo trae datos de contacto: ningún mensaje de este módulo incluye valores, solo nombres
de campo y ubicaciones.
"""

import json
from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction

from sitio import pendientes
from sitio.forms import FormularioDatosNegocio, FormularioServicio
from sitio.models import DatosNegocio, Servicio
from sitio.services import slug_libre

FORMATO = "web-seba/contenido"
VERSION = 1
CAMPOS_NEGOCIO = tuple(FormularioDatosNegocio.Meta.fields)
TEXTOS_SERVICIO = ("nombre", "slug", "icono", "resumen", "descripcion")
CAMPOS_SERVICIO = (*TEXTOS_SERVICIO, "activo")
# Slug de los servicios de `cargar_demo`. No cambia al renombrar el servicio en el panel.
SLUG_DEMO = "servicio-demo-"


class ErrorDeContenido(Exception):
    """No se pudo importar. El mensaje nunca incluye valores del archivo."""


class ContenidoInvalido(ErrorDeContenido):
    """El archivo trae algo inesperado."""


class BaseConOtroContenido(ErrorDeContenido):
    """La base ya tiene contenido distinto del que trae el archivo."""


# --- Exportar ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Exportacion:
    datos: dict
    # Lo que no viajó o cambió, para informarlo: nombres de campo y slugs, nunca valores.
    campos_vaciados: list = field(default_factory=list)
    servicios_omitidos: int = 0
    slugs_cambiados: list = field(default_factory=list)


def _servicio_de_prueba(servicio):
    return any(
        pendientes.de_prueba(valor)
        for valor in (servicio.nombre, servicio.resumen, servicio.descripcion)
    )


def exportar():
    """El contenido de esta base, sin datos de prueba. El orden de los servicios es el de la
    lista."""
    negocio = DatosNegocio.cargar()
    vaciados = [campo for campo in CAMPOS_NEGOCIO if pendientes.de_prueba(getattr(negocio, campo))]
    datos_negocio = {
        campo: "" if campo in vaciados else getattr(negocio, campo) for campo in CAMPOS_NEGOCIO
    }

    todos = list(Servicio.objects.all())
    reales = [servicio for servicio in todos if not _servicio_de_prueba(servicio)]
    # Un servicio real creado sobre uno de demostración conserva el slug de demostración:
    # se reemplaza por uno derivado de su nombre.
    ocupados = {servicio.slug for servicio in reales if not servicio.slug.startswith(SLUG_DEMO)}
    servicios, cambiados = [], []
    for servicio in reales:
        slug = servicio.slug
        if slug.startswith(SLUG_DEMO):
            slug = slug_libre(servicio.nombre, ocupados.__contains__)
            ocupados.add(slug)
            cambiados.append((servicio.slug, slug))
        servicios.append(
            {
                "nombre": servicio.nombre,
                "slug": slug,
                "icono": servicio.icono,
                "resumen": servicio.resumen,
                "descripcion": servicio.descripcion,
                "activo": servicio.activo,
            }
        )
    return Exportacion(
        datos={
            "formato": FORMATO,
            "version": VERSION,
            "datos_negocio": datos_negocio,
            "servicios": servicios,
        },
        campos_vaciados=vaciados,
        servicios_omitidos=len(todos) - len(reales),
        slugs_cambiados=cambiados,
    )


def serializar(datos):
    """Texto del archivo. Siempre igual para el mismo contenido: dos exportaciones se pueden
    comparar byte a byte."""
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


# --- Importar ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Importacion:
    campos: int
    servicios_creados: int
    servicios_iguales: int

    @property
    def sin_cambios(self):
        return not self.campos and not self.servicios_creados


_OTRO_CONTENIDO = (
    "La base ya tiene otro contenido. importar_contenido solo carga sobre una base sin "
    "contenido, o con el mismo del archivo. Difieren: "
)


def leer(texto):
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise ContenidoInvalido(
            f"El archivo no es JSON válido (línea {error.lineno}, columna {error.colno})."
        ) from None


def _objeto(valor, claves, donde):
    """Exige un objeto con exactamente esas claves."""
    if not isinstance(valor, dict):
        raise ContenidoInvalido(f"{donde}: se esperaba un objeto.")
    sobrantes = sorted(set(valor) - set(claves))
    faltantes = [clave for clave in claves if clave not in valor]
    if sobrantes:
        raise ContenidoInvalido(f"{donde}: claves inesperadas: {', '.join(sobrantes)}.")
    if faltantes:
        raise ContenidoInvalido(f"{donde}: faltan claves: {', '.join(faltantes)}.")


def _comprobar_estructura(datos):
    if isinstance(datos, list):
        if any(isinstance(fila, dict) and "model" in fila for fila in datos):
            raise ContenidoInvalido(
                "El archivo tiene el formato de dumpdata (registros con model, pk y fields), "
                "no el de exportar_contenido. Vuelva a exportar con exportar_contenido."
            )
        raise ContenidoInvalido("La raíz del archivo debe ser un objeto, no una lista.")
    _objeto(datos, ("formato", "version", "datos_negocio", "servicios"), "Raíz del archivo")
    if datos["formato"] != FORMATO:
        raise ContenidoInvalido(f"formato: se esperaba {FORMATO}.")
    if type(datos["version"]) is not int or datos["version"] != VERSION:
        raise ContenidoInvalido(f"version: este comando solo lee la versión {VERSION}.")

    _objeto(datos["datos_negocio"], CAMPOS_NEGOCIO, "datos_negocio")
    if not isinstance(datos["servicios"], list):
        raise ContenidoInvalido("servicios: se esperaba una lista.")
    for numero, servicio in enumerate(datos["servicios"], start=1):
        _objeto(servicio, CAMPOS_SERVICIO, f"servicios, elemento {numero}")


def _errores_de_texto(valores, campos, donde):
    errores = []
    for campo in campos:
        if not isinstance(valores[campo], str):
            errores.append(f"{donde}.{campo}: debe ser un texto.")
        elif pendientes.de_prueba(valores[campo]):
            errores.append(f"{donde}.{campo}: lleva una marca de datos de prueba.")
    return errores


def _errores_de_formulario(formulario, donde):
    return [
        f"{donde}.{campo}: {' '.join(error.messages)}"
        for campo, lista in formulario.errors.as_data().items()
        for error in lista
    ]


def _validar_slug(slug):
    try:
        Servicio._meta.get_field("slug").clean(slug, None)
    except ValidationError as error:
        return " ".join(error.messages)
    return "Es un identificador de demostración." if slug.startswith(SLUG_DEMO) else ""


def importar(datos):
    """Carga el contenido en una base que no lo tiene. Repetirlo con el mismo archivo no cambia
    nada; si la base ya tiene otro contenido, se niega. O entra todo, o no entra nada."""
    _comprobar_estructura(datos)
    entrantes = datos["servicios"]
    errores = _errores_de_texto(datos["datos_negocio"], CAMPOS_NEGOCIO, "datos_negocio")
    for numero, entrante in enumerate(entrantes, start=1):
        donde = f"servicios, elemento {numero}"
        errores += _errores_de_texto(entrante, TEXTOS_SERVICIO, donde)
        if not isinstance(entrante["activo"], bool):
            errores.append(f"{donde}.activo: debe ser true o false.")
    if errores:
        raise ContenidoInvalido("\n".join(errores))

    for clave in ("slug", "nombre"):
        vistos = set()
        for numero, entrante in enumerate(entrantes, start=1):
            valor = entrante[clave].casefold()
            if valor in vistos:
                errores.append(f"servicios, elemento {numero}.{clave}: está repetido.")
            vistos.add(valor)
    if errores:
        raise ContenidoInvalido("\n".join(errores))

    with transaction.atomic():
        negocio = DatosNegocio.cargar()
        antes = {campo: getattr(negocio, campo) for campo in CAMPOS_NEGOCIO}
        existentes = {servicio.slug: servicio for servicio in Servicio.objects.all()}
        distintos = sorted(
            f"servicio {slug}"
            for slug in set(existentes) - {entrante["slug"] for entrante in entrantes}
        )
        if distintos:
            raise BaseConOtroContenido(_OTRO_CONTENIDO + ", ".join(distintos) + ".")

        formulario_negocio = FormularioDatosNegocio(datos["datos_negocio"], instance=negocio)
        errores += _errores_de_formulario(formulario_negocio, "datos_negocio")
        nuevos, iguales = [], 0
        for orden, entrante in enumerate(entrantes, start=1):
            donde = f"servicios, elemento {orden}"
            existente = existentes.get(entrante["slug"])
            actual = existente and (
                *(getattr(existente, campo) for campo in CAMPOS_SERVICIO),
                existente.orden,
            )
            formulario = FormularioServicio(entrante, instance=existente)
            errores += _errores_de_formulario(formulario, donde)
            if error_de_slug := _validar_slug(entrante["slug"]):
                errores.append(f"{donde}.slug: {error_de_slug}")
            if not formulario.is_valid():
                continue
            limpio = formulario.cleaned_data
            if existente is None:
                nuevos.append((formulario, entrante["slug"], orden, entrante["activo"]))
            elif actual == (
                limpio["nombre"],
                entrante["slug"],
                limpio["icono"],
                limpio["resumen"],
                limpio["descripcion"],
                entrante["activo"],
                orden,
            ):
                iguales += 1
            else:
                distintos.append(f"servicio {entrante['slug']}")
        if errores:
            raise ContenidoInvalido("\n".join(errores))

        limpios = formulario_negocio.cleaned_data
        distintos += [
            f"datos_negocio.{campo}"
            for campo in CAMPOS_NEGOCIO
            if antes[campo] and antes[campo] != limpios[campo]
        ]
        if distintos:
            raise BaseConOtroContenido(_OTRO_CONTENIDO + ", ".join(distintos) + ".")

        campos = [campo for campo in CAMPOS_NEGOCIO if antes[campo] != limpios[campo]]
        if campos:
            formulario_negocio.save()
        for formulario, slug, orden, activo in nuevos:
            servicio = formulario.save(commit=False)
            servicio.slug, servicio.orden, servicio.activo = slug, orden, activo
            servicio.save()
    return Importacion(campos=len(campos), servicios_creados=len(nuevos), servicios_iguales=iguales)
