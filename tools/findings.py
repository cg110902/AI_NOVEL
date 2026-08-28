# -*- coding: utf-8 -*-
"""
Unified envelope / findings contract for quality tools' `--json` output.

The contract (see docs/tool-contracts.md §2.1) standardises every quality
command's JSON envelope as:

    {
      "schema":   "novel-studio.envelope/v1",
      "command":  "<cli command name>",
      "status":   "BLOCK" | "REVIEW" | "SUGGEST" | "PASS" | "ERROR",
      "findings": [ {id, level, message, detector, evidence?, location?, confidence?}, ... ],
      "summary":  { "total_findings", "block", "review", "suggest", "info" }
    }

Legacy severity labels are mapped to contract levels via `level()`:
    CRITICAL / FATAL / ERROR / FAIL  ->  BLOCK   (deterministic gate, blocks delivery)
    WARNING / REVIEW                 ->  REVIEW  (literary heuristic, needs LLM/human review)
    SUGGEST                          ->  SUGGEST (optimisation hint, never blocks)
    INFO                             ->  INFO    (contextual statistics)

Only BLOCK findings gate delivery; ordinary literary issues default to
REVIEW / SUGGEST / INFO and never block by themselves.
"""

from collections import Counter

ENVELOPE_SCHEMA = "novel-studio.envelope/v1"


def level(severity):
    """Map a legacy severity label (str or None) to a contract level string."""
    s = str(severity or "").upper()
    if s in {"CRITICAL", "FATAL", "ERROR", "FAIL"}:
        return "BLOCK"
    if s in {"WARNING", "REVIEW"}:
        return "REVIEW"
    if s == "SUGGEST":
        return "SUGGEST"
    if s == "INFO":
        return "INFO"
    # Missing/unknown severity must never be auto-promoted to BLOCK.
    return "REVIEW"


def finding(message, detector, level="REVIEW", id=None, evidence=None,
            location=None, confidence=None):
    """Build a single finding dict, keeping only non-empty optional fields."""
    f = {
        "id": id,
        "level": level,
        "message": message,
        "detector": detector,
    }
    if evidence:
        f["evidence"] = evidence
    if location:
        f["location"] = location
    if confidence is not None:
        f["confidence"] = confidence
    return f


def summary_of(findings):
    """Summarise a list of findings into per-level counts."""
    c = Counter((f or {}).get("level", "REVIEW") for f in findings)
    return {
        "total_findings": len(findings),
        "block": c.get("BLOCK", 0),
        "review": c.get("REVIEW", 0),
        "suggest": c.get("SUGGEST", 0),
        "info": c.get("INFO", 0),
    }


def envelope(command, status, findings, **meta):
    """Assemble the standard envelope dict."""
    env = {
        "schema": ENVELOPE_SCHEMA,
        "command": command,
        "status": status,
        "findings": findings,
        "summary": summary_of(findings),
    }
    env.update(meta)
    return env
