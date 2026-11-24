cd /workspaces/trialtrace && cat > README.md <<'README_END'
# TrialTrace: traceable clinical-trial extraction

TrialTrace ingests ClinicalTrials.gov records and extracts structured fields with
**Pydantic AI**. It will not report a value unless the value is tied to an exact,
verifiable span of the source text. If the text doesn't support an answer, it
says **"not found"** instead of guessing.

**Stack:** Python · FastAPI · PostgreSQL · SQLAlchemy · Pydantic AI · Next.js / React (TypeScript) · Docker · GitHub Codespaces

<!-- Add a screenshot of the UI here: docs/screenshot.png -->

## Why

Pharma portfolio strategy, competitive intelligence and BD decisions depend on
facts buried in trial registries, regulatory filings and congress readouts. In
that setting **a wrong answer is worse than a missing one**. TrialTrace makes
document traceability a hard rule enforced in code. A prompt alone isn't trusted
to deliver it.

## How it works

```
ClinicalTrials.gov API v2
        │  ingest: narrative text only (titles, summary, description, outcome text)
        ▼
PostgreSQL ── documents (text + held-out structured fields as ground truth)
        │
        ▼
Pydantic AI agent ── typed output per field: value + verbatim quote + confidence
        │
        ▼
Provenance guard (deterministic code, not the LLM)
   • quote found in source  → keep value, store span_start / span_end
   • quote NOT found        → value = "not found", flagged as blocked hallucination
        │
        ▼
PostgreSQL ── extractions ──► FastAPI ──► Next.js UI (click a value → source highlighted)
```

**Fields:** phase · indication · sponsor · primary endpoint · recruitment status

**Stored with every field:** value, document ID (NCT number), exact character
span, source quote, confidence, the model's raw answer, and the model name.

## Results

<!-- RESULTS:START -->
_Run `python -m app.evaluate` to generate results._
<!-- RESULTS:END -->

### Evaluation method

- **Ground truth without leakage:** the model only sees narrative text. The
  registry's structured fields (phase, conditions, lead sponsor, primary outcome,
  overall status) are held back and used as labels.
- **Accuracy** = correct / trials that have a ground-truth value.
  **Precision** = correct / fields the system actually answered.
  **Abstained** = share answered "not found".
- **Hallucinations blocked** = values the LLM claimed but could not ground in
  the source text. The guard discarded these before they reached the database
  as answers.

### Reading the results

- High precision on indication and primary endpoint shows the system is
  accurate when the information is in the text.
- High abstention on **sponsor** and **status** is expected, because narrative
  text rarely states them. The system abstains rather than guessing. That is
  the intended trade-off, and recall can be raised by adding structured fields
  to the input.
- The "wrong-answer rate" is an upper bound on hallucination. It includes
  answers that are grounded in the text but worded differently from the
  registry's label, for example a more specific condition name.

## Run in the browser (GitHub Codespaces)

1. **Create a codespace:** Code → Codespaces → Create codespace.
2. **Install and start the database:**
   ```bash
   bash setup.sh
   docker compose up -d db
   ```
3. **Add an API key:** edit `backend/.env` and add a key. The default is
   Gemini via Google AI Studio; OpenAI and Anthropic also work.
4. **Terminal 1 — start the API:**
   ```bash
   cd backend && source .venv/bin/activate && uvicorn app.main:app --reload
   ```
5. **Terminal 2 — ingest, extract and evaluate:**
   ```bash
   cd backend && source .venv/bin/activate
   curl -X POST "http://localhost:8000/ingest?condition=breast%20cancer&n=50"
   curl -X POST "http://localhost:8000/extract-all"
   python -m app.evaluate
   ```
6. **Terminal 3 — start the UI:**
   ```bash
   cd frontend && npm run dev
   ```
   Then open port 3000.

To compare models, change `LLM_MODEL` in `backend/.env`, restart the API, run
`curl -X POST "http://localhost:8000/extract-all?only_missing=false"`, and
evaluate again.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Status and active model |
| POST | `/ingest?condition=&n=` | Fetch trials from ClinicalTrials.gov |
| POST | `/extract/{nct_id}` | Extract one trial |
| POST | `/extract-all?only_missing=` | Extract all trials (concurrent) |
| GET | `/trials` | List trials with extracted values |
| GET | `/trials/{nct_id}` | Source text and every field with its span and confidence |

Interactive docs: `http://localhost:8000/docs`

## Project structure

```
backend/app/
  ctgov.py      ingestion from ClinicalTrials.gov API v2, document building, ground truth
  extract.py    Pydantic AI schema + agent, provenance guard (locate/verify)
  db.py         SQLAlchemy models: documents, extractions
  main.py       FastAPI endpoints
  evaluate.py   field-level metrics → EVAL.md
frontend/app/page.tsx   trial browser; click a value to highlight its source span
docker-compose.yml      PostgreSQL (+ full stack profile for deployment)
```

## Limitations and next steps

- **More document types:** PDF ingestion for FDA/EMA documents and congress
  abstracts, with page- and bounding-box-level provenance.
- **Client data isolation:** Postgres row-level security, role-based access
  control and audit logging, aligned with SOC 2.
- **Human review:** a review queue for low-confidence or blocked fields.
- **Better evaluation:** hand-labelled gold set and synonym-aware matching for
  conditions (e.g. MeSH).
- **Deployment:** AWS (ECS/RDS) deployment.

## Author

S M Mahamudul Hasan, Applied AI Engineer, London
README_END
python3 - <<'PY'
import re, pathlib
r = pathlib.Path("README.md"); e = pathlib.Path("EVAL.md")
if e.exists():
    body = e.read_text().replace("# Evaluation", "**Evaluation**", 1)
    s = r.read_text()
    s = re.sub(r"<!-- RESULTS:START -->.*<!-- RESULTS:END -->",
               lambda m: "<!-- RESULTS:START -->\n" + body + "\n<!-- RESULTS:END -->", s, flags=re.S)
    r.write_text(s); print("README updated with EVAL.md results")
else:
    print("EVAL.md not found: run python -m app.evaluate in backend first")
PY
rm -f /workspaces/trialtrace/update_readme.sh
