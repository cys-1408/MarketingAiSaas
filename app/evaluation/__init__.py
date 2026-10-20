"""Evaluation package.

Modules added per the implementation contract (documented in PLAN.md and
README.md):

* ``schemas``   — typed evaluation cases/results (versioned datasets)
* ``retrieval`` — Recall@k, Precision@k, MRR, nDCG@k, tenant-filter checks
* ``answers``   — citation correctness, numeric accuracy, abstention
* ``agents``    — tool-selection / bounds / completion checks
* ``ingestion`` — mapping, dedup, parsing success measurement
* ``runner``    — versioned execution and persistence of runs
"""
