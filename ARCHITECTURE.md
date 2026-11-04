# Architecture

```
┌──────────────┐   ┌───────────────┐        ┌──────────────────────────── FastAPI (backend/) ─────────────────────────┐
│ Web (Next.js)│   │ Mobile        │ HTTPS  │ api/v1 routers ─► services ─► SQLAlchemy ─► PostgreSQL (SQLite in dev)   │
│ ZXing scan   │──►│ (Flutter)     │──────► │   auth · products · analysis · profiles · history · admin · billing     │
│ Tesseract OCR│   │ mobile_scanner│  JSON  │ services: product_service ─► providers/{openfoodfacts, usda}            │
└──────────────┘   │ ML Kit OCR    │        │           ingredient_parser · knowledge (KB) · allergens · nutrition     │
                   │ offline queue │        │           scoring/engine (versioned config) · compatibility · alternatives│
                   └───────────────┘        │           entitlements · payments/billing · ai/{provider, features}      │
                                            └─────┬──────────────────┬───────────────────┬──────────────────┬──────────┘
                                                  ▼                  ▼                   ▼                  ▼
                                        Open Food Facts API   USDA FoodData Central   Gemini API     Stripe / RevenueCat / Paystack
```

## Principles
1. **The deterministic core decides; AI only assists.** Parsing, matching, allergen detection, scoring and
   compatibility are pure Python functions with unit tests. LLMs are used only for optional vision extraction
   (always reviewed by the user) and the grounded assistant.
2. **Provider adapters.** Each data source normalises into `ProviderProduct`
   (`services/providers/base.py`). `product_service.merge_providers` fills gaps field by field and records
   provenance. Adding a source such as a retailer feed or Nutritionix means adding one adapter.
3. **Versioned configuration.** The scoring methodology is data (`scoring_methodologies.config`), validated
   and published by admins without a rebuild. Every score stores its version and an `inputs_hash`.
4. **Secrets server-side only.** Clients hold only a user session token.
5. **US-first, internationally ready.** FDA Daily Values, US Big 9 allergens, FD&C names, en-US/USD
   defaults; EU 14 allergens, E-numbers/INS numbers, per-100 g presentation and multilingual synonyms are
   built in for EU/UK and global markets.

## Request flow: barcode scan
1. Client decodes the barcode on-device (ZXing / ML Kit) → `GET /products/barcode/{code}`.
2. `barcode.parse_barcode` validates the check digit and normalises to GTIN-14 (dedupe key).
3. Cache hit (fresh for `PRODUCT_CACHE_HOURS`, or community/admin-verified) → skip providers.
4. Otherwise: Open Food Facts → (if incomplete or US) USDA FDC → merge → `upsert_product`, which stores
   barcodes, nutrition, images and parsed `product_ingredients`.
5. `analyze_product`: parse ingredients → match against the KB → detect allergens → load verified recalls
   and lab reports → `compute_score(active methodology)` → personal `evaluate()` per profile → persist
   `product_scores` and `product_warnings` (idempotent on version and hash).
6. Scan is logged to `food_scans` (including failures, for scan-quality monitoring) and `scan_history`.

**Failure handling:** an invalid barcode returns 422 `invalid_barcode`. If providers are down and data is
cached, the stale copy is served with `stale: true`. If providers are down and nothing is cached, the API
returns 503 `provider_unavailable`. If no source has the product, it returns 404 `product_not_found` and the
client offers the submission flow.

## Modules (backend/app)
| Path | Responsibility |
|---|---|
| `core/config.py` | Environment settings (pydantic-settings) |
| `core/security.py`, `core/deps.py` | bcrypt, JWT, Firebase ID token verification, server-side RBAC |
| `core/ratelimit.py` | Sliding-window limiter (swap for Redis/gateway when scaling out) |
| `models/` | 45 tables (see DATABASE_SCHEMA.md) |
| `data/` | Seed knowledge: ingredients/additives, allergens, scientific sources |
| `services/ingredient_parser.py` | Label text → tree (nesting, %, E/INS numbers, "may contain") |
| `services/knowledge.py` | Synonym index, longest-phrase matching, encyclopedia search |
| `services/allergens.py` | contains / may contain / not detected / unknown, false-friend & refined-oil handling |
| `services/nutrition.py` | FDA DVs, %DV, FOP levels, OFF nutriments, OCR label parsing |
| `services/scoring/` | Methodology config + explainable engine |
| `services/compatibility.py` | Personal verdicts and critical allergen alerts |
| `services/alternatives.py` | Category alternatives, N-way comparison, share tokens |
| `services/entitlements.py` | Plan matrix, quotas, AI credit accounting |
| `services/payments/billing.py` | Stripe / RevenueCat / Paystack verification and idempotent handling |
| `services/ai/` | Provider abstraction (Gemini), grounded prompts, vision extraction |

## Clients
- **Web** (`web/`): Next.js 16 App Router, React 19, Tailwind 4. Client components call the API. The design
  tokens in `globals.css` support light and dark mode. Offline: scan queue and product cache in
  `localStorage`.
- **Mobile** (`mobile/`): Flutter 3.47 (Android/iOS). `mobile_scanner` for barcodes, ML Kit for OCR,
  `SharedPreferences` for the offline queue and cache, `connectivity_plus` triggers sync. Subscriptions
  are planned through RevenueCat (server webhook already implemented).

## Scaling notes
- The API is stateless apart from the in-process rate limiter and KB cache, so run N replicas behind a
  load balancer with a shared limiter (Redis).
- Hot read path: `product_barcodes.gtin14` (unique index) and the cached `product_scores`. On PostgreSQL,
  add a GIN index on `to_tsvector('simple', search_text)` for large catalogues (see DEPLOYMENT.md).
- Expensive or batch work (re-scoring after a methodology change, recall ingestion) belongs in a worker
  (Cloud Tasks, Celery or RQ) calling the same service functions.
- Uploads go to the local disk volume in the MVP. Switch `services/uploads.py` to GCS or Firebase Storage
  for multi-instance deployments.
