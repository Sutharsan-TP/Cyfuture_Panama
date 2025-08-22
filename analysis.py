"""
Summarization + Risk Analysis for segmented and annotated contracts.
- Reads documents/clauses_with_entities.json
- Uses Google Gemini to generate:
  * Executive summary
  * Key terms
  * Risks with severities and clause references
  * Recommendations / open questions
- Writes JSON and Markdown reports under documents/

Requires: GOOGLE_API_KEY in .env
"""
from __future__ import annotations
import os
import json
from pathlib import Path
from typing import Any, Dict

import dotenv
import google.generativeai as genai

INPUT_PATH = Path("documents/clauses_with_entities.json")
OUT_JSON = Path("documents/summary_and_risks.json")
OUT_MD = Path("documents/summary_and_risks.md")

PROMPT_TEMPLATE = (
    "You are a contract analyst. Given the contract clauses and any extracted entities,\n"
    "produce a concise, accurate, and helpful analysis.\n\n"
    "Return strictly valid JSON matching this schema (no extra keys, no prose outside JSON):\n"
    "{\n"
    "  \"executive_summary\": [string, ...],\n"
    "  \"key_terms\": {\n"
    "    \"parties\": [string, ...],\n"
    "    \"effective_date\": string|null,\n"
    "    \"term\": string|null,\n"
    "    \"termination\": string|null,\n"
    "    \"governing_law\": string|null,\n"
    "    \"payment_terms\": string|null,\n"
    "    \"confidentiality\": string|null,\n"
    "    \"other_notable\": [string, ...]\n"
    "  },\n"
    "  \"risks\": [\n"
    "    {\n"
    "      \"title\": string,\n"
    "      \"severity\": \"low\"|\"medium\"|\"high\",\n"
    "      \"clause_title\": string|null,\n"
    "      \"rationale\": string,\n"
    "      \"snippet\": string|null\n"
    "    }\n"
    "  ],\n"
    "  \"recommendations\": [string, ...],\n"
    "  \"open_questions\": [string, ...]\n"
    "}\n\n"
    "Guidelines:\n"
    "- Be precise and factual.\n"
    "- If a key term is not found, set it to null (or empty list).\n"
    "- Map and cite risks to relevant clauses when possible.\n"
    "- Keep executive_summary to 3-6 bullet points.\n"
)


def configure_gemini() -> None:
    dotenv.load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY in environment/.env")
    genai.configure(api_key=api_key)


def load_input(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Accept both list and dict formats; normalize to dict for prompting
    if isinstance(data, list):
        return {"clauses": data}
    return data


def build_user_payload(clauses_payload: Dict[str, Any]) -> str:
    # Keep payload bounded; truncate overly long clause texts for prompt stability
    MAX_CHARS_PER_CLAUSE = 2000
    safe = []
    clauses = clauses_payload.get("clauses", clauses_payload)
    for item in clauses:
        ct = item.get("clause_text", "")
        safe.append({
            "clause_title": item.get("clause_title", ""),
            "clause_text": (ct[:MAX_CHARS_PER_CLAUSE] + ("..." if len(ct) > MAX_CHARS_PER_CLAUSE else "")),
            "entities": item.get("entities", []),
        })
    return json.dumps({"clauses": safe}, ensure_ascii=False)


def analyze(clauses_payload: Dict[str, Any]) -> Dict[str, Any]:
    configure_gemini()
    model = genai.GenerativeModel("gemini-1.5-flash")
    user_payload = build_user_payload(clauses_payload)

    prompt = PROMPT_TEMPLATE + "\nContract data (JSON):\n" + user_payload
    resp = model.generate_content(prompt)

    # Clean potential markdown fencing and parse
    raw = (resp.text or "").strip()
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except Exception as e:
        # Fallback format if JSON parsing fails
        return {
            "executive_summary": ["Model returned non-JSON output.", f"Raw: {raw[:4000]}"] ,
            "key_terms": {
                "parties": [],
                "effective_date": None,
                "term": None,
                "termination": None,
                "governing_law": None,
                "payment_terms": None,
                "confidentiality": None,
                "other_notable": [],
            },
            "risks": [],
            "recommendations": [],
            "open_questions": [],
        }


def write_outputs(result: Dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Also emit a readable Markdown summary
    lines = ["# Contract Summary & Risk Analysis", ""]
    es = result.get("executive_summary", [])
    if es:
        lines.append("## Executive Summary")
        for b in es:
            lines.append(f"- {b}")
        lines.append("")

    kt = result.get("key_terms", {})
    if kt:
        lines.append("## Key Terms")
        for k, v in kt.items():
            if isinstance(v, list):
                vv = ", ".join(v)
            else:
                vv = v if v is not None else "—"
            pretty = k.replace("_", " ").title()
            lines.append(f"- {pretty}: {vv}")
        lines.append("")

    risks = result.get("risks", [])
    if risks:
        lines.append("## Risks")
        for r in risks:
            title = r.get("title", "Risk")
            sev = r.get("severity", "")
            ct = r.get("clause_title", "")
            rat = r.get("rationale", "")
            snip = r.get("snippet", "")
            lines.append(f"- [{sev.upper()}] {title}")
            if ct:
                lines.append(f"  - Clause: {ct}")
            if rat:
                lines.append(f"  - Why: {rat}")
            if snip:
                lines.append(f"  - Snippet: {snip}")
        lines.append("")

    recs = result.get("recommendations", [])
    if recs:
        lines.append("## Recommendations")
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    qs = result.get("open_questions", [])
    if qs:
        lines.append("## Open Questions")
        for q in qs:
            lines.append(f"- {q}")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    payload = load_input(INPUT_PATH)
    result = analyze(payload)
    write_outputs(result)
    print(f"\nAnalysis written to:\n- {OUT_JSON}\n- {OUT_MD}")
