"""Logs estructurados: una línea JSON por registro, a stdout (RNF-05)."""

import json
import logging
from datetime import UTC, datetime


class FormatoJson(logging.Formatter):
    def format(self, record):
        entrada = {
            "fecha": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="seconds"),
            "nivel": record.levelname,
            "origen": record.name,
            "mensaje": record.getMessage(),
        }
        codigo = getattr(record, "status_code", None)
        if codigo is not None:
            entrada["codigo"] = codigo
        if record.exc_info:
            entrada["traza"] = self.formatException(record.exc_info)
        return json.dumps(entrada, ensure_ascii=False)
