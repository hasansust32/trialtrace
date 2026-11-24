"""Ingestion from the public ClinicalTrials.gov API v2 (no key needed)."""
import httpx

API = "https://clinicaltrials.gov/api/v2/studies"


def fetch_studies(condition: str, n: int = 50) -> list[dict]:
    """Fetch up to n interventional studies that have a narrative description."""
    studies: list[dict] = []
    token = None
    with httpx.Client(timeout=30) as client:
        while len(studies) < n:
            params = {
                "query.cond": condition,
                "filter.advanced": "AREA[StudyType]INTERVENTIONAL",
                "pageSize": 100,
                "format": "json",
            }
            if token:
                params["pageToken"] = token
            r = client.get(API, params=params)
            r.raise_for_status()
            data = r.json()
            for s in data.get("studies", []):
                if s.get("protocolSection", {}).get("descriptionModule", {}).get("briefSummary"):
                    studies.append(s)
            token = data.get("nextPageToken")
            if not token:
                break
    return studies[:n]


def build_document(study: dict) -> tuple[str, str, str, dict]:
    """Return (nct_id, title, source_text, ground_truth).

    The source text deliberately contains ONLY narrative sections (titles,
    summary, description, outcome text). Structured fields such as status,
    sponsor and phase are held back as ground truth — so the evaluation
    measures real extraction from prose, not copying a label.
    """
    p = study["protocolSection"]
    ident = p.get("identificationModule", {})
    desc = p.get("descriptionModule", {})
    outcomes = p.get("outcomesModule", {})
    nct_id = ident["nctId"]
    title = ident.get("briefTitle", nct_id)

    parts = [f"Title: {title}"]
    if ident.get("officialTitle"):
        parts.append(f"Official title: {ident['officialTitle']}")
    parts.append(f"Summary: {desc.get('briefSummary', '')}")
    if desc.get("detailedDescription"):
        parts.append(f"Detailed description: {desc['detailedDescription']}")
    for o in outcomes.get("primaryOutcomes", []):
        line = f"Primary outcome: {o.get('measure', '')}"
        if o.get("description"):
            line += f" — {o['description']}"
        parts.append(line)
    text = "\n\n".join(parts)

    primary = outcomes.get("primaryOutcomes", [])
    ground_truth = {
        "phase": "/".join(p.get("designModule", {}).get("phases", []) or []) or None,
        "indication": p.get("conditionsModule", {}).get("conditions", []),
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "primary_endpoint": primary[0].get("measure") if primary else None,
        "status": p.get("statusModule", {}).get("overallStatus"),
    }
    return nct_id, title, text, ground_truth
