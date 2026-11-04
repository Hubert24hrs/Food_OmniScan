# AI Integration

## Where AI is used, and where it isn't

| Capability | Engine | AI? |
|---|---|---|
| Barcode scanning | ZXing (web), ML Kit / `mobile_scanner` (mobile), on-device | No |
| Ingredient & nutrition label OCR | Tesseract.js (web) / ML Kit Text Recognition (mobile), on-device | No |
| Ingredient parsing, matching, allergens, scoring, compatibility | Deterministic Python (`backend/app/services`) | **No** |
| Cloud label extraction (hard photos) | Gemini vision, `POST /analysis/image` (`ingredients` / `nutrition`) | Yes, quota |
| Front-of-pack product identification | Gemini vision, `task=front` | Yes, quota |
| Meal photo recognition (incl. Nigerian/African dishes) | Gemini vision, `task=meal` | Yes, quota; outputs marked *estimate* |
| Nutrition assistant | Gemini text, `POST /assistant/ask`, grounded | Yes, quota |

**The scoring engine never calls an LLM.** Scores are reproducible and auditable.

## Provider abstraction
`backend/app/services/ai/provider.py` defines `AIProvider.generate(system, messages, images, json_mode)`.
`GeminiProvider` calls `POST {GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent` with the key in the
`x-goog-api-key` header. To add another provider (e.g. Claude or Vertex), implement `AIProvider` and select it
with `AI_PROVIDER`.

Configuration: `GEMINI_API_KEY`, `GEMINI_MODEL` (default `gemini-3.5-flash-lite`), `AI_PROVIDER=gemini|none`.
Without a key, AI endpoints return `503 ai_not_configured` with a fallback hint (on-device OCR). They never
return fake output.

## Grounding (retrieval-augmented)
The assistant gets a JSON context built only from data we hold:
- product records (ingredients text, nutrition per 100 g, provenance/attribution),
- the full score breakdown (every adjustment, cap and note),
- knowledge-base entries for matched or requested ingredients (function, concern level, regulatory notes),
- the scientific sources cited by those adjustments (title, publisher, year, URL, evidence quality),
- the active profile (allergens, diets), when the user chooses one.

The system prompt (`ASSISTANT_SYSTEM` in `features.py`) requires the model to:
answer only from the context; say "I don't have that information" otherwise; cite source keys found in the
context; distinguish regulatory findings, measurements, research and estimates; repeat allergen status verbatim
and send users back to the physical label; never diagnose; and label any nutrient numbers it estimates.
Each response includes the sources list, `ai_generated: true` and a medical disclaimer.

**Vector search.** The current corpus (≈30 curated sources, ≈210 ingredients) fits in structured lookups by key, so
no embedding index is needed yet. When the research library grows, add `pgvector` with embeddings of
`scientific_sources.summary` and retrieve top-k sources per question. The context builder is the seam.

## Vision extraction rules
Prompts ask for **verbatim transcription** in JSON (`responseMimeType: application/json`, temperature 0).
Extracted text then goes through the same deterministic parser and scorer as on-device OCR. Users review and
correct it before submitting a product, and submissions still need moderator approval. AI output never writes
product data directly.

## Quotas & cost accounting
- Plan matrix (`subscription_entitlements`, admin-editable): e.g. assistant 5 / 60 / 500 / 1000 per month for
  Free / Plus / Premium / Family; vision 3 / 30 / 300 / 600.
- `require_quota` runs **before** the provider call; `record_usage` runs after. A failed call is stored with
  `status=error` and 0 credits.
- `ai_usage_records` stores tokens and an estimated cost. `GET /admin/ai-usage` aggregates by feature and status.
  The estimate uses list-price constants in `entitlements.record_usage`; update them when pricing changes.

## Privacy
Images and questions go to Google's Gemini API under Google's terms. Don't send images the user hasn't chosen to
analyse. Conversation history is kept client-side and not stored server-side.

## Background jobs
Vision calls run synchronously today (one image, a few seconds). For batch work (re-scoring after a methodology
change, recall ingestion, meal-plan generation), run a worker such as Cloud Tasks, Celery or RQ against the same
service functions; they have no web dependencies.
