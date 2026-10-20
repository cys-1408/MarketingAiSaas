"""Claim verification over model replies.

Splits structured sections into claims, verifies that observed facts resolve
to supplied evidence, checks numeric consistency, flags causal language
unsupported by experiments, and stamps support levels.  Deterministic — no
model-based judge is required for these checks.
"""

from __future__ import annotations

import re
from typing import Any

CITATION_RE = re.compile(r"\[EV-(\d+)\]")
_CAUSAL_MARKERS = ("caused", "because of", "due to", "led to", "therefore")
_STUDY_MARKERS = ("experiment", "a/b test", "controlled", "variant")


def verify_reply(
    sections: dict[str, Any],
    evidence: list[Any],  # EvidenceItem-shaped
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    max_citation = len(evidence)

    for index, fact in enumerate(sections.get("observed_facts", [])):
        citations = [int(m.group(1)) for m in CITATION_RE.finditer(str(fact))]
        unsupported = any(
            citation < 1 or citation > max_citation for citation in citations
        )
        if citations and unsupported:
            findings.append(
                {
                    "level": "unsupported",
                    "claim": str(fact),
                    "detail": f"citation [EV-{max(citations)}] does not resolve to provided evidence",
                }
            )
        elif not citations:
            findings.append(
                {
                    "level": "unverified",
                    "claim": str(fact),
                    "detail": "observed fact carries no evidence citation",
                }
            )
        else:
            findings.append(
                {
                    "level": "measured_fact",
                    "claim": str(fact),
                    "detail": "cited evidence resolves; statement traced",
                    "evidence_index": citations,
                }
            )

    for claim in sections.get("hypotheses", []) + sections.get("recommendations", []):
        lowered = str(claim).lower()
        causal = any(marker in lowered for marker in _CAUSAL_MARKERS)
        experimental = any(marker in lowered for marker in _STUDY_MARKERS)
        qualified = any(
            word in lowered for word in ("hypothesis", "might", "test", "worth testing")
        )
        if causal and not (experimental or qualified):
            findings.append(
                {
                    "level": "unsupported",
                    "claim": str(claim),
                    "detail": "causal language without experimental support",
                }
            )
        elif causal:
            findings.append(
                {
                    "level": "hypothesis",
                    "claim": str(claim),
                    "detail": "causal phrasing present but qualified/tested framing detected",
                }
            )

    # Numbers in observed facts must appear in the evidence statement.
    for fact in sections.get("observed_facts", []):
        for number in re.findall(r"\d+(?:\.\d+)?", str(fact)):
            if not any(number in item.statement for item in evidence):
                findings.append(
                    {
                        "level": "unsupported",
                        "claim": str(fact),
                        "detail": f"number {number} does not appear in retrieved evidence",
                    }
                )
                break
    return findings
