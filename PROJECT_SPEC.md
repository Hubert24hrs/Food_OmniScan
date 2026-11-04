# Food omniScan — Project Specification & Roadmap

> **Know What's Inside. Understand What You Eat.**
> AI food intelligence, nutrition and ingredient scanner for Android, iOS and Web.
> **Market priority: 1) United States, 2) Europe & UK, 3) global** (incl. Africa).
> **US standards are the default**: FDA Daily Values and the FDA 5/20 rule for nutrient
> assessment, US Nutrition Facts presentation (per serving, %DV, added sugars), the US
> "Big 9" major allergens, FD&C additive names, en-US locale, USD and US customary units.
> EU/UK presentation (per 100 g, EU 14 allergens, E-numbers, traffic lights) is a
> first-class secondary mode selected by user region.

## 1. Repository audit (2026-11-04)

The GitHub repository `Hubert24hrs/Food_OmniScan` contained a single
`README.md` with only a title, so there was no existing code, schema, auth or
screens to preserve. Everything here is new. The local machine has Python 3.13,
Node 22, Flutter 3.47 and Dart 3.13, but no Docker and no PostgreSQL. Because of
that, the backend runs on **PostgreSQL in production** and on **SQLite for local
development and tests** through SQLAlchemy's portable types. Dialect-specific
features (full-text search) have SQLite fallbacks.

## 2. Product principles (non-negotiable)

1. **No fabricated data.** Product records come from Open Food Facts, USDA
   FoodData Central, verified community submissions or administrator entry.
   No product record, nutrient value, lab result or citation is invented.
2. **Explainable scoring.** Every point deducted or awarded is recorded with a
   reason and the methodology version that produced it.
3. **Honest uncertainty.** Missing data produces an `insufficient_data` state or
   a lowered confidence level. A missing measurement is never filled in.
4. **Allergen safety first.** Personal allergen warnings are computed separately
   and cannot be hidden by a good overall score. "No allergen detected" is never
   presented as "allergen-safe".
5. **Evidence tiers.** Each claim is tagged as a regulatory finding, a
   product-specific measurement, published research, an estimate or unverified.
6. **Scores are not for sale.** Sponsored and affiliate content is labelled, and
   payment never changes the scoring code path.

## 3. Phased roadmap and feature checklist

Legend: ✅ implemented and tested · 🟡 implemented, needs external credentials or
device testing · ⏳ designed in the schema/API but not built yet

### Phase 1: Foundation
- ✅ Repository audit, architecture docs, branding (logo, design tokens)
- ✅ FastAPI service with versioned API (`/api/v1`), config, CORS, security headers
- ✅ Auth provider abstraction: local email/password (bcrypt + JWT) and Firebase ID-token verification 🟡
- ✅ Role-based access control (user / contributor / moderator / admin), verified server-side
- ✅ SQLAlchemy models for all required entities, plus Alembic migrations
- ✅ Rate limiting, input validation, audit logging

### Phase 2: Scanning and the product database
- ✅ Barcode validation (EAN-13, EAN-8, UPC-A, UPC-E with check digits, UPC-E→UPC-A expansion)
- ✅ Open Food Facts adapter (v2 API, User-Agent, caching, retry, 429 handling, ODbL attribution)
- ✅ USDA FoodData Central adapter (needs an API key; `DEMO_KEY` works for low volume) 🟡
- ✅ Product lookup: local cache → OFF → "unknown product" plus a submission prompt
- ✅ Product search (local full-text plus OFF search)
- ✅ Web barcode scanner (camera, ZXing) and ingredient/nutrition label OCR (Tesseract.js, on-device)
- ✅ Server-side ingredient-text and nutrition-label-text parsers with confidence scores
- 🟡 Cloud OCR / AI front-of-pack recognition (Gemini Vision; needs `GEMINI_API_KEY`)
- ✅ Community product submission, then the moderation queue and approve/reject workflow
- ✅ Scan history with timestamps; 🟡 offline queue (mobile)

### Phase 3: Intelligence engine
- ✅ Ingredient parser (nested parentheses, percentages, E-numbers, multilingual synonyms)
- ✅ Ingredient and additive knowledge base (E-numbers, functions, categories, regulatory notes; seeded entries are marked *pending admin verification*)
- ✅ Versioned, configurable scoring engine (40/25/15/10/10) with per-deduction explanations
- ✅ NOVA from OFF, or an *estimated* NOVA from ultra-processing markers
- ✅ Detection of seed oils, sweeteners, colours, flavourings, preservatives, emulsifiers, trans fats and added sugars
- ✅ Insufficient-data state and confidence levels
- ✅ Contaminant transparency: "no product-specific lab data" state, plus lab-report and recall models
- ✅ Admin can publish a new methodology version without a rebuild; version history is kept

### Phase 4: Personalisation
- ✅ Dietary profiles and family member profiles, with profile switching
- ✅ Allergens (EU 14 + US 9), shown separately as contains / may contain / unknown
- ✅ Vegan, vegetarian, halal (ingredient screen only, never certification), gluten-free, dairy-free, lactose-free, low-FODMAP (screen), keto, low-carb, high-protein, low-sodium, low-sugar
- ✅ Custom ingredients-to-avoid lists
- ✅ Green, yellow and red verdicts that name the ingredient behind each one

### Phase 5: Alternatives and comparison
- ✅ Healthier alternatives in the same category (local DB + OFF category search), filtered by profile
- ✅ "Why it's better / where it isn't" explanations
- ✅ N-way product comparison with an objective (lowest sugar, highest protein…) and a shareable report
- ✅ Favourites, trusted/incompatible lists, reviews and ratings
- 🟡 Price comparison: schema present; no reliable pricing source is integrated yet

### Phase 6: Admin and commerce
- ✅ Admin dashboard API and web UI: submissions, products, ingredients, methodologies, recalls, lab reports, users, audit log, AI usage, analytics
- ✅ Subscription tiers (Free / Plus / Premium / Family), server-verified entitlements, AI credit quotas
- 🟡 Paystack (HMAC-SHA512 webhook verification + idempotency) and RevenueCat webhooks; need live keys

### Phase 7: AI assistant and nutrition tracking
- 🟡 Grounded nutrition assistant (structured product context only, with sources and a disclaimer); needs `GEMINI_API_KEY`
- ✅ Food diary and meal entries (manual + product-based), daily/weekly totals
- 🟡 Meal photo recognition (Gemini Vision; estimates are labelled as estimates)
- ⏳ Meal plans, recipes and grocery-list generation (schema present)

### Phase 8: Research and regional (incl. African) food intelligence — lower priority
- ✅ Scientific sources, evidence quality and lab report / recall models + admin CRUD
- ✅ Regional synonyms (e.g. groundnut, crayfish, ugu, egusi) and NAFDAC number fields
- ⏳ Official recall feed ingestion (FDA, FSA, NAFDAC)
- ⏳ Curated African packaged-food database: this has to come from real labels and community contributions, so none is seeded

### Phase 9: Discovery and expansion
- ⏳ Restaurant discovery, menu OCR, maps
- ⏳ Retailer price tracking

## 4. Acceptance criteria → evidence

| Criterion | Where verified |
|---|---|
| Register + dietary profile | `backend/tests/test_auth_profiles.py`, web E2E |
| Scan barcode → real product | `test_products.py` (mocked OFF) + `test_live_off.py` (live OFF, opt-in) |
| Ingredient label photo → extracted ingredients | web OCR → `/analysis/ingredients-text`; `test_ingredient_parser.py` |
| Transparent, reproducible score | `test_scoring.py` (determinism, deductions, versioning) |
| Allergens + warnings | `test_allergens.py` |
| Personal compatibility | `test_compatibility.py` |
| Compare + alternatives | `test_alternatives_compare.py` |
| History + favourites | `test_user_data.py` |
| Missing product submission | `test_submissions_admin.py` |
| Admin moderation | `test_submissions_admin.py` |
| Subscriptions + AI quotas | `test_billing.py` |
| Graceful failures | `test_products.py` (OFF down, invalid barcode) |

See [TESTING.md](TESTING.md) for how to run each suite.
