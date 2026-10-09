"""Formatos de es-CL: fechas dd-mm-aaaa, coma decimal y punto de miles."""

DATE_FORMAT = "d-m-Y"
SHORT_DATE_FORMAT = "d-m-Y"
DATETIME_FORMAT = "d-m-Y H:i"
SHORT_DATETIME_FORMAT = "d-m-Y H:i"
TIME_FORMAT = "H:i"
FIRST_DAY_OF_WEEK = 1
DATE_INPUT_FORMATS = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]
DATETIME_INPUT_FORMATS = ["%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
