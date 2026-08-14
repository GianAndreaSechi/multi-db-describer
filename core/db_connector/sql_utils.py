from typing import Optional, Tuple


def validate_limit_offset(
    limit: Optional[int],
    offset: Optional[int],
) -> Tuple[Optional[int], Optional[int]]:
    for name, value in (("limit", limit), ("offset", offset)):
        if value is None:
            continue
        if not isinstance(value, int):
            raise ValueError(f"{name} must be an integer.")
        if value < 0:
            raise ValueError(f"{name} must be greater than or equal to 0.")
    return limit, offset


def quote_identifier(identifier: str, quote_char: str = '"') -> str:
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("SQL identifier must be a non-empty string.")
    escaped = identifier.replace(quote_char, quote_char * 2)
    return f"{quote_char}{escaped}{quote_char}"


def quote_sql_string(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("SQL string literal value must be a string.")
    return "'" + value.replace("'", "''") + "'"
