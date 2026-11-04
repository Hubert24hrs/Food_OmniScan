# Food omniScan

**Know what's inside. Understand what you eat.**

Food omniScan is an AI-assisted food intelligence platform for the web, Android and iOS. Scan a packaged
food's barcode (or photograph its label) to get:
- a transparent 0–100 health score where every deduction is explained;
- plain-English ingredient explanations;
- allergen and diet compatibility for every family member;
- healthier alternatives.

**US standards first** (FDA Daily Values, Nutrition Facts, the US "Big 9" allergens, FD&C names), then
Europe/UK (EU 14 allergens, E-numbers, per-100 g), then global.

| | |
|---|---|
| Backend | Python 3.13 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL (SQLite in dev) |
| Web | Next.js 16 · React 19 · Tailwind 4 · ZXing (barcodes) · Tesseract.js (on-device OCR) |
| Mobile | Flutter 3.47 · mobile_scanner · Google ML Kit text recognition · offline queue |
| Data | Open Food Facts (ODbL) · USDA FoodData Central (CC0) · curated regulatory knowledge base |
| AI | Gemini behind a provider abstraction: grounded assistant and label/meal vision (optional) |
| Payments | Stripe (web) · RevenueCat (App Store / Google Play) · Paystack (Africa) |

## Quick start
```bash
# 1) API
cd backend && py -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # set JWT_SECRET
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
# 2) Web
cd ../web && npm install && echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local && npm run dev
# 3) Mobile
cd ../mobile && flutter pub get && flutter run --dart-define=API_URL=http://10.0.2.2:8000/api/v1
```
Or run everything with PostgreSQL: `docker compose up --build`. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Documentation
[PROJECT_SPEC.md](PROJECT_SPEC.md) (roadmap and checklist) · [ARCHITECTURE.md](ARCHITECTURE.md) ·
[DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) · [API_DOCUMENTATION.md](API_DOCUMENTATION.md) ·
[SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md) · [AI_INTEGRATION.md](AI_INTEGRATION.md) ·
[SECURITY.md](SECURITY.md) · [DEPLOYMENT.md](DEPLOYMENT.md) · [TESTING.md](TESTING.md)

## Feature status
✅ built and tested · 🟡 built, needs credentials or device testing · ⏳ designed (schema/API) but not built

**Scanning & data**
- ✅ Barcode validation (EAN-13/8, UPC-A/E, GTIN-14) with GTIN-14 de-duplication
- ✅ Web camera scanning with flashlight and manual entry
- 🟡 Mobile camera scanning (code complete; needs a physical device to verify)
- ✅ Live Open Food Facts lookup and search with caching, retries and provenance
- 🟡 USDA FoodData Central gap-filling (needs a free `USDA_API_KEY`)
- ✅ Data-quality guards: truncated ingredient text, implausible "0 g added sugars"
- ✅ On-device label OCR (web: Tesseract; mobile: ML Kit) with image-quality checks and user correction
- ✅ US Nutrition Facts / EU table parsing, with %DV-based OCR error correction
- 🟡 Cloud vision extraction of labels, front-of-pack and meals (needs `GEMINI_API_KEY`; outputs labelled as estimates)
- ✅ Unknown-product submission with photo upload (EXIF stripped), moderation queue, approve/reject, contributor notifications
- ✅ Offline scan queue with idempotent sync, and offline product cache

**Intelligence**
- ✅ Ingredient parser (nesting, %, E/INS numbers, class headings, "may contain")
- ✅ 212-entry knowledge base with US label names first, E-numbers, function, concern level, regulatory notes and cited sources (seeded entries flagged *pending editorial verification*)
- ✅ Versioned, explainable score (40/25/15/10/10) built on FDA Daily Values and the 5/20 rule; beverages scored per 12 fl oz
- ✅ Insufficient-data state, confidence levels and documented caps
- ✅ NOVA (from OFF, or estimated)
- ✅ Detection of seed oils, sweeteners, colours, flavourings, preservatives, emulsifiers, trans fat and added sugars
- ✅ Contaminant transparency: product-specific lab reports and recalls only, with an explicit "no data" state
- ✅ FDA proposed front-of-package "Nutrition Info" levels

**Personalisation**
- ✅ Family profiles, profile switching, US Big 9 + EU 14 allergens with severity and trace handling
- ✅ 14 diet preferences and custom avoid lists
- ✅ Green / yellow / red verdicts that name the responsible ingredient, plus critical allergen alerts that are never hidden

**Food management**
- ✅ Alternatives (same category, filtered by profile, "better / not better" explanations)
- ✅ N-way comparison with objectives and shareable reports
- ✅ Favourites, trusted and incompatible lists, reviews, shopping lists
- ✅ Food diary with weekly summary
- ✅ Grounded AI assistant (🟡 needs `GEMINI_API_KEY`)

**Business & operations**
- ✅ Admin console: stats, failed scans, moderation, methodology publishing/activation, recalls with user notification, roles, audit log, AI usage
- ✅ Plans (Free / Plus $3.99 / Premium $7.99 / Family $11.99, annual pricing), server-side entitlements and AI quotas
- 🟡 Stripe checkout and webhooks, RevenueCat and Paystack webhooks (signature-verified and idempotent; need live keys)
- ✅ Privacy: health-data consent gate, data export, account deletion

**Not built yet**
- ⏳ Meal plans, recipes, grocery-list generation (tables exist)
- ⏳ Restaurant discovery
- ⏳ Retailer price data
- ⏳ Official recall feed ingestion
- ⏳ FCM push notifications
- ⏳ Crashlytics

## Known limitations
- **No product records are seeded.** Coverage depends on Open Food Facts, USDA and community submissions.
  The African packaged-food catalogue in particular needs real label contributions; regional ingredient
  synonyms (egusi, ogbono, iru, ugu, crayfish…) are already in the knowledge base.
- **Multilingual matching is partial.** The knowledge base is English-first. Non-English ingredient lists
  parse, but more terms go unrecognised, which lowers confidence. Allergen tags from OFF still apply.
- **Knowledge base needs editorial review.** Seeded sources and ingredient entries are marked
  `pending verification` until an editor reviews them in the admin console.
- **Score calibration.** There are no category-specific adjustments yet (e.g. cheese scores low because
  saturated fat and sodium per 100 g are high). See SCORING_METHODOLOGY.md.
- **Web session storage.** The web app keeps the session token in `localStorage`. Move to httpOnly cookies
  before launch (SECURITY.md).
- **Mobile app scope.** The Flutter app covers scanning, label OCR, results, search, diary and profiles. Family
  profile editing, data export and account deletion currently link to the web app.

## Licensing & attribution
Product data © Open Food Facts contributors, available under the Open Database License; images under
CC BY-SA. Nutrient data from USDA FoodData Central (public domain). Attribution is shown on every product.
Food omniScan provides general nutrition information and isn't medical advice.
