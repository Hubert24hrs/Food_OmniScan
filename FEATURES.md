# Feature coverage

How Food omniScan covers the 170 capabilities in the combined competitor feature list, as of 2026-11-04.

**Status:** **Done** means it works end to end and is tested. **Partial** means it works with a stated limit. **Not yet** means it isn't built.
**Plan:** Free, Plus ($3.99), Premium ($7.99), Family ($11.99). Plans are enforced on the server (`backend/app/services/entitlements.py`), and admins can change limits per plan without a release.

> **Never paywalled:** scanning, the health score and its full explanation, allergen warnings, diet compatibility, recalls, verified lab results, and food-safety research. Paid plans add convenience, depth and AI. They never add safety information.

**Platforms:** W = web app, M = mobile app (Android/iOS), A = API only.

## Totals

| Status | Count |
|---|---|
| Done | 153 |
| Partial | 15 |
| Not yet | 2 |

Most gaps are limited by data rather than code: retailer price feeds, West African food-composition data, and a NAFDAC API.

---

## 1. Food scanning and recognition

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 1 | Barcode scanning | Done | W (ZXing), M (ML Kit). GTIN check-digit validation | Free |
| 2 | Ingredient label OCR | Done | W (Tesseract), M (ML Kit) on device; optional AI reading | Free; AI metered |
| 3 | Nutrition label scanning | Done | US Nutrition Facts and EU tables parsed, with OCR digit correction | Free |
| 4 | AI food recognition | Done | Gemini vision: packaged (front of pack) and unpackaged (meal) | AI photo credits |
| 5 | Meal photo scanning | Done | W, M: dishes, portions and estimated nutrients, reviewed then logged as estimates | AI photo credits |
| 6 | Product image recognition | Partial | W: Discover camera button finds the product by name or brand. Not on mobile yet | AI photo credits |
| 7 | Multi-language label recognition | Partial | AI reading returns the original text plus an English translation, and scores the translation. On-device OCR is Latin-script only | AI photo credits |
| 8 | Manual product search | Done | Name, brand, category or barcode; voice search on web | Free |
| 9 | Unknown product submission | Done | W submission flow with photos; moderator review | Free |
| 10 | Scan history | Done | W, M | Free |
| 11 | Offline scanning | Done | M: queued scans sync on reconnect; cached products | Free |
| 12 | Scan result sharing | Done | Public report link with no personal data; shareable comparisons | Free |

## 2. Food health scoring and product evaluation

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 13 | Overall score 0–100 | Done | Versioned, deterministic engine (no AI) | Free |
| 14 | Colour-coded ratings | Done | | Free |
| 15 | Nutrition scoring | Done | FDA Daily Values; 5/20 rule; beverages per 12 fl oz | Free |
| 16 | Ingredient quality | Done | | Free |
| 17 | Additive assessment | Done | E-numbers, classes, concern levels | Free |
| 18 | Processing (NOVA) | Done | From Open Food Facts, or estimated and labelled as such | Free |
| 19 | Sugar assessment | Done | Added vs total sugars, hidden sugar names, sweeteners, data-conflict flag | Free |
| 20 | Oil assessment | Done | Seed oils and palm oil flagged; partially hydrogenated oils flagged | Free |
| 21 | Artificial ingredient detection | Done | Colours, sweeteners, flavourings | Free |
| 22 | Product verdict | Done | | Free |
| 23 | Detailed score breakdown | Done | Every deduction, cap and source shown | Free |
| 24 | Category rankings | Done | `/rankings`; products without enough data aren't ranked | Top 5 free; full list Plus |
| 25 | Product improvement insights | Done | Alternatives explain what's better and what isn't | Free (monthly limit) |

The score is separate from personal compatibility. The presence of an ingredient never makes a product "dangerous" on its own.

## 3. Ingredient and additive intelligence

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 26–36 | Identification, plain language, purpose, additive database, E-numbers, preservatives, colours, sweeteners, emulsifiers, flavour enhancers, hidden names | Done | 212-ingredient knowledge base with synonyms, US names, E/INS numbers, class headings | Free |
| 37 | Concern classification | Done | Evidence level, regulatory status, sources | Free |
| 38 | Ingredient alternatives | Partial | Recipe substitutions for allergies and diets (e.g. crayfish → iru). No per-additive swap list | Free |
| 39 | Ingredient search | Done | Encyclopedia | Free |
| 40 | Ingredient watchlist | Done | Per-profile avoid list in compatibility (free); notifications when scanned (Plus) | Free / Plus |

## 4. Contaminants, chemicals and food safety

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 41–44 | Heavy metals, microplastics, pesticides, glyphosate (plus aflatoxins) | Done | `/safety` with category-level evidence and sources | Free |
| 45 | Contamination reports | Done | Shown only from verified, product-specific lab reports | Free |
| 46 | Laboratory test results | Done | Admin upload and verify; shown on the product page | Free |
| 47 | Recall alerts | Partial | Admin publishes recalls and people who scanned the product are notified. No automatic FDA/FSA/NAFDAC feed import yet | Free |
| 48 | Regulatory information | Done | Regulatory notes per ingredient, cited | Free |
| 49 | Contamination history | Partial | Lab reports keep date and batch. No dedicated timeline view | Free |
| 50 | Evidence transparency | Done | Label data / regulatory / research / estimate tags | Free |
| 51 | Risk explanations | Done | Hazard vs exposure vs risk explainer and article | Free |
| 52 | Batch identification | Partial | Lab reports have a batch field; recalls don't yet | Free |

A study about a food category is never presented as a result for a specific brand.

## 5. Nutrition intelligence and tracking

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 53, 54 | Calories, macros | Done | W, M diary | Free |
| 55 | Micronutrients | Done | 18 vitamins and minerals with FDA DVs, only from label data | Plus |
| 56 | Food diary | Done | | Free |
| 57 | Serving-size adjustment | Done | Log by servings or grams | Free |
| 58 | Daily dashboard | Done | Totals vs targets, water | Free |
| 59 | Nutritional targets | Done | Defaults are FDA DVs; user-editable | Free |
| 60 | Water tracking | Done | W, M | Free |
| 61 | Meal history | Done | | Free |
| 62 | Nutrition reports | Done | Weekly and monthly; Monday summary notification | Plus |
| 63 | Deficiency insights | Done | "Below your target on N of M days", never a diagnosis | Premium |
| 64 | Weight and fitness goals | Partial | Weight log, goal weight and calorie targets. No activity or exercise tracking | Free |

## 6. Personalised diets and allergen protection

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 65–70, 72–77 | Profiles, allergies, intolerances, diets, gluten-free, dairy-free, custom exclusions, compatibility, allergen warnings, contains / may contain, cross-contact, family profiles | Done | US Big 9 + EU 14; severities incl. intolerance; 14 diets | Free (1 profile); more profiles on paid plans |
| 71 | Low-FODMAP | Done | Screening using FODMAP data in the knowledge base | Free |
| 78 | Personalised recommendations | Done | Better-scoring products in the categories you buy, filtered by your profile | Plus |

## 7. Alternatives and comparisons

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 79–84, 86–88 | Alternatives, comparison (nutrition, ingredients, additives, compatibility), best in category, explanations, ranking | Done | Alternatives prefer products sold in your country | Free with monthly limits; more on paid plans |
| 85 | Price comparison | Partial | Crowd-reported shelf prices per store. No retailer price feeds | Plus |

## 8. AI food and nutrition assistant

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 89–97 | Assistant, product explanations, ingredient and nutrition questions, substitutions, personal guidance, meal suggestions, label interpretation, food education | Done | W, M; answers only from our data, with sources | AI question credits |
| 98 | Context-aware conversations | Partial | Uses the active profile and the current chat. Chats aren't stored, by design (privacy) | AI question credits |
| — | Answers in Pidgin, Yoruba, Igbo, Hausa, French, Spanish | Done | | Plus |

## 9. Meal planning and recipes

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 99–102 | Meal recognition, portions, calories, macros | Done | Photo estimates, always labelled as estimates | AI photo credits |
| 103 | Recipe discovery | Done | 12 seeded recipes (8 Nigerian); admins add more | Free |
| 104 | AI recipe generation | Done | Follows allergies, avoided ingredients and diets | Plus+ (metered) |
| 105, 106 | Weekly and daily planner | Done | W, M | Plus (4 plans); unlimited Premium |
| 107 | Recipe nutrition | Done | AI estimate on request, labelled; no invented values | AI recipe credits |
| 108 | Ingredient substitutions | Done | For allergies, diets and low sodium | Free |
| 109 | Recipe → shopping list | Done | Scales to servings; no duplicates | Free |
| 110 | Plan personalisation | Done | Allergies, diets, cuisine, calories, weekly budget | Premium (AI plans) |

## 10. Shopping, pantry and grocery management

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 111 | Shopping lists | Done | | Free (2), more on paid plans |
| 112 | Lists from plans and recipes | Done | | Free / Plus |
| 113 | Healthier shopping suggestions | Done | Alternatives | Free (monthly limit) |
| 114 | Favourites | Done | Saved and trusted lists | Free |
| 115–117 | Pantry, expiry dates, reminders | Done | Reminders run in the daily job | Plus |
| 118 | Household sharing | Done | Shared pantry, lists and budget; invite by email. Managed on web | Family (members on any plan) |
| 119, 120 | Budget, shopping history | Done | Per person or household; multi-currency incl. ₦ | Plus |
| 121 | Product availability | Partial | "Seen at" stores from user price reports | Free (stores), Plus (prices) |
| 122 | Grocery price comparison across retailers | Not yet | Needs retailer partnerships or data feeds | — |

## 11. Food database, community and research

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 123–125 | Product, ingredient and additive databases | Done | Open Food Facts + USDA, merged with field-level provenance | Free |
| 126–128 | Research library, citations, regulatory database | Done | 40 sources (pending editorial verification) | Free |
| 129, 130 | Submissions, corrections | Done | Moderated | Free |
| 131 | Community reviews | Done | W product page; reviews don't affect scores | Free |
| 132 | Verified information | Done | Verified badges on products and sources | Free |
| 133 | Brand and manufacturer | Done | Shown when known; manufacturer data is sparse | Free |
| 134 | Update history | Done | From the audit log; scoring methodology is versioned | Free |

## 12. African and Nigerian food intelligence

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 135, 136 | African / Nigerian packaged-food and barcode databases | Partial | Open Food Facts Nigeria coverage plus community submissions with NAFDAC numbers. No bulk local dataset imported | Free |
| 137 | Nigerian meal recognition | Done | Meal-photo prompt covers jollof, egusi, moi moi, akara, eba and others | AI photo credits |
| 138 | African nutrition database | Not yet | FAO/INFOODS West Africa table is cited but not imported, so we show estimates rather than invented values | — |
| 139 | Local ingredient recognition | Partial | Yoruba/Igbo/Hausa names for 19 staples feed ingredient matching (pending editorial review) | Free |
| 140 | Local label interpretation | Done | kJ/kcal per 100 g parsing; NAFDAC article | Free |
| 141 | NAFDAC information | Partial | Number captured, format check, Greenbook link. NAFDAC has no public API to integrate | Free |
| 142 | Local alternatives | Done | Alternatives and rankings filter or prefer products sold in Nigeria | Free / Plus |
| 143 | African meal planning | Done | AI plans built from familiar Nigerian dishes | Premium |
| 144 | Regional food names | Partial | Glossary with Pidgin/Yoruba/Igbo/Hausa names; assistant answers in those languages (Plus). App interface is English only | Free / Plus |
| 145 | Naira pricing | Done | NGN for Nigerian accounts; budgets and prices in ₦; Paystack billing | — |
| 146 | Preparation analysis | Done | Per-recipe and per-dish notes (e.g. steamed moi moi vs fried akara) | Free |

## 13. Notifications, reports and engagement

| # | Feature | Status | Where | Plan |
|---|---|---|---|---|
| 147, 150 | Watchlist / ingredient alerts | Done | Once a day per product | Plus |
| 148 | Allergen alerts | Done | | Free |
| 149 | Recall notifications | Done | | Free |
| 151 | Weekly nutrition reports | Done | Monday notification | Plus |
| 152 | Personal insights | Done | | Premium |
| 153 | Saved collections | Done | | Free |
| 154 | Shareable reports | Done | | Free |
| 155 | Educational notifications | Done | Weekly tip, opt-in | Free |

Each kind of notification can be switched on or off on the profile page. The daily job (`python -m app.services.alerts`, or **Run daily jobs** in admin) must be scheduled in production.

## 14. Admin and business

| # | Feature | Status | Where |
|---|---|---|---|
| 156–160 | Dashboard, products (create/edit/hide), ingredients (create/edit), verification, versioned scoring | Done | W admin |
| 161–163 | Research, lab reports, recalls | Done | |
| 164–166 | Users and roles, subscriptions and entitlements, AI usage and cost | Done | |
| 167 | Analytics | Done | Scans per day, popular products, most-scanned missing barcodes, feature usage |
| 168, 169 | Moderation, audit logs | Done | |
| 170 | Content management | Done | Articles, recipe moderation, announcements |

## Beyond the list

- **Restaurant and menu intelligence** (from the Phase 3 roadmap) isn't built.
- **Mobile gaps:** household management and setting a monthly budget are on the web app only.
