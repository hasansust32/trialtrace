"""FastAPI service: ingest -> extract -> browse with provenance."""
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, select

from . import ctgov
from .db import Document, Extraction, SessionLocal, init_db
from .extract import MODEL, extract

app = FastAPI(title="TrialTrace", description="Traceable clinical-trial extraction")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"ok": True, "model": MODEL}


@app.post("/ingest")
def ingest(condition: str = "breast cancer", n: int = 50):
    studies = ctgov.fetch_studies(condition, n)
    with SessionLocal() as s:
        for st in studies:
            nct_id, title, text, gt = ctgov.build_document(st)
            s.merge(Document(nct_id=nct_id, title=title, text=text, ground_truth=gt, raw=st))
        s.commit()
    return {"ingested": len(studies), "condition": condition}


def _extract_one(nct_id: str) -> int:
    with SessionLocal() as s:
        doc = s.get(Document, nct_id)
        if not doc:
            raise HTTPException(404, "unknown trial")
        rows = extract(doc.text)
        s.execute(delete(Extraction).where(Extraction.nct_id == nct_id))
        for r in rows:
            s.add(Extraction(nct_id=nct_id, model=MODEL, **r))
        s.commit()
        return len(rows)


@app.post("/extract/{nct_id}")
def extract_one(nct_id: str):
    return {"nct_id": nct_id, "fields": _extract_one(nct_id)}


@app.post("/extract-all")
def extract_all(only_missing: bool = True, workers: int = 2):
    with SessionLocal() as s:
        ids = s.scalars(select(Document.nct_id)).all()
        if only_missing:
            done = set(s.scalars(select(Extraction.nct_id).distinct()).all())
            ids = [i for i in ids if i not in done]
    errors = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {i: pool.submit(_extract_one, i) for i in ids}
        for i, f in futures.items():
            try:
                f.result()
            except Exception as e:  # keep going; report failures
                errors[i] = str(e)[:200]
    return {"processed": len(ids) - len(errors), "errors": errors}


def _serialize(e: Extraction) -> dict:
    return {
        "field": e.field, "value": e.value or "not found", "found": e.value is not None,
        "source_quote": e.source_quote, "span_start": e.span_start, "span_end": e.span_end,
        "confidence": e.confidence, "blocked_hallucination": e.blocked_hallucination,
        "raw_value": e.raw_value, "document_id": e.nct_id, "model": e.model,
    }


@app.get("/trials")
def list_trials():
    with SessionLocal() as s:
        docs = s.scalars(select(Document).order_by(Document.nct_id)).all()
        return [
            {"nct_id": d.nct_id, "title": d.title,
             "fields": {e.field: e.value or "not found" for e in d.extractions}}
            for d in docs
        ]


@app.get("/trials/{nct_id}")
def get_trial(nct_id: str):
    with SessionLocal() as s:
        d = s.get(Document, nct_id)
        if not d:
            raise HTTPException(404, "unknown trial")
        return {
            "nct_id": d.nct_id, "title": d.title, "text": d.text,
            "source_url": f"https://clinicaltrials.gov/study/{d.nct_id}",
            "extractions": [_serialize(e) for e in d.extractions],
        }
