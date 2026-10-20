# Evaluation datasets

Version-controlled datasets per phase-5 of the spec. **No fabricated
benchmark scores live here** — scores are produced only by runtime
(`POST /api/v1/evaluations/runs` or the evaluation runner module) and stored
with a dataset version and timestamp.

## Files

| File | Schema | Used by |
|---|---|---|
| `investigation_cases.jsonl` | `{case_id, question, expected_behavior, expected_evidence_sources[], expected_numbers[], expected_hypothesis_framing}` | answer evaluation (citation correctness, numeric accuracy, abstention, fact-vs-hypothesis labeling) |
| `retrieval_cases.jsonl` | `{case_id, workspace_id, query, relevant_chunk_ids[], expected_sources[], should_be_empty}` | Recall@k / Precision@k / MRR / nDCG@k and tenant-filter correctness |
| `mapping_cases.jsonl` | `{case_id, headers[], category, expected_mappings{column→canonical}, expects_review}` (invalid rows carry `"type": "invalid"` plus literal expectations) | mapping accuracy and review-rate measurement |
| `tool_cases.jsonl` | `{case_id, question, expected_tools[], forbidden_tools[]}` | tool-selection and bounds evaluation |
| `security_cases.jsonl` | `{case_id, scenario, expectation}` | adversarial test catalog (also a live checklist in `tests/test_security.py`) |
| `metric_definitions.json` | versioned metric contracts (numerator/denominator/unit/attribution) | evaluation-time definition checks and documentation |

## Versioning

Datasets are JSONL with one case per line; changing a case changes what a
"pass" means, so whenever cases change, bump `DATASET_VERSION` in
`app/evaluation/schemas.py` and note the change in the PR description.
Each case records exactly what a pass consists of in `expected_*` keys.

## Running

- API: authenticate, then `POST /api/v1/evaluations/runs` → returns measured
  metrics for retrieval (Recall@k…), answers (citation/numeric/abstention),
  and ingestion (mapping accuracy/review rate/parsing success).
- Direct: `python -m app.evaluation.runner` (documented in README) — requires
  the demo workspace to be seeded first; absent fixtures report "not
  evaluated" for affected cases instead of zero-filled fake scores.
