"use client";
import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api";

type Summary = { nct_id: string; title: string; fields: Record<string, string> };
type Field = {
  field: string; value: string; found: boolean; source_quote: string | null;
  span_start: number | null; span_end: number | null; confidence: number;
  blocked_hallucination: boolean; raw_value: string | null; document_id: string;
};
type Trial = { nct_id: string; title: string; text: string; source_url: string; extractions: Field[] };

export default function Home() {
  const [trials, setTrials] = useState<Summary[]>([]);
  const [trial, setTrial] = useState<Trial | null>(null);
  const [selected, setSelected] = useState<Field | null>(null);
  const markRef = useRef<HTMLElement>(null);

  useEffect(() => { fetch(`${API}/trials`).then(r => r.json()).then(setTrials); }, []);
  useEffect(() => { markRef.current?.scrollIntoView({ behavior: "smooth", block: "center" }); }, [selected]);

  const open = async (id: string) => {
    setSelected(null);
    setTrial(await fetch(`${API}/trials/${id}`).then(r => r.json()));
  };

  const renderSource = (t: Trial) => {
    if (!selected || selected.span_start == null || selected.span_end == null) return t.text;
    return (<>
      {t.text.slice(0, selected.span_start)}
      <mark ref={markRef}>{t.text.slice(selected.span_start, selected.span_end)}</mark>
      {t.text.slice(selected.span_end)}
    </>);
  };

  return (<>
    <header>
      <h1>TrialTrace</h1>
      <p>Clinical trial extraction where every value links to its exact source text · {trials.length} trials</p>
    </header>
    <div className="wrap">
      <div className="list">
        {trials.map(t => (
          <div key={t.nct_id} className={`item ${trial?.nct_id === t.nct_id ? "active" : ""}`} onClick={() => open(t.nct_id)}>
            <b>{t.nct_id} · {t.fields.phase ?? "not extracted"}</b>{t.title}
          </div>
        ))}
      </div>
      <div className="detail">
        {!trial ? <p>Select a trial on the left.</p> : (<>
          <div>
            <h2>{trial.title}</h2>
            <p><a href={trial.source_url} target="_blank">{trial.nct_id} on ClinicalTrials.gov ↗</a></p>
            <table>
              <thead><tr><th>Field</th><th>Value (click for source)</th><th>Conf.</th></tr></thead>
              <tbody>
                {trial.extractions.map(f => (
                  <tr key={f.field}>
                    <td>{f.field}</td>
                    <td>
                      <span className={`val ${f.found ? "" : "missing"}`} onClick={() => f.found && setSelected(f)}>{f.value}</span>
                      {f.blocked_hallucination && <span className="flag">⚠ model said “{f.raw_value}” but no supporting quote found — blocked</span>}
                    </td>
                    <td>{f.found ? f.confidence.toFixed(2) : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div>
            <h2>Source document {selected && `— highlighting “${selected.field}”`}</h2>
            <div className="source">{renderSource(trial)}</div>
          </div>
        </>)}
      </div>
    </div>
  </>);
}
