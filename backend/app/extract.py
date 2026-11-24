"""Structured LLM extraction with Pydantic AI + a deterministic provenance guard.

The LLM must return, for each field, a value AND a verbatim quote from the
source. We then check the quote really exists in the document. If it does not,
the value is discarded and reported as "not found" — the model is never
trusted on its own word. That is the zero-hallucination contract.
"""
import os
import re

from pydantic import BaseModel, Field
from pydantic_ai import Agent

FIELDS = ["phase", "indication", "sponsor", "primary_endpoint", "status"]
MODEL = os.getenv("LLM_MODEL", "google:gemini-3.5-flash-lite")


class ExtractedField(BaseModel):
    value: str | None = Field(
        description="Normalised value, or null if the text does not state it explicitly."
    )
    source_quote: str | None = Field(
        description="Exact, verbatim, contiguous substring of the source text that supports "
        "the value (copy-paste, max ~200 chars). Null if value is null."
    )
    confidence: float = Field(ge=0, le=1, description="0-1 confidence the value is correct.")


class TrialExtraction(BaseModel):
    phase: ExtractedField = Field(
        description="Trial phase as one of: EARLY_PHASE1, PHASE1, PHASE2, PHASE3, PHASE4, "
        "PHASE1/PHASE2, PHASE2/PHASE3, NA."
    )
    indication: ExtractedField = Field(description="Disease or condition being studied.")
    sponsor: ExtractedField = Field(description="Organisation sponsoring/running the trial.")
    primary_endpoint: ExtractedField = Field(description="The main primary outcome measure.")
    status: ExtractedField = Field(
        description="Recruitment status as one of: NOT_YET_RECRUITING, RECRUITING, "
        "ACTIVE_NOT_RECRUITING, COMPLETED, TERMINATED, WITHDRAWN, SUSPENDED."
    )


INSTRUCTIONS = """You extract facts from clinical trial registry text for a pharma
intelligence product where a wrong answer is worse than no answer.
Rules:
- Use ONLY the provided text. Never use outside knowledge about the trial or drug.
- If the text does not explicitly state a field, return value=null, source_quote=null.
- source_quote must be copied character-for-character from the text.
- Be conservative with confidence."""


def make_agent(model=None) -> Agent:
    return Agent(model or MODEL, output_type=TrialExtraction, instructions=INSTRUCTIONS)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def locate(quote: str, text: str) -> tuple[int, int] | None:
    """Find quote in text: exact match first, then whitespace/case-insensitive."""
    if not quote:
        return None
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    # Tolerant search: build a regex that allows any whitespace between words.
    words = [re.escape(w) for w in quote.split()]
    if not words:
        return None
    m = re.search(r"\s+".join(words), text, flags=re.IGNORECASE)
    return (m.start(), m.end()) if m else None


def verify(result: TrialExtraction, text: str) -> list[dict]:
    """Apply the provenance guard. Returns one row per field."""
    rows = []
    for name in FIELDS:
        f: ExtractedField = getattr(result, name)
        span = locate(f.source_quote or "", text) if f.value else None
        verified = span is not None
        rows.append(
            {
                "field": name,
                "raw_value": f.value,
                "value": f.value if verified else None,
                "source_quote": text[span[0]:span[1]] if span else None,
                "span_start": span[0] if span else None,
                "span_end": span[1] if span else None,
                "confidence": f.confidence if verified else 0.0,
                "verified": verified,
                # model claimed a value but could not ground it in the text
                "blocked_hallucination": bool(f.value) and not verified,
            }
        )
    return rows


def extract(text: str, agent: Agent | None = None) -> list[dict]:
    agent = agent or make_agent()
    result = agent.run_sync(f"SOURCE TEXT:\n<<<\n{text}\n>>>")
    return verify(result.output, text)
