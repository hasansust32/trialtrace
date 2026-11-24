"""Evaluate extractions against ClinicalTrials.gov structured fields.

Run: python -m app.evaluate   (writes EVAL.md at repo root)

Metrics per field
- accuracy:   correct / trials where ground truth exists
- precision:  correct / fields the system answered (not "not found")
- abstain:    share answered "not found"
- blocked:    LLM claimed a value whose quote was NOT in the source (caught by guard)
- hallucination rate (overall): answered values that are wrong, out of all answered
"""
import re
from pathlib import Path

from sqlalchemy import select

from .db import Document, SessionLocal
from .extract import FIELDS


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", s.lower()) if len(t) > 2}


def _phase(s: str) -> str:
    s = s.upper().replace(" ", "").replace("PHASEI", "PHASE1")
    return re.sub(r"[^A-Z0-9/]", "", s)


def is_correct(field: str, pred: str, gt) -> bool:
    if field == "phase":
        return _phase(pred) == _phase(gt)
    if field == "status":
        return pred.strip().upper().replace(" ", "_") == gt
    if field == "indication":  # gt is a list of conditions
        p = _tokens(pred)
        return any(p & _tokens(c) for c in gt)
    a, b = _tokens(pred), _tokens(gt)  # sponsor, primary_endpoint: token overlap
    return bool(a and b) and len(a & b) / min(len(a), len(b)) >= 0.5


def main() -> None:
    stats = {f: dict(gt=0, answered=0, correct=0, abstain=0, blocked=0) for f in FIELDS}
    with SessionLocal() as s:
        docs = [d for d in s.scalars(select(Document)).all() if d.extractions]
        for d in docs:
            ex = {e.field: e for e in d.extractions}
            for f in FIELDS:
                e, gt = ex.get(f), d.ground_truth.get(f)
                st = stats[f]
                has_gt = bool(gt) and gt != "NA"
                st["gt"] += has_gt
                if e is None or e.value is None:
                    st["abstain"] += 1
                    st["blocked"] += bool(e and e.blocked_hallucination)
                    continue
                st["answered"] += 1
                st["correct"] += has_gt and is_correct(f, e.value, gt)

    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "–"
    n = len(docs)
    lines = [
        f"# Evaluation ({n} trials)\n",
        "Ground truth = ClinicalTrials.gov structured fields, hidden from the model.\n",
        "| Field | Accuracy | Precision (when answered) | Abstained | Hallucinations blocked |",
        "|---|---|---|---|---|",
    ]
    tot_ans = tot_cor = tot_blk = 0
    for f, st in stats.items():
        tot_ans += st["answered"]; tot_cor += st["correct"]; tot_blk += st["blocked"]
        lines.append(
            f"| {f} | {pct(st['correct'], st['gt'])} | {pct(st['correct'], st['answered'])} "
            f"| {pct(st['abstain'], n)} | {st['blocked']} |"
        )
    lines += [
        "",
        f"**Overall precision:** {pct(tot_cor, tot_ans)} · "
        f"**Residual wrong-answer rate:** {pct(tot_ans - tot_cor, tot_ans)} · "
        f"**Ungrounded claims blocked by provenance guard:** {tot_blk}",
        "",
        "Note: the residual rate includes answers that are grounded in the text but "
        "disagree with the registry's structured field (e.g. synonym conditions), so "
        "it is an upper bound on true hallucination. Spot-check these by hand.",
    ]
    out = "\n".join(lines)
    print(out)
    Path(__file__).resolve().parents[2].joinpath("EVAL.md").write_text(out + "\n")


if __name__ == "__main__":
    main()
