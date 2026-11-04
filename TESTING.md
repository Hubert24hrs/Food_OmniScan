# Testing

All suites below except the live-provider tests run on every pull request and on pushes to `main` via GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): backend lint, format, tests, migration check and `pip-audit`; web types, lint, build and `npm audit`; Playwright E2E against a freshly started stack; `flutter analyze` and `flutter test`.

| Suite | Command | What it covers | Status (2026-11-04) |
|---|---|---|---|
| Backend unit + integration | `cd backend && .venv/Scripts/python -m pytest` | Barcode validation, parser, KB matching, allergens (false friends, refined oils, PAL), nutrition label OCR (US + EU, OCR digit correction), scoring (determinism, caps, insufficient data, conflicting OFF data), compatibility, every API router against SQLite with mocked providers (respx), auth/RBAC, consent, export/delete, offline sync idempotency, submissions & moderation, methodology versioning, recalls, entitlements/quotas, Stripe/RevenueCat/Paystack signatures + idempotency, AI grounding & credit accounting, AI label photos keep allergen statements, plan gating and upgrade prompts, diary targets/water/weight/micros/reports/insights, recipes (compatibility, substitutions, shopping list), AI recipes and meal plans, pantry and expiry reminders, households, budget, rankings, shared reports, prices, scan alerts, local foods, safety topics, admin content and jobs, assistant languages, translated labels, Gemini retry | **91 passed** |
| Live provider tests | `pytest -m live -o addopts=""` | Real Open Food Facts barcode lookup + parse rate; unknown barcode | **2 passed** |
| Backend lint | `.venv/Scripts/ruff check app` | ruff (pyflakes, bugbear, bandit-security subset, isort, pyupgrade) | clean |
| Migration check | `alembic upgrade head && alembic check` | Migration matches models | clean |
| Web types + lint | `cd web && npx tsc --noEmit && npx eslint src` | TypeScript strict, React 19 hooks rules | clean |
| Web build | `npm run build` | Production build, 42 routes | passes |
| Web E2E | `npm run test:e2e` (API on :8010 + web on :3000 running) | Barcode lookup → explained score; invalid barcode; register → allergy → critical allergen alert → history; encyclopedia (desktop + Pixel 7) | **8 passed** |
| Mobile analyze + tests | `cd mobile && flutter analyze && flutter test` | Offline queue sync/retry, API error codes, product cache, allergen banner ordering, colour mapping, photo upload (multipart + token), assistant chat (sends product, shows grounded answer, signed-out state), AI error messages, upgrade notice, diary (targets, water, plan lock), Explore modules | **13 passed**, analyze clean |

E2E uses the live Open Food Facts API for one stable barcode, so it needs internet access.

## Not yet automated (manual or pending)
- Camera barcode scanning on physical devices (tested via manual entry and decoder configuration only).
- OCR accuracy across lighting conditions and label layouts. The parser tests cover OCR-style errors;
  a photo corpus benchmark is still to do.
- Accessibility audit (axe/Lighthouse). The UI uses semantic roles, labels, focus rings, 44 px targets and
  reduced-motion support, but it hasn't been formally audited.
- Load testing on a large catalogue (Locust/k6 against PostgreSQL).
- Dependency vulnerability scanning: run `pip-audit -r backend/requirements.txt` and `npm audit` in CI.
