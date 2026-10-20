# Synthetic demo data

**Every record in this directory is fictional and clearly labelled.** It
exists for repeatable demonstrations, tests, and evaluation fixture runs;
none of it represents real customer results.

## Contents

| File | Purpose |
|---|---|
| `campaign_metrics.csv` | Multiple campaigns with spend/impressions/clicks/sessions/revenue and an ambiguous `conv_events` column (definition conflict: is it signups or purchases?) that triggers the mapping-review flow. |
| `customer_feedback.csv` | Fictional reviews/survey/support comments tied to products. |
| `products.json` | Fictional product facts, features, limitations, approved claims. |
| `brand_guidelines.md` | Fictional tone, terminology, prohibited claims, disclaimers, channel rules. |
| `campaigns.json` | Campaign metadata: audience, offer, message, landing page. |
| `experiment_results.csv` | Fictional control/variant observations with sample sizes and explicit metadata. |

## Demo scenario

The metrics include a campaign with strong engagement but weak
conversions, matching feedback mentioning pricing/shipping objections,
product facts, and an experiment testing clearer pricing — enabling the
"why did clicks not convert?" investigation end to end, deterministically.

## Loading

Demo data is never auto-loaded into a real workspace.  Use the API: sign
up, then `POST /api/v1/sources/uploads` with each file.  The ingestion
pipeline labels the source as synthetic-derived in `Source.category` via
the taxonomy of the uploaded content; UI screens always show
"[synthetic demo]" context for these fixtures.
