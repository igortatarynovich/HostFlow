from __future__ import annotations

from typing import Any, Dict


def presign_upload(document_id: str) -> Dict[str, Any]:
    """
    Мок пресайна для загрузки (S3/GCS-style POST form).
    Возвращаем обобщённый словарь, т.к. внутри есть вложенные поля.
    """
    return {
        "url": "https://mock-bucket/upload",
        "method": "POST",
        "fields": {
            "key": f"documents/{document_id}/original.bin",
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "Policy": "base64-policy",
            "X-Amz-Signature": "deadbeef",
        },
    }
