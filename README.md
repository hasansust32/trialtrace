# TrialTrace — traceable clinical-trial extraction

A small pipeline that ingests ClinicalTrials.gov records, extracts structured
fields with **Pydantic AI**, and refuses to report any value it cannot tie to an
exact span of source text.

**Stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · Pydantic AI · Next.js/React (TypeScript) · Docker · AWS EC2

## Why it exists
Commercial pharma decisions (portfolio, competitive intelligence, BD) depend on
facts buried in registries, filings and congress abstracts. A wrong value is
worse than a missing one. TrialTrace treats provenance as a hard requirement.

## How it works
```
ClinicalTrials.gov API v2 ─► ingest (narrative text only) ─► PostgreSQL: documents
                                                                   │
                     Pydantic AI agent (typed output: value + verbatim quote + confidence)
                                                                   │
                     Provenance guard: quote must exist in source ─► span_start / span_end
                     quote not found ─► value = "not found", flagged as blocked hallucination
                                                                   │
                                     PostgreSQL: extractions ─► FastAPI ─► Next.js UI
```
- **Fields:** phase, indication, sponsor, primary endpoint, recruitment status
- **Each field stores:** value, document ID, exact character span, source quote, confidence, model
- **Fair evaluation:** the model only sees narrative text. The registry's
  structured fields are held back and used as ground truth.

## Results
See [EVAL.md](EVAL.md) — <!-- paste the summary table here after running the eval -->

## Run in the browser (GitHub Codespaces)
Code → Codespaces → Create codespace. Dependencies install automatically; then follow the steps below from `docker compose up -d db`.

## Run locally
```bash
docker compose up -d db
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && cp .env.example .env   # add your API key
uvicorn app.main:app --reload                              # http://localhost:8000/docs
curl -X POST "localhost:8000/ingest?condition=breast%20cancer&n=50"
curl -X POST "localhost:8000/extract-all"
python -m app.evaluate
cd ../frontend && npm install && npm run dev              # http://localhost:3000
```

## Limitations / next steps
- Status and sponsor are often absent from narrative text, so the system
  abstains by design. That is correct behaviour, but it lowers recall.
- Next: PDF ingestion (FDA/EMA documents, congress abstracts), per-client data
  isolation (Postgres row-level security), auth/RBAC, and a human-review queue
  for low-confidence fields.
