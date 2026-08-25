"""RFC 8785 JSON Canonicalization Scheme (JCS) + SHA-256.

Forms C2: schema_hash is SHA-256 of JCS bytes of frozen field_schema.
Do not hash with json.dumps — key order must not change the digest.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

SCHEMA_HASH_ALGORITHM = "sha256"


def _utf16_units(key: str) -> tuple[int, ...]:
    encoded = key.encode("utf-16-be")
    return tuple(int.from_bytes(encoded[i : i + 2], "big") for i in range(0, len(encoded), 2))


def canonical_jcs(value: Any) -> str:
    """Return RFC 8785 JCS text (no insignificant whitespace)."""
    return _serialize(value)


def canonical_jcs_bytes(value: Any) -> bytes:
    return canonical_jcs(value).encode("utf-8")


def schema_hash_sha256(field_schema: dict[str, Any]) -> str:
    """Lowercase hex SHA-256 of canonical field_schema."""
    if not isinstance(field_schema, dict):
        raise TypeError("field_schema must be an object")
    return hashlib.sha256(canonical_jcs_bytes(field_schema)).hexdigest()


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("RFC 8785 JCS rejects NaN and Infinity")
        if value == 0.0:
            return "0" if math.copysign(1.0, value) > 0 else "-0"
        # ES6 NumberToString: integral floats as integers.
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return json.dumps(value)
    if isinstance(value, dict):
        parts: list[str] = []
        for key in sorted(value.keys(), key=lambda k: _utf16_units(str(k))):
            if not isinstance(key, str):
                raise TypeError("JCS object keys must be strings")
            parts.append(f"{json.dumps(key, ensure_ascii=False)}:{_serialize(value[key])}")
        return "{" + ",".join(parts) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    raise TypeError(f"JCS cannot serialize {type(value)!r}")
