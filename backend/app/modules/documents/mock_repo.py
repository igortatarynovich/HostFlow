from __future__ import annotations

import itertools
import uuid
from dataclasses import asdict
from typing import Dict, Iterable, List, Optional

from types_py import Document, OwnerRef
from validators import ValidationError


class InMemoryDocsRepo:
    """Очень простой репозиторий без внешних зависимостей."""

    def __init__(self) -> None:
        self._docs: Dict[str, Document] = {}
        self._seq = itertools.count(1)

    def _new_id(self) -> str:
        return f"doc_{next(self._seq)}_{uuid.uuid4().hex[:8]}"

    # CRUD
    def create(self, doc: Document) -> Document:
        if not doc.id:
            doc.id = self._new_id()
        if doc.id in self._docs:
            raise ValidationError("DOC-002", "Duplicate id")
        self._docs[doc.id] = doc
        return doc

    def get(self, doc_id: str) -> Optional[Document]:
        return self._docs.get(doc_id)

    def update(self, doc_id: str, **patch) -> Document:
        d = self._docs.get(doc_id)
        if not d:
            raise ValidationError("DOC-002", "Not found")
        for k, v in patch.items():
            if hasattr(d, k):
                setattr(d, k, v)
        d.version += 1
        return d

    def delete(self, doc_id: str) -> None:
        self._docs.pop(doc_id, None)

    # Queries
    def list_by_owner(self, owner: OwnerRef) -> List[Document]:
        return [
            d
            for d in self._docs.values()
            if d.owner.type == owner.type and d.owner.id == owner.id
        ]

    def list_all(self) -> List[Document]:
        return list(self._docs.values())

    # Helpers
    def to_dicts(self, docs: Iterable[Document]) -> List[dict]:
        return [asdict(d) for d in docs]
