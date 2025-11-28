from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ocr_pipeline import OcrPipeline
from owner_summary import compute_owner_summary
from pydantic import BaseModel, Field
from rules_engine import (
    compute_candidate_checklist,
    expiring_threshold_for,
    load_ruleset,
)

# ---------- Pydantic schemas (только для мок-API) ----------


class VacancyCtx(BaseModel):
    category: Optional[str] = Field(
        default=None,
        description="driver | non_driver",
    )
    requires_driver_attestation: Optional[bool] = None
    country_of_work: Optional[str] = None


class ChecklistCtx(BaseModel):
    citizenship: Optional[str] = None
    residency_status: Optional[str] = None
    vacancy: Optional[Dict[str, Any]] = None


class ChecklistRequest(BaseModel):
    ruleset_path: str = Field(
        ...,
        description="Path to ruleset JSON (e.g. data/ruleset.v1_1.json)",
    )
    ctx: ChecklistCtx


class ExtractRequest(BaseModel):
    doc_type: str
    meta_schema_path: str = Field(
        ...,
        description="Path to meta schema JSON (e.g. meta_schemas/passport.json)",
    )
    # для мока байты не нужны; имитируем файл
    fake_bytes_len: int = Field(
        default=16,
        description="Fake file size in bytes for mock extractor",
    )


class DocInput(BaseModel):
    type: str
    status: str
    issued_at: Optional[str] = None
    expires_at: Optional[str] = None


class SummaryRequest(BaseModel):
    ruleset_path: str = Field(
        ...,
        description="Path to ruleset JSON (e.g. data/ruleset.v1_1.json)",
    )
    ctx: ChecklistCtx
    documents: List[DocInput] = Field(default_factory=list)


# ---------- App ----------

app = FastAPI(title="HostFlow Documents (Sandbox API)", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

pipe = OcrPipeline()


@app.get("/")
def index():
    return {
        "service": "HostFlow Documents — Sandbox",
        "endpoints": {
            "POST /checklist": "Генерация требуемых/опциональных типов по ruleset и контексту",
            "POST /extract": "Мок-OCR: извлечь поля по doc_type и meta_schema",
            "POST /summary": "Сводка владельца по списку документов",
        },
    }


@app.post("/checklist")
def checklist(req: ChecklistRequest):
    try:
        rs = load_ruleset(req.ruleset_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400, detail=f"Ruleset not found: {req.ruleset_path}"
        )

    ctx = {
        "citizenship": req.ctx.citizenship,
        "residency_status": req.ctx.residency_status,
        "vacancy": req.ctx.vacancy or {},
    }
    out = compute_candidate_checklist(ctx, rs)
    thresholds = {t: expiring_threshold_for(t, rs) for t in out["requiredTypes"]}
    return {"checklist": out, "expiring_thresholds": thresholds}


@app.post("/extract")
def extract(req: ExtractRequest):
    try:
        schema = pipe.load_meta_schema(req.meta_schema_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400, detail=f"Meta schema not found: {req.meta_schema_path}"
        )

    fake_bytes = b"x" * max(1, req.fake_bytes_len)
    try:
        result = pipe.run(fake_bytes, req.doc_type, schema)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"doc_type": req.doc_type, "result": result}


@app.post("/summary")
def summary(req: SummaryRequest):
    try:
        rs = load_ruleset(req.ruleset_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400, detail=f"Ruleset not found: {req.ruleset_path}"
        )

    ctx = {
        "citizenship": req.ctx.citizenship,
        "residency_status": req.ctx.residency_status,
        "vacancy": req.ctx.vacancy or {},
    }
    docs_plain = [d.dict() for d in req.documents]
    try:
        out = compute_owner_summary(ctx, rs, docs_plain)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return out


# --- DB-backed API (sandbox) ---
from docs.labs.docs_module.router import router as db_router  # noqa: E402

app.include_router(db_router)
