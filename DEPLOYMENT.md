# Deployment

## Local development
```bash
# API
cd backend
py -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt   # Windows
# python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt        # macOS/Linux
cp .env.example .env          # set JWT_SECRET; optional USDA_API_KEY, GEMINI_API_KEY
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
# SQLite tables are created and reference data is seeded automatically in development.

# Web
cd web && npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 > .env.local
npm run dev                   # http://localhost:3000

# Mobile (Android emulator reaches the host at 10.0.2.2)
cd mobile && flutter pub get
flutter run --dart-define=API_URL=http://10.0.2.2:8000/api/v1
```
Make an admin: put your email in `BOOTSTRAP_ADMIN_EMAILS` before registering (or have an existing admin
change your role in the admin console).

## Docker (full stack with PostgreSQL)
```bash
cp backend/.env.example backend/.env    # fill JWT_SECRET
docker compose up --build               # API :8000 (runs alembic upgrade head), web :3000, Postgres
```

## Production (recommended: Google Cloud)
| Component | Service |
|---|---|
| API | Cloud Run (container from `backend/Dockerfile`), min instances ≥1, 2 workers per instance |
| Database | Cloud SQL for PostgreSQL 16, private IP, automated daily backups + PITR (7–30 days) |
| Web | Cloud Run or Vercel (`web/Dockerfile`, `NEXT_PUBLIC_API_URL` set at build) |
| Uploads | Cloud Storage bucket (switch `services/uploads.py`), CDN for product images |
| Secrets | Secret Manager → env vars (`JWT_SECRET`, `GEMINI_API_KEY`, `USDA_API_KEY`, Stripe/RevenueCat/Paystack) |
| Auth | Firebase Authentication (`AUTH_PROVIDER=firebase`, `FIREBASE_PROJECT_ID`) |
| Push | Firebase Cloud Messaging (pending integration, see README) |
| Monitoring | Cloud Logging/Error Reporting for the API; Firebase Crashlytics for mobile (pending) |

### Release steps
1. `ENVIRONMENT=production`, strong `JWT_SECRET`, `CORS_ORIGINS=https://app.yourdomain.com`.
2. Build and push the images; the API container runs `alembic upgrade head` on start (run migrations as a
   one-off job instead if you deploy many replicas at once).
3. Recommended PostgreSQL index for large catalogues:
   ```sql
   CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_products_search_fts
     ON products USING gin (to_tsvector('simple', coalesce(search_text, '')));
   ```
4. Configure webhooks:
   - Stripe → `https://api.../api/v1/billing/webhooks/stripe` (events: `customer.subscription.*`). Create
     prices with `metadata.tier` and set `STRIPE_PRICES`.
   - RevenueCat → `.../billing/webhooks/revenuecat` with the Authorization header = `REVENUECAT_WEBHOOK_AUTH`.
     Use product ids containing `plus`/`premium`/`family`, and set `app_user_id` to the Food omniScan user id.
   - Paystack → `.../billing/webhooks/paystack` (metadata `user_id`, `tier`).
5. Set a descriptive `OFF_USER_AGENT` with a contact address for your organisation (required by Open Food Facts).
6. Put a WAF or rate limiter in front (Cloud Armor), since the in-process limiter is per instance.

### Backups & recovery
- Cloud SQL automated backups + point-in-time recovery. Test a restore into a staging instance quarterly.
- Uploads bucket: object versioning + a 30-day lifecycle on non-current versions.
- Reference data is reproducible (`python -m app.db.seed`). User data and community submissions are not,
  so they rely on DB backups.

### Mobile release
- Android: `flutter build appbundle --dart-define=API_URL=https://api.../api/v1`, then the Play Console
  (Billing via RevenueCat).
- iOS: `flutter build ipa --dart-define=API_URL=...` on macOS with Xcode; camera and photo usage strings
  are already in `Info.plist`.
