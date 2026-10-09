"""Logs estructurados: una línea JSON por registro, a stdout (RNF-05)."""

import json
import logging
import re
from datetime import UTC, datetime

# Los enlaces de activación y de restablecimiento llevan su token en la ruta. El servidor
# registra la ruta de cada petición: aquí se oculta el token antes de escribirla (SEG-10).
_TOKEN_EN_RUTA = re.compile(r"/(activar|restablecer)/[^/\s\"'?]+")


def ocultar_tokens(texto):
    return _TOKEN_EN_RUTA.sub(r"/\1/[oculto]", texto)


class FormatoJson(logging.Formatter):
    def format(self, record):
        entrada = {
            "fecha": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="seconds"),
            "nivel": record.levelname,
            "origen": record.name,
            "mensaje": ocultar_tokens(record.getMessage()),
        }
        codigo = getattr(record, "status_code", None)
        if codigo is not None:
            entrada["codigo"] = codigo
        if record.exc_info:
            entrada["traza"] = ocultar_tokens(self.formatException(record.exc_info))
        return json.dumps(entrada, ensure_ascii=False)
