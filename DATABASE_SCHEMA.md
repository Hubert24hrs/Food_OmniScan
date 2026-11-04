# Database Schema

PostgreSQL 15+ in staging/production; SQLite for local development and tests. The models live in
[`backend/app/models/`](backend/app/models) and migrations in [`backend/alembic/versions/`](backend/alembic/versions).

## Conventions
- Primary keys: UUID strings (`String(36)`), so ids can be generated client-side for offline sync.
- Timestamps: `timestamptz` (UTC). JSON columns are `JSONB` on PostgreSQL.
- Duplicate barcodes are blocked by `product_barcodes.gtin14` (unique). UPC-A `049000000443` and EAN-13
  `0049000000443` normalise to the same GTIN-14.
- **Provenance:** every product records `source`, `source_id`, `source_url`, `source_license`,
  `last_synced_at`, `verified_at/by` and `raw_data.provenance` (which provider supplied each field).
- **Raw data vs derived data:** `products.raw_data` keeps the provider payload subset untouched.
  `product_ingredients`, `product_scores` and `product_warnings` are derived and versioned
  (`analysis_version`, `methodology_version`, `inputs_hash`). AI output is never written to product tables.
- **Consent & privacy:** `users.consent_health_data_at` gates storage of `allergen_profiles`,
  `dietary_preferences` and `ingredient_avoidance_rules`. Withdrawing consent deletes those rows. Account
  deletion cascades through every user-owned table.
- **Multilingual:** `ingredient_synonyms (term, language, region)`, `products.ingredients_lang`,
  `ingredients.us_name` (US display name) alongside the international name.

## Entity groups

| Group | Tables |
|---|---|
| Accounts | `users`, `user_profiles` (settings), `family_profiles`, `dietary_preferences`, `allergen_profiles`, `ingredient_avoidance_rules`, `admin_users` |
| Catalogue | `products`, `product_barcodes`, `product_images`, `product_ingredients`, `nutrition_facts`, `food_categories`, `food_brands`, `manufacturers` |
| Knowledge | `ingredients`, `ingredient_synonyms`, `food_additives`, `scientific_sources` |
| Scoring | `scoring_methodologies`, `scoring_rules`, `product_scores`, `product_warnings` |
| Research | `product_evidence`, `laboratory_reports`, `product_recalls` |
| Activity | `food_scans` (raw log incl. failures), `scan_history`, `favourite_products`, `user_reviews`, `product_alternatives`, `product_comparisons`, `community_submissions` |
| Food management | `shopping_lists`, `shopping_list_items`, `food_diaries`, `meal_entries`, `meal_plans`, `recipes` |
| Commerce | `subscriptions`, `subscription_entitlements`, `ai_usage_records`, `payment_events` |
| Ops | `notifications`, `admin_audit_logs` |

## Migrations & seed
```bash
cd backend
alembic upgrade head          # apply migrations (production / staging)
python -m app.db.seed         # idempotent reference data (also runs on API startup)
alembic revision --autogenerate -m "describe change"   # after editing models
```
The seed loads only reference data (sources, ingredient knowledge base, scoring methodology,
plan matrix). **It doesn't seed any product records.**

## Database access policy
The API is the only client of the database. Use separate PostgreSQL roles: `omniscan_app` (DML on app
tables) and `omniscan_migrator` (DDL). Row ownership is enforced in the API layer. If you add
direct-access tools later (e.g. analytics), give them read replicas without the `users` PII columns.

## Tables (generated)
Regenerate with `python scripts/gen_docs.py` from `backend/`.

<!-- BEGIN GENERATED -->

### `admin_audit_logs`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `actor_id` | VARCHAR(36) | no | indexed |
| `action` | VARCHAR(60) | no | indexed |
| `entity` | VARCHAR(60) | no |  |
| `entity_id` | VARCHAR(64) | yes |  |
| `before` | JSON | yes |  |
| `after` | JSON | yes |  |
| `ip` | VARCHAR(64) | yes |  |
| `created_at` | DATETIME | no | indexed |
| `note` | TEXT | yes |  |
| `id` | VARCHAR(36) | no | PK |

### `admin_users`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), unique |
| `role` | VARCHAR(20) | no |  |
| `granted_by` | VARCHAR(36) | yes |  |
| `granted_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

### `ai_usage_records`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | yes | FK → `users.id` (SET NULL), indexed |
| `feature` | VARCHAR(40) | no | indexed |
| `provider` | VARCHAR(20) | no |  |
| `model` | VARCHAR(60) | yes |  |
| `input_tokens` | INTEGER | no |  |
| `output_tokens` | INTEGER | no |  |
| `credits` | INTEGER | no |  |
| `est_cost_usd` | FLOAT | no |  |
| `status` | VARCHAR(20) | no |  |
| `created_at` | DATETIME | no | indexed |
| `id` | VARCHAR(36) | no | PK |

### `allergen_profiles`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `profile_id` | VARCHAR(36) | no | FK → `family_profiles.id` (CASCADE), indexed |
| `allergen_code` | VARCHAR(40) | no |  |
| `severity` | VARCHAR(20) | no |  |
| `avoid_traces` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (profile_id, allergen_code)

### `community_submissions`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `kind` | VARCHAR(20) | no |  |
| `barcode` | VARCHAR(14) | yes | indexed |
| `product_id` | VARCHAR(36) | yes | FK → `products.id` (SET NULL) |
| `payload` | JSON | no |  |
| `images` | JSON | no |  |
| `ocr_confidence` | FLOAT | yes |  |
| `status` | VARCHAR(20) | no | indexed |
| `reviewer_id` | VARCHAR(36) | yes |  |
| `review_notes` | TEXT | yes |  |
| `reviewed_at` | DATETIME | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `dietary_preferences`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `profile_id` | VARCHAR(36) | no | FK → `family_profiles.id` (CASCADE), indexed |
| `code` | VARCHAR(40) | no |  |
| `strict` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (profile_id, code)

### `family_profiles`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `owner_user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `name` | VARCHAR(80) | no |  |
| `relationship_label` | VARCHAR(40) | yes |  |
| `is_primary` | BOOLEAN | no |  |
| `birth_year` | INTEGER | yes |  |
| `avatar_color` | VARCHAR(9) | yes |  |
| `goals` | JSON | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `favourite_products`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE) |
| `list_type` | VARCHAR(20) | no |  |
| `profile_id` | VARCHAR(36) | yes |  |
| `note` | VARCHAR(300) | yes |  |
| `created_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (user_id, product_id, list_type)

### `food_additives`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `e_number` | VARCHAR(10) | no | unique, indexed |
| `ingredient_id` | VARCHAR(36) | no | FK → `ingredients.id` (CASCADE), unique |
| `additive_class` | VARCHAR(60) | no |  |
| `adi_mg_per_kg_bw` | FLOAT | yes |  |
| `adi_source_key` | VARCHAR(80) | yes |  |
| `eu_status` | VARCHAR(40) | yes |  |
| `us_status` | VARCHAR(40) | yes |  |
| `notes` | TEXT | yes |  |
| `id` | VARCHAR(36) | no | PK |

### `food_brands`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `name` | VARCHAR(200) | no |  |
| `normalized_name` | VARCHAR(200) | no | unique, indexed |
| `manufacturer_id` | VARCHAR(36) | yes | FK → `manufacturers.id` (SET NULL) |
| `country` | VARCHAR(2) | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `food_categories`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `code` | VARCHAR(160) | no | unique, indexed |
| `name` | VARCHAR(160) | no |  |
| `parent_id` | VARCHAR(36) | yes | FK → `food_categories.id` (SET NULL) |
| `is_beverage` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |

### `food_diaries`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `profile_id` | VARCHAR(36) | no | FK → `family_profiles.id` (CASCADE) |
| `day` | DATE | no | indexed |
| `id` | VARCHAR(36) | no | PK |

Unique: (profile_id, day)

### `food_scans`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | yes | FK → `users.id` (CASCADE), indexed |
| `profile_id` | VARCHAR(36) | yes |  |
| `scan_type` | VARCHAR(20) | no |  |
| `barcode` | VARCHAR(14) | yes | indexed |
| `product_id` | VARCHAR(36) | yes | FK → `products.id` (SET NULL), indexed |
| `status` | VARCHAR(20) | no |  |
| `confidence` | FLOAT | yes |  |
| `ocr_text` | TEXT | yes |  |
| `image_url` | VARCHAR(500) | yes |  |
| `client_id` | VARCHAR(64) | yes |  |
| `client_scanned_at` | DATETIME | yes |  |
| `created_at` | DATETIME | no | indexed |
| `id` | VARCHAR(36) | no | PK |

Unique: (user_id, client_id)

### `ingredient_avoidance_rules`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `profile_id` | VARCHAR(36) | no | FK → `family_profiles.id` (CASCADE), indexed |
| `term` | VARCHAR(120) | no |  |
| `ingredient_slug` | VARCHAR(120) | yes |  |
| `reason` | VARCHAR(200) | yes |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (profile_id, term)

### `ingredient_synonyms`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `ingredient_id` | VARCHAR(36) | no | FK → `ingredients.id` (CASCADE), indexed |
| `term` | VARCHAR(160) | no | indexed |
| `language` | VARCHAR(8) | no |  |
| `region` | VARCHAR(8) | yes |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (term, language)

### `ingredients`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `slug` | VARCHAR(120) | no | unique, indexed |
| `name` | VARCHAR(200) | no |  |
| `us_name` | VARCHAR(200) | yes |  |
| `category` | VARCHAR(60) | no | indexed |
| `function` | VARCHAR(300) | yes |  |
| `plain_language` | TEXT | yes |  |
| `concern_level` | VARCHAR(20) | no | indexed |
| `concern_summary` | TEXT | yes |  |
| `e_number` | VARCHAR(10) | yes | indexed |
| `is_additive` | BOOLEAN | no |  |
| `vegan` | VARCHAR(8) | no |  |
| `vegetarian` | VARCHAR(8) | no |  |
| `halal_concern` | VARCHAR(8) | no |  |
| `allergen_code` | VARCHAR(40) | yes |  |
| `flags` | JSON | no |  |
| `fodmap` | VARCHAR(8) | yes |  |
| `regulatory_notes` | JSON | no |  |
| `source_keys` | JSON | no |  |
| `verification_status` | VARCHAR(20) | no |  |
| `verified_by` | VARCHAR(36) | yes |  |
| `verified_at` | DATETIME | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `laboratory_reports`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `lab_name` | VARCHAR(200) | no |  |
| `method` | VARCHAR(200) | yes |  |
| `batch` | VARCHAR(80) | yes |  |
| `tested_on` | DATE | yes |  |
| `analyte` | VARCHAR(60) | no | indexed |
| `value` | FLOAT | yes |  |
| `unit` | VARCHAR(20) | no |  |
| `threshold` | FLOAT | yes |  |
| `threshold_jurisdiction` | VARCHAR(60) | yes |  |
| `threshold_reference` | VARCHAR(300) | yes |  |
| `exceeds_threshold` | BOOLEAN | yes |  |
| `source_id` | VARCHAR(36) | yes | FK → `scientific_sources.id` (SET NULL) |
| `verified` | BOOLEAN | no |  |
| `verified_by` | VARCHAR(36) | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `manufacturers`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `name` | VARCHAR(200) | no |  |
| `normalized_name` | VARCHAR(200) | no | unique, indexed |
| `country` | VARCHAR(2) | yes |  |
| `website` | VARCHAR(300) | yes |  |
| `parent_company` | VARCHAR(200) | yes |  |
| `transparency_notes` | TEXT | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `meal_entries`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `diary_id` | VARCHAR(36) | no | FK → `food_diaries.id` (CASCADE), indexed |
| `meal_type` | VARCHAR(20) | no |  |
| `product_id` | VARCHAR(36) | yes | FK → `products.id` (SET NULL) |
| `description` | VARCHAR(200) | no |  |
| `quantity_g` | FLOAT | yes |  |
| `energy_kcal` | FLOAT | yes |  |
| `protein` | FLOAT | yes |  |
| `carbohydrates` | FLOAT | yes |  |
| `fat` | FLOAT | yes |  |
| `fiber` | FLOAT | yes |  |
| `sugars` | FLOAT | yes |  |
| `sodium` | FLOAT | yes |  |
| `source` | VARCHAR(20) | no |  |
| `is_estimate` | BOOLEAN | no |  |
| `created_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

### `meal_plans`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `profile_id` | VARCHAR(36) | yes |  |
| `name` | VARCHAR(120) | no |  |
| `start_date` | DATE | yes |  |
| `days` | JSON | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `notifications`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `kind` | VARCHAR(30) | no |  |
| `title` | VARCHAR(200) | no |  |
| `body` | TEXT | no |  |
| `data` | JSON | no |  |
| `read_at` | DATETIME | yes |  |
| `created_at` | DATETIME | no | indexed |
| `id` | VARCHAR(36) | no | PK |

### `nutrition_facts`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `basis` | VARCHAR(10) | no |  |
| `serving_size_g` | FLOAT | yes |  |
| `energy_kcal` | FLOAT | yes |  |
| `energy_kj` | FLOAT | yes |  |
| `fat` | FLOAT | yes |  |
| `saturated_fat` | FLOAT | yes |  |
| `trans_fat` | FLOAT | yes |  |
| `carbohydrates` | FLOAT | yes |  |
| `sugars` | FLOAT | yes |  |
| `added_sugars` | FLOAT | yes |  |
| `fiber` | FLOAT | yes |  |
| `protein` | FLOAT | yes |  |
| `salt` | FLOAT | yes |  |
| `sodium` | FLOAT | yes |  |
| `cholesterol_mg` | FLOAT | yes |  |
| `fruits_veg_nuts_pct` | FLOAT | yes |  |
| `extra` | JSON | no |  |
| `source` | VARCHAR(20) | no |  |
| `confidence` | FLOAT | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

Unique: (product_id, basis)

### `payment_events`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `provider` | VARCHAR(20) | no |  |
| `event_id` | VARCHAR(160) | no |  |
| `event_type` | VARCHAR(80) | no |  |
| `payload` | JSON | no |  |
| `processed_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (provider, event_id)

### `product_alternatives`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `alternative_product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE) |
| `methodology_version` | VARCHAR(20) | no |  |
| `score_delta` | INTEGER | no |  |
| `reasons` | JSON | no |  |
| `computed_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (product_id, alternative_product_id, methodology_version)

### `product_barcodes`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `gtin14` | VARCHAR(14) | no | unique, indexed |
| `barcode` | VARCHAR(14) | no | indexed |
| `format` | VARCHAR(10) | no |  |
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `id` | VARCHAR(36) | no | PK |

### `product_comparisons`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | yes | FK → `users.id` (CASCADE), indexed |
| `product_ids` | JSON | no |  |
| `objective` | VARCHAR(30) | no |  |
| `result` | JSON | no |  |
| `share_token` | VARCHAR(32) | no | unique, indexed |
| `created_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

### `product_evidence`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `source_id` | VARCHAR(36) | yes | FK → `scientific_sources.id` (SET NULL) |
| `claim` | TEXT | no |  |
| `evidence_type` | VARCHAR(30) | no |  |
| `verified` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `product_images`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `kind` | VARCHAR(20) | no |  |
| `url` | VARCHAR(500) | no |  |
| `source` | VARCHAR(20) | no |  |
| `uploaded_by` | VARCHAR(36) | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `product_ingredients`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `position` | INTEGER | no |  |
| `depth` | INTEGER | no |  |
| `raw_text` | VARCHAR(300) | no |  |
| `ingredient_slug` | VARCHAR(120) | yes | indexed |
| `percent` | FLOAT | yes |  |
| `match_confidence` | FLOAT | no |  |
| `analysis_version` | VARCHAR(20) | yes |  |
| `id` | VARCHAR(36) | no | PK |

### `product_recalls`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | yes | FK → `products.id` (SET NULL), indexed |
| `barcode` | VARCHAR(14) | yes | indexed |
| `title` | VARCHAR(300) | no |  |
| `reason` | TEXT | no |  |
| `hazard` | VARCHAR(60) | yes |  |
| `jurisdiction` | VARCHAR(10) | no |  |
| `authority` | VARCHAR(80) | no |  |
| `recall_date` | DATE | yes |  |
| `url` | VARCHAR(500) | yes |  |
| `status` | VARCHAR(20) | no |  |
| `verified` | BOOLEAN | no |  |
| `notified_at` | DATETIME | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `product_scores`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `methodology_version` | VARCHAR(20) | no | indexed |
| `inputs_hash` | VARCHAR(64) | no |  |
| `overall` | INTEGER | yes |  |
| `grade` | VARCHAR(20) | no |  |
| `confidence` | VARCHAR(10) | no |  |
| `coverage` | FLOAT | no |  |
| `result` | JSON | no |  |
| `computed_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (product_id, methodology_version, inputs_hash)

### `product_warnings`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `code` | VARCHAR(80) | no |  |
| `severity` | VARCHAR(10) | no |  |
| `title` | VARCHAR(200) | no |  |
| `explanation` | TEXT | no |  |
| `evidence_type` | VARCHAR(30) | no |  |
| `source_keys` | JSON | no |  |
| `methodology_version` | VARCHAR(20) | no |  |
| `id` | VARCHAR(36) | no | PK |

### `products`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `name` | VARCHAR(300) | yes | indexed |
| `generic_name` | VARCHAR(300) | yes |  |
| `brand_id` | VARCHAR(36) | yes | FK → `food_brands.id` (SET NULL), indexed |
| `brand_text` | VARCHAR(300) | yes |  |
| `category_id` | VARCHAR(36) | yes | FK → `food_categories.id` (SET NULL), indexed |
| `categories_tags` | JSON | no |  |
| `quantity` | VARCHAR(80) | yes |  |
| `serving_size` | VARCHAR(80) | yes |  |
| `countries_tags` | JSON | no |  |
| `labels_tags` | JSON | no |  |
| `packaging_text` | TEXT | yes |  |
| `packaging_tags` | JSON | no |  |
| `ingredients_text` | TEXT | yes |  |
| `ingredients_lang` | VARCHAR(8) | yes |  |
| `allergens_tags` | JSON | no |  |
| `traces_tags` | JSON | no |  |
| `additives_tags` | JSON | no |  |
| `ingredients_analysis_tags` | JSON | no |  |
| `nova_group` | INTEGER | yes |  |
| `nova_source` | VARCHAR(20) | yes |  |
| `nutriscore_grade` | VARCHAR(2) | yes |  |
| `image_url` | VARCHAR(500) | yes |  |
| `nafdac_number` | VARCHAR(40) | yes | indexed |
| `is_beverage` | BOOLEAN | no |  |
| `source` | VARCHAR(20) | no | indexed |
| `source_id` | VARCHAR(80) | yes |  |
| `source_url` | VARCHAR(500) | yes |  |
| `source_license` | VARCHAR(120) | yes |  |
| `raw_data` | JSON | yes |  |
| `status` | VARCHAR(20) | no | indexed |
| `completeness` | FLOAT | no |  |
| `last_synced_at` | DATETIME | yes |  |
| `verified_at` | DATETIME | yes |  |
| `verified_by` | VARCHAR(36) | yes |  |
| `search_text` | TEXT | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `recipes`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `title` | VARCHAR(200) | no | indexed |
| `cuisine` | VARCHAR(60) | yes |  |
| `region` | VARCHAR(8) | yes |  |
| `ingredients` | JSON | no |  |
| `steps` | JSON | no |  |
| `nutrition` | JSON | yes |  |
| `nutrition_is_estimate` | BOOLEAN | no |  |
| `source` | VARCHAR(300) | yes |  |
| `verified` | BOOLEAN | no |  |
| `created_by` | VARCHAR(36) | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `scan_history`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE) |
| `profile_id` | VARCHAR(36) | yes |  |
| `first_scanned_at` | DATETIME | no |  |
| `last_scanned_at` | DATETIME | no | indexed |
| `scan_count` | INTEGER | no |  |
| `hidden` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (user_id, product_id)

### `scientific_sources`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `key` | VARCHAR(80) | no | unique, indexed |
| `title` | VARCHAR(500) | no |  |
| `authors` | VARCHAR(500) | yes |  |
| `publisher` | VARCHAR(200) | yes |  |
| `year` | INTEGER | yes |  |
| `url` | VARCHAR(500) | yes |  |
| `doi` | VARCHAR(120) | yes |  |
| `source_type` | VARCHAR(30) | no |  |
| `evidence_quality` | VARCHAR(10) | no |  |
| `summary` | TEXT | yes |  |
| `verified` | BOOLEAN | no |  |
| `verified_by` | VARCHAR(36) | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `scoring_methodologies`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `version` | VARCHAR(20) | no | unique, indexed |
| `name` | VARCHAR(120) | no |  |
| `config` | JSON | no |  |
| `is_active` | BOOLEAN | no | indexed |
| `notes` | TEXT | yes |  |
| `created_by` | VARCHAR(36) | yes |  |
| `published_at` | DATETIME | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `scoring_rules`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `methodology_id` | VARCHAR(36) | no | FK → `scoring_methodologies.id` (CASCADE), indexed |
| `component` | VARCHAR(40) | no |  |
| `code` | VARCHAR(80) | no |  |
| `params` | JSON | no |  |
| `description` | TEXT | yes |  |
| `id` | VARCHAR(36) | no | PK |

### `shopping_list_items`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `list_id` | VARCHAR(36) | no | FK → `shopping_lists.id` (CASCADE), indexed |
| `product_id` | VARCHAR(36) | yes | FK → `products.id` (SET NULL) |
| `text` | VARCHAR(200) | no |  |
| `quantity` | VARCHAR(40) | yes |  |
| `checked` | BOOLEAN | no |  |
| `added_by` | VARCHAR(36) | yes |  |
| `created_at` | DATETIME | no |  |
| `id` | VARCHAR(36) | no | PK |

### `shopping_lists`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `owner_user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `name` | VARCHAR(120) | no |  |
| `shared_with_family` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `subscription_entitlements`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `tier` | VARCHAR(20) | no | indexed |
| `feature` | VARCHAR(40) | no |  |
| `monthly_limit` | INTEGER | yes |  |
| `id` | VARCHAR(36) | no | PK |

Unique: (tier, feature)

### `subscriptions`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `tier` | VARCHAR(20) | no |  |
| `status` | VARCHAR(20) | no | indexed |
| `interval` | VARCHAR(10) | no |  |
| `provider` | VARCHAR(20) | no |  |
| `provider_ref` | VARCHAR(120) | yes | indexed |
| `current_period_end` | DATETIME | yes |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `user_profiles`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), unique |
| `active_family_profile_id` | VARCHAR(36) | yes |  |
| `units` | VARCHAR(10) | no |  |
| `theme` | VARCHAR(10) | no |  |
| `notification_prefs` | JSON | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

### `user_reviews`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `user_id` | VARCHAR(36) | no | FK → `users.id` (CASCADE), indexed |
| `product_id` | VARCHAR(36) | no | FK → `products.id` (CASCADE), indexed |
| `rating` | INTEGER | no |  |
| `title` | VARCHAR(120) | yes |  |
| `body` | TEXT | yes |  |
| `status` | VARCHAR(20) | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |

Unique: (user_id, product_id)

### `users`

| Column | Type | Null | Key / constraint |
|---|---|---|---|
| `email` | VARCHAR(320) | no | unique, indexed |
| `password_hash` | VARCHAR(200) | yes |  |
| `firebase_uid` | VARCHAR(128) | yes | unique, indexed |
| `display_name` | VARCHAR(120) | yes |  |
| `role` | VARCHAR(20) | no | indexed |
| `is_active` | BOOLEAN | no |  |
| `country` | VARCHAR(2) | yes |  |
| `locale` | VARCHAR(10) | no |  |
| `currency` | VARCHAR(3) | no |  |
| `last_login_at` | DATETIME | yes |  |
| `consent_terms_at` | DATETIME | yes |  |
| `consent_health_data_at` | DATETIME | yes |  |
| `consent_ai_history` | BOOLEAN | no |  |
| `marketing_opt_in` | BOOLEAN | no |  |
| `id` | VARCHAR(36) | no | PK |
| `created_at` | DATETIME | no |  |
| `updated_at` | DATETIME | no |  |


<!-- END GENERATED -->
