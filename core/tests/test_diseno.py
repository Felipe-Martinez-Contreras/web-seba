"""Comprobaciones de los tokens de diseño (sección 9 de la especificación)."""

import re

import pytest
from django.conf import settings

CSS = (settings.BASE_DIR / "static_src" / "css" / "app.css").read_text(encoding="utf-8")
TOKENS = dict(re.findall(r"--color-([a-z-]+):\s*(#[0-9a-fA-F]{6});", CSS))


def _luminancia(hexadecimal):
    canales = [int(hexadecimal[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lineales = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * lineales[0] + 0.7152 * lineales[1] + 0.0722 * lineales[2]


def contraste(color_a, color_b):
    """Razón de contraste de WCAG 2 entre dos colores."""
    clara, oscura = sorted((_luminancia(color_a), _luminancia(color_b)), reverse=True)
    return (clara + 0.05) / (oscura + 0.05)


def test_los_tokens_son_los_de_la_especificacion():
    esperados = {
        "primario": "#1b2d4f",
        "primario-hover": "#142340",
        "primario-suave": "#eef2f8",
        "sobre-primario-secundario": "#c7d0dd",
        "texto": "#0f172a",
        "texto-secundario": "#5b6678",
        "borde-campo": "#7b8597",
        "divisor": "#e3e8ef",
        "fondo": "#f5f7fa",
        "superficie": "#ffffff",
        "error": "#b91c1c",
        "error-suave": "#fdecec",
        "info": "#1d4ed8",
        "info-suave": "#eaf1fd",
        "exito": "#15803d",
        "exito-suave": "#e8f6ee",
        "advertencia": "#b45309",
        "neutro": "#475569",
        "neutro-suave": "#f1f5f9",
        "archivo-pdf": "#dc2626",
        "archivo-word": "#2563eb",
        "archivo-excel": "#16a34a",
        "archivo-powerpoint": "#ea580c",
        "archivo-imagen": "#7c3aed",
    }
    for nombre, valor in esperados.items():
        assert TOKENS.get(nombre) == valor, nombre


# Texto normal: WCAG 2.2 AA exige 4,5:1.
PARES_DE_TEXTO = [
    ("blanco", "primario"),
    ("blanco", "primario-hover"),
    ("sobre-primario-secundario", "primario"),
    ("sobre-primario-secundario", "primario-hover"),
    ("primario", "blanco"),
    ("primario", "primario-suave"),
    ("primario", "fondo"),
    ("texto", "superficie"),
    ("texto", "fondo"),
    ("texto-secundario", "superficie"),
    ("texto-secundario", "fondo"),
    ("texto-secundario", "primario-suave"),
    ("blanco", "error"),
    ("error", "superficie"),
    ("error", "error-suave"),
    ("info", "info-suave"),
    ("exito", "exito-suave"),
    ("advertencia", "advertencia-suave"),
    ("neutro", "neutro-suave"),
    ("texto", "error-suave"),
    ("texto", "info-suave"),
    ("texto", "exito-suave"),
    ("texto", "advertencia-suave"),
]

# Bordes de campos e íconos: 3:1.
PARES_NO_TEXTUALES = [
    ("borde-campo", "superficie"),
    ("borde-campo", "fondo"),
    ("primario", "superficie"),
    ("archivo-pdf", "superficie"),
    ("archivo-word", "superficie"),
    ("archivo-excel", "superficie"),
    ("archivo-powerpoint", "superficie"),
    ("archivo-imagen", "superficie"),
    ("error", "error-suave"),
    ("info", "info-suave"),
    ("exito", "exito-suave"),
    ("advertencia", "advertencia-suave"),
]


@pytest.mark.parametrize(("frente", "fondo"), PARES_DE_TEXTO)
def test_contraste_aa_del_texto(frente, fondo):
    razon = contraste(TOKENS[frente], TOKENS[fondo])
    assert razon >= 4.5, f"{frente} sobre {fondo}: {razon:.2f}:1"


@pytest.mark.parametrize(("frente", "fondo"), PARES_NO_TEXTUALES)
def test_contraste_de_bordes_e_iconos(frente, fondo):
    razon = contraste(TOKENS[frente], TOKENS[fondo])
    assert razon >= 3, f"{frente} sobre {fondo}: {razon:.2f}:1"


def test_la_tipografia_es_inter_autoalojada():
    assert '--font-sans: "Inter", system-ui, sans-serif;' in CSS
    assert "IBM Plex" not in CSS
    fuentes = re.findall(r'url\("\.\./fonts/([^"]+)"\)', CSS)
    assert fuentes == [f"inter-latin-{peso}-normal.woff2" for peso in (400, 500, 600, 700)]
    for archivo in fuentes:
        ruta = settings.BASE_DIR / "static" / "fonts" / archivo
        # Las fuentes woff2 empiezan con la firma "wOF2".
        assert ruta.read_bytes()[:4] == b"wOF2", archivo
    assert not list((settings.BASE_DIR / "static" / "fonts").glob("IBMPlex*"))


def test_ninguna_plantilla_carga_recursos_de_terceros():
    """HTMX, fuentes e íconos son propios: nada de CDN (sección 5)."""
    for carpeta in ("templates", "core/templates", "static_src", "static/js"):
        for ruta in (settings.BASE_DIR / carpeta).rglob("*"):
            if ruta.suffix not in {".html", ".css", ".js"}:
                continue
            contenido = ruta.read_text(encoding="utf-8")
            assert "//fonts.googleapis.com" not in contenido, ruta
            assert not re.search(r'(?:src|href)="https?://', contenido), ruta


def _mezcla(color, fondo, opacidad):
    """Color que resulta de poner `color` con esa opacidad sobre `fondo`."""
    canales = [
        round(int(color[i : i + 2], 16) * opacidad + int(fondo[i : i + 2], 16) * (1 - opacidad))
        for i in (1, 3, 5)
    ]
    return "#" + "".join(f"{canal:02x}" for canal in canales)


def test_el_velo_asegura_el_contraste_del_texto_sobre_cualquier_fotografia():
    """Sección 9: velo azul marino al 70-80 %. Se usa 80 %: el peor caso es un píxel blanco
    bajo el velo, y aun ahí el texto blanco y el secundario cumplen AA. Con 75 % el
    secundario no llegaba."""
    velo = re.search(r"\.velo \{\s*background-color: rgb\(27 45 79 / ([0-9.]+)\);", CSS)
    opacidad = float(velo.group(1))
    assert 0.7 <= opacidad <= 0.8
    assert TOKENS["primario"] == "#1b2d4f"
    for fondo_de_la_foto in ("#ffffff", "#ffff00", "#808080", "#000000"):
        fondo = _mezcla(TOKENS["primario"], fondo_de_la_foto, opacidad)
        assert contraste("#ffffff", fondo) >= 4.5, fondo_de_la_foto
        assert contraste(TOKENS["sobre-primario-secundario"], fondo) >= 4.5, fondo_de_la_foto
    peor = _mezcla(TOKENS["primario"], "#ffffff", 0.75)
    assert contraste(TOKENS["sobre-primario-secundario"], peor) < 4.5
