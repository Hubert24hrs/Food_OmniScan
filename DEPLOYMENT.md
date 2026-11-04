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

## Quickest low-cost launch: Railway (about $5–10 a month)
One Railway project runs the API, the website and PostgreSQL from this GitHub repo, with free HTTPS addresses
(`*.up.railway.app`) until you add your own domain. `backend/railway.json` and `web/railway.json` set the build and health checks.

1. Sign up at railway.com with GitHub and choose the Hobby plan.
2. **New project → Deploy PostgreSQL.**
3. **New → GitHub repo → Food_OmniScan**, root directory `backend`. Variables:
   `PORT=8000`, `ENVIRONMENT=production`, `DATABASE_URL=${{Postgres.DATABASE_URL}}` (plain `postgresql://` URLs are converted
   automatically), `JWT_SECRET` (long random string), `GEMINI_API_KEY`, `REVENUECAT_WEBHOOK_AUTH`,
   `CORS_ORIGINS` and `PUBLIC_APP_URL` (the web address from step 4). Add a **volume** mounted at `/app/uploads` and set
   `RAILWAY_RUN_UID=0` so the container can write to it. **Settings → Networking → Generate domain.**
4. **New → GitHub repo → Food_OmniScan** again, root directory `web`. Variables: `PORT=3000`,
   `NEXT_PUBLIC_API_URL=https://<api domain>/api/v1`, `NEXT_PUBLIC_SUPPORT_EMAIL=<support address>`. Generate a domain.
5. Check `https://<web domain>/privacy`, `/terms` and `/account-deletion`, and `https://<api domain>/health`.
6. Create the Play reviewer account on the live site and give it Premium (Admin → Users, or a `manual` subscription row).

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
7. Schedule the daily job once a day (Cloud Scheduler → Cloud Run job): `python -m app.services.alerts`.
   It sends pantry expiry reminders every day, and weekly nutrition reports and tips on Mondays.

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
