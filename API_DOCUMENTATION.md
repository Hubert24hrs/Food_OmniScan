# API Documentation

Base URL: `/api/v1`. Interactive docs (dev/staging only): `GET /docs` (OpenAPI 3.1 at `/openapi.json`).

## Conventions
- **Auth:** `Authorization: Bearer <token>`. The token is either a local JWT from `/auth/login` or a
  Firebase ID token (`AUTH_PROVIDER=firebase|both`).
- **Errors:** `{"detail": {"code": "...", "message": "..."}}` or `{"detail": "..."}`. Stable codes:
  `invalid_barcode` (422), `product_not_found` (404), `provider_unavailable` (503), `validation_error` (422),
  `consent_required` (403), `plan_limit` / `quota_exceeded` (402), `ai_not_configured` (503), `ai_failed` (502),
  `billing_not_configured` (503).
- **Rate limits:** per IP (auth 10/min, scan 120/min, search 30/min by default) → `429`.
- **Units:** nutrient values per 100 g (or 100 ml for beverages); `sodium` in **grams** in nutrition objects,
  `sodium_mg` where named. Scores use FDA Daily Values (see SCORING_METHODOLOGY.md).

## Key flows

### Scan a barcode
`GET /products/barcode/{code}?profile_ids=...` → `{product, analysis, sources, stale}`
- Validates EAN-13 / EAN-8 / UPC-A / UPC-E / GTIN-14 check digits.
- Lookup order: cache → Open Food Facts → USDA FoodData Central (fills gaps such as US added sugars).
- `analysis.score`: overall, grade, color, confidence, components with explained `adjustments`,
  `caps_applied`, `highlights` (seed oils, sweeteners, colours…), `front_of_pack` (FDA Low/Med/High per serving).
- `analysis.allergens`: `contains | may_contain | not_detected | unknown` with evidence.
- `analysis.compatibility[]`: per profile `verdict` (green/yellow/red), `critical_allergen_alerts`, `reasons`.
- Records the scan in history when authenticated.

### Analyze label text (on-device OCR output)
`POST /analysis/text` `{ingredients_text?, nutrition_text?, nutrition?, is_beverage, profile_ids?}`. Nothing
is saved. `POST /analysis/nutrition-label` `{text}` parses a US Nutrition Facts panel or an EU table into
per-100 g values with per-field confidence.

### Unknown product submission → moderation
`POST /uploads` (multipart `image`) → `image_id`; `POST /submissions` → pending; moderator
`POST /admin/submissions/{id}/review` `{action: approve|reject|needs_info}` creates a verified
community product and notifies the contributor.

### Offline sync
`POST /scans/sync` `[{client_id, barcode, scanned_at}]`, idempotent on `client_id`. Returns
`found | not_found | invalid | retry_later` per item.

### Billing webhooks
`POST /billing/webhooks/stripe` (Stripe-Signature), `/revenuecat` (Authorization), `/paystack`
(x-paystack-signature). All idempotent.

## Example
```bash
curl -s localhost:8000/api/v1/products/barcode/3017620422003 | jq '.analysis.score | {overall, grade, confidence}'
```

## Endpoint reference (generated)

<!-- BEGIN GENERATED -->

| Method | Path | Summary | Token |
|---|---|---|---|
| GET | `/api/v1/admin/ai-usage` | Ai Usage | admin or moderator role |
| GET | `/api/v1/admin/analytics` | Analytics | admin or moderator role |
| GET | `/api/v1/admin/articles` | Admin Articles | admin or moderator role |
| PUT | `/api/v1/admin/articles/{slug}` | Upsert Article | admin or moderator role |
| DELETE | `/api/v1/admin/articles/{slug}` | Delete Article | admin or moderator role |
| GET | `/api/v1/admin/audit-logs` | Audit Logs | admin or moderator role |
| GET | `/api/v1/admin/entitlements` | Get Entitlements | admin or moderator role |
| PUT | `/api/v1/admin/entitlements` | Put Entitlement | admin or moderator role |
| POST | `/api/v1/admin/ingredients` | Create Ingredient | admin or moderator role |
| PATCH | `/api/v1/admin/ingredients/{slug}` | Patch Ingredient | admin or moderator role |
| POST | `/api/v1/admin/jobs/daily` | Run Daily Jobs | admin or moderator role |
| POST | `/api/v1/admin/lab-reports` | Create Lab | admin or moderator role |
| GET | `/api/v1/admin/lab-reports` | Lab Reports | admin or moderator role |
| POST | `/api/v1/admin/lab-reports/{report_id}/verify` | Verify Lab | admin or moderator role |
| GET | `/api/v1/admin/methodologies` | Methodologies | admin or moderator role |
| POST | `/api/v1/admin/methodologies` | Publish Methodology | admin or moderator role |
| POST | `/api/v1/admin/methodologies/{version}/activate` | Activate Methodology | admin or moderator role |
| POST | `/api/v1/admin/notifications/broadcast` | Broadcast | admin or moderator role |
| DELETE | `/api/v1/admin/prices/{price_id}` | Delete Price | admin or moderator role |
| GET | `/api/v1/admin/products` | Admin Products | admin or moderator role |
| POST | `/api/v1/admin/products` | Create Product | admin or moderator role |
| PATCH | `/api/v1/admin/products/{pid}` | Patch Product | admin or moderator role |
| GET | `/api/v1/admin/recalls` | Recalls | admin or moderator role |
| POST | `/api/v1/admin/recalls` | Create Recall | admin or moderator role |
| GET | `/api/v1/admin/recipes` | Admin Recipes | admin or moderator role |
| PATCH | `/api/v1/admin/recipes/{recipe_id}` | Patch Recipe | admin or moderator role |
| GET | `/api/v1/admin/scans/failed` | Failed Scans | admin or moderator role |
| POST | `/api/v1/admin/sources` | Create Source | admin or moderator role |
| POST | `/api/v1/admin/sources/{key}/verify` | Verify Source | admin or moderator role |
| GET | `/api/v1/admin/stats` | Stats | admin or moderator role |
| GET | `/api/v1/admin/submissions` | List Submissions | admin or moderator role |
| POST | `/api/v1/admin/submissions/{sid}/review` | Review Submission | admin or moderator role |
| GET | `/api/v1/admin/users` | Users | admin or moderator role |
| PATCH | `/api/v1/admin/users/{uid}` | Patch User | admin or moderator role |
| POST | `/api/v1/analysis/image` | Analyze Image | accepted (see route) |
| POST | `/api/v1/analysis/nutrition-label` | Nutrition Label | not used |
| POST | `/api/v1/analysis/text` | Analyze Text | accepted (see route) |
| GET | `/api/v1/articles` | Articles | not used |
| GET | `/api/v1/articles/{slug}` | Article | not used |
| POST | `/api/v1/assistant/ask` | Ask | accepted (see route) |
| POST | `/api/v1/auth/login` | Login | not used |
| POST | `/api/v1/auth/register` | Register | not used |
| POST | `/api/v1/billing/checkout` | Checkout | accepted (see route) |
| GET | `/api/v1/billing/me` | My Billing | accepted (see route) |
| GET | `/api/v1/billing/plans` | Plans | not used |
| POST | `/api/v1/billing/webhooks/paystack` | Paystack Webhook | not used |
| POST | `/api/v1/billing/webhooks/revenuecat` | Revenuecat Webhook | not used |
| POST | `/api/v1/billing/webhooks/stripe` | Stripe Webhook | not used |
| PUT | `/api/v1/budget` | Set Budget | accepted (see route) |
| GET | `/api/v1/budget` | Budget Summary | accepted (see route) |
| GET | `/api/v1/categories` | Categories | not used |
| POST | `/api/v1/compare` | Compare | accepted (see route) |
| GET | `/api/v1/compare/{token}` | Shared Comparison | not used |
| GET | `/api/v1/diary` | Get Day | accepted (see route) |
| POST | `/api/v1/diary/entries` | Add Entry | accepted (see route) |
| POST | `/api/v1/diary/entries/bulk` | Add Entries | accepted (see route) |
| DELETE | `/api/v1/diary/entries/{entry_id}` | Delete Entry | accepted (see route) |
| PUT | `/api/v1/diary/goals` | Set Goals | accepted (see route) |
| GET | `/api/v1/diary/insights` | Food Insights | accepted (see route) |
| GET | `/api/v1/diary/report` | Report | accepted (see route) |
| GET | `/api/v1/diary/summary` | Summary | accepted (see route) |
| POST | `/api/v1/diary/water` | Add Water | accepted (see route) |
| DELETE | `/api/v1/diary/water/{log_id}` | Delete Water | accepted (see route) |
| PUT | `/api/v1/diary/weight` | Log Weight | accepted (see route) |
| GET | `/api/v1/diary/weight` | Weight History | accepted (see route) |
| GET | `/api/v1/favourites` | List Favs | accepted (see route) |
| POST | `/api/v1/favourites` | Add Fav | accepted (see route) |
| DELETE | `/api/v1/favourites/{fav_id}` | Del Fav | accepted (see route) |
| GET | `/api/v1/history` | History | accepted (see route) |
| DELETE | `/api/v1/history/{history_id}` | Hide History | accepted (see route) |
| GET | `/api/v1/household` | My Household | accepted (see route) |
| POST | `/api/v1/household` | Create Household | accepted (see route) |
| POST | `/api/v1/household/invite` | Invite | accepted (see route) |
| POST | `/api/v1/household/invites/{member_id}/accept` | Accept Invite | accepted (see route) |
| DELETE | `/api/v1/household/members/{member_id}` | Remove Member | accepted (see route) |
| GET | `/api/v1/ingredients` | List Ingredients | not used |
| GET | `/api/v1/ingredients/{slug}` | Get Ingredient | not used |
| GET | `/api/v1/local-foods` | Local Foods | not used |
| GET | `/api/v1/me` | Get Me | accepted (see route) |
| DELETE | `/api/v1/me` | Delete Account | accepted (see route) |
| PATCH | `/api/v1/me` | Patch Me | accepted (see route) |
| GET | `/api/v1/me/export` | Export Data | accepted (see route) |
| GET | `/api/v1/me/usage` | Usage | accepted (see route) |
| GET | `/api/v1/meal-plans` | List Plans | accepted (see route) |
| POST | `/api/v1/meal-plans` | Create Plan | accepted (see route) |
| POST | `/api/v1/meal-plans/generate` | Generate Plan | accepted (see route) |
| GET | `/api/v1/meal-plans/{plan_id}` | Get Plan | accepted (see route) |
| PUT | `/api/v1/meal-plans/{plan_id}` | Update Plan | accepted (see route) |
| DELETE | `/api/v1/meal-plans/{plan_id}` | Delete Plan | accepted (see route) |
| POST | `/api/v1/meal-plans/{plan_id}/shopping-list` | Plan To List | accepted (see route) |
| GET | `/api/v1/meta` | Meta | not used |
| GET | `/api/v1/notifications` | Notifications | accepted (see route) |
| POST | `/api/v1/notifications/{nid}/read` | Mark Read | accepted (see route) |
| GET | `/api/v1/pantry` | List Pantry | accepted (see route) |
| POST | `/api/v1/pantry` | Add Pantry | accepted (see route) |
| GET | `/api/v1/pantry/expiring` | Expiring | accepted (see route) |
| PATCH | `/api/v1/pantry/{item_id}` | Patch Pantry | accepted (see route) |
| DELETE | `/api/v1/pantry/{item_id}` | Delete Pantry | accepted (see route) |
| POST | `/api/v1/prices/compare` | Compare Prices | accepted (see route) |
| GET | `/api/v1/products/barcode/{code}` | Scan Barcode | accepted (see route) |
| GET | `/api/v1/products/search` | Search | not used |
| GET | `/api/v1/products/{product_id}` | Get Product | accepted (see route) |
| GET | `/api/v1/products/{product_id}/alternatives` | Alternatives | accepted (see route) |
| GET | `/api/v1/products/{product_id}/details` | Product Details | not used |
| POST | `/api/v1/products/{product_id}/prices` | Report Price | accepted (see route) |
| GET | `/api/v1/products/{product_id}/prices` | Product Prices | accepted (see route) |
| POST | `/api/v1/products/{product_id}/report` | Report Issue | accepted (see route) |
| GET | `/api/v1/products/{product_id}/reviews` | List Reviews | not used |
| PUT | `/api/v1/products/{product_id}/reviews` | Upsert Review | accepted (see route) |
| POST | `/api/v1/products/{product_id}/share` | Share Product | accepted (see route) |
| GET | `/api/v1/profiles` | List Profiles | accepted (see route) |
| POST | `/api/v1/profiles` | Create Profile | accepted (see route) |
| GET | `/api/v1/profiles/options` | Options | not used |
| PATCH | `/api/v1/profiles/{profile_id}` | Update Profile | accepted (see route) |
| DELETE | `/api/v1/profiles/{profile_id}` | Delete Profile | accepted (see route) |
| GET | `/api/v1/profiles/{profile_id}` | Get Profile | accepted (see route) |
| POST | `/api/v1/profiles/{profile_id}/activate` | Activate | accepted (see route) |
| PUT | `/api/v1/profiles/{profile_id}/allergens` | Set Allergens | accepted (see route) |
| PUT | `/api/v1/profiles/{profile_id}/avoid` | Set Avoid | accepted (see route) |
| PUT | `/api/v1/profiles/{profile_id}/diets` | Set Diets | accepted (see route) |
| POST | `/api/v1/purchases` | Add Purchase | accepted (see route) |
| GET | `/api/v1/purchases` | Purchases | accepted (see route) |
| DELETE | `/api/v1/purchases/{purchase_id}` | Delete Purchase | accepted (see route) |
| GET | `/api/v1/rankings` | Rankings | accepted (see route) |
| GET | `/api/v1/recalls` | Recalls | not used |
| GET | `/api/v1/recipes` | List Recipes | accepted (see route) |
| POST | `/api/v1/recipes` | Create Recipe | accepted (see route) |
| POST | `/api/v1/recipes/generate` | Generate Recipe | accepted (see route) |
| GET | `/api/v1/recipes/{recipe_id}` | Get Recipe | accepted (see route) |
| DELETE | `/api/v1/recipes/{recipe_id}` | Delete Recipe | accepted (see route) |
| POST | `/api/v1/recipes/{recipe_id}/nutrition-estimate` | Estimate Nutrition | accepted (see route) |
| POST | `/api/v1/recipes/{recipe_id}/shopping-list` | Recipe To List | accepted (see route) |
| GET | `/api/v1/recommendations` | Recommendations | accepted (see route) |
| GET | `/api/v1/safety/topics` | Safety Topics | not used |
| POST | `/api/v1/scans/sync` | Sync Scans | accepted (see route) |
| GET | `/api/v1/shared/{token}` | Shared Report | not used |
| GET | `/api/v1/shopping-lists` | All Lists | accepted (see route) |
| POST | `/api/v1/shopping-lists` | Create | accepted (see route) |
| DELETE | `/api/v1/shopping-lists/{list_id}` | Delete | accepted (see route) |
| POST | `/api/v1/shopping-lists/{list_id}/items` | Add Item | accepted (see route) |
| PATCH | `/api/v1/shopping-lists/{list_id}/items/{item_id}` | Patch Item | accepted (see route) |
| DELETE | `/api/v1/shopping-lists/{list_id}/items/{item_id}` | Delete Item | accepted (see route) |
| GET | `/api/v1/sources` | List Sources | not used |
| POST | `/api/v1/submissions` | Submit | accepted (see route) |
| GET | `/api/v1/submissions/mine` | Mine | accepted (see route) |
| POST | `/api/v1/uploads` | Upload | accepted (see route) |
| GET | `/api/v1/uploads/{name}` | Get Upload | not used |
| GET | `/health` | Health | not used |

<!-- END GENERATED -->
