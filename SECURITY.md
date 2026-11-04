# Security & Privacy

## Reporting a vulnerability
Email security@foodomniscan.app (placeholder; set up before launch) with steps to reproduce. Please don't open a
public issue for vulnerabilities.

## Authentication
- **Firebase Authentication** (production target, `AUTH_PROVIDER=firebase`): ID tokens are verified server-side
  against Google's public certificates with issuer and audience checks (`FIREBASE_PROJECT_ID`). No service-account
  secret is needed for verification.
- **Local auth** (`AUTH_PROVIDER=local`, dev/self-host): bcrypt (cost 12) password hashes, HS256 JWT with issuer
  claim and expiry. `JWT_SECRET` must be a strong random value; the app refuses to start in production with the
  default secret.
- Passwords are 8–72 bytes and need an uppercase letter and a digit. Auth endpoints are rate limited per IP.

## Authorization
- Roles: `user` < `contributor` < `moderator` < `admin`.
- **Every admin route re-reads the role from the database** (`require_role`). The role claim in the JWT is
  informational and never trusted. Client-side role checks only hide UI.
- Role grants are recorded in `admin_users`. Every admin/moderator mutation writes to `admin_audit_logs` with
  before/after snapshots, actor, IP and reason.
- Ownership is enforced on profiles, lists, diary entries, favourites and history. Another user's resource returns
  404, which avoids enumeration.

## Sensitive data (allergies, diets, health goals)
- Treated as **health data** under GDPR Art. 9 / UK GDPR, and as sensitive personal data under CCPA/CPRA and
  NDPR/NDPA (Nigeria).
- **Explicit consent is required** before any allergy or diet data is stored (`consent_health_data`).
  Withdrawing consent deletes that data immediately.
- **Data export:** `GET /api/v1/me/export` returns everything held about the user as JSON.
- **Account deletion:** `DELETE /api/v1/me` (with `{"confirm": "DELETE"}`) hard-deletes the account and its cascade.
- AI conversations are **not stored** by default (`history_stored: false`). The client keeps history, and the
  `consent_ai_history` flag is reserved for opt-in storage.
- Shared comparison links strip personal compatibility verdicts.

## Secrets
- Every secret (AI keys, USDA key, Stripe/RevenueCat/Paystack secrets, JWT secret) is server-side, set by
  environment variable, and documented in `backend/.env.example` without values. **No secret is shipped to the
  web or mobile clients.** Clients call the API, which calls the providers.
- The Gemini key is sent in the `x-goog-api-key` header, not the URL, so it doesn't land in proxy logs.

## Payments
- Entitlements come only from verified server-side webhooks:
  - Stripe: `Stripe-Signature` HMAC-SHA256 with a 5-minute timestamp tolerance
  - RevenueCat: shared `Authorization` secret, compared in constant time
  - Paystack: `x-paystack-signature` HMAC-SHA512
- All webhooks are idempotent through `payment_events (provider, event_id)`.
- Quotas are enforced server-side (`402 quota_exceeded`). Failed AI calls are recorded with 0 credits.

## Input handling & abuse protection
- Pydantic validation on every request body, with length limits on free text and numeric bounds on nutrients.
- SQL goes through the SQLAlchemy ORM with bound parameters; no string-built SQL.
- Uploads: 8 MB cap, Pillow format sniffing (JPEG/PNG/WebP only), a decompression-bomb guard, and re-encoding to
  JPEG, which strips EXIF/GPS metadata. Random filenames, path-traversal checks on fetch.
- Sliding-window rate limits per IP: auth, scan and search buckets. The limiter is in-process, so use a gateway
  or Redis limiter when running several replicas.
- Security headers: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS in production, and
  `Cache-Control: private, no-store` on authenticated GETs.
- OpenAPI docs are disabled in production.

## Transport & storage
- TLS terminates at the load balancer or ingress; the API sets HSTS in production.
- PostgreSQL: enable encryption at rest (managed providers do this by default), use least-privilege DB users and
  automated backups (see DEPLOYMENT.md).

## Known gaps (tracked)
- Web stores the access token in `localStorage`. Before launch, move to httpOnly cookies via a same-site API route
  or Firebase's SDK persistence, and add a strict CSP.
- No refresh tokens for local auth (24 h expiry). Firebase handles refresh in the production setup.
- No automated dependency scanning in CI yet. Run `pip-audit` and `npm audit` (see TESTING.md).

## Health & legal disclaimers
The app gives general nutrition information. It doesn't diagnose or treat, and it doesn't certify that a food is
safe for an allergy. Allergen results always tell users to check the physical label, and AI output is labelled as
AI-generated.
