# Scoring Methodology

**Current version:** `2026.11-us.1` (Food omniScan Score, US FDA basis)
**Source of truth:** [`backend/app/services/scoring/default_methodology.py`](backend/app/services/scoring/default_methodology.py) (config) and [`engine.py`](backend/app/services/scoring/engine.py) (logic)

The score summarises general nutritional quality and ingredient quality on a 0–100 scale.
It isn't medical advice and it isn't personal. Personal dietary compatibility (allergies,
diets, avoid lists) is computed separately and is never averaged into the score.

## 1. Principles

1. **US standards by default.** Nutrients are judged against the FDA Daily Values (21 CFR 101.9)
   using FDA's own "5/20" rule: ≤5% DV is low and ≥20% DV is high. These are the same thresholds
   as FDA's proposed front-of-package "Nutrition Info box".
2. **Explain everything.** Every point gained or lost is an *adjustment* with a code, a
   plain-language reason, an evidence type and source keys. The API returns all of them.
3. **Reproducible.** Same inputs + same methodology version give the same result. Each stored
   score has an `inputs_hash` (SHA-256 of the normalised inputs and the version).
4. **No invented data.** Missing values are never treated as zero. Missing nutrition gives
   `insufficient_data`, and a component without data is marked "not assessed".
5. **Not every additive is equal.** Penalties depend on regulatory status and evidence quality,
   not on "sounds chemical". Seed oils and palm oil are *flagged* for information but not
   penalised.
6. **Versioned and immutable.** Admins publish new versions; old versions are never edited.

## 2. Components and weights

| Component | Weight | What it measures |
|---|---|---|
| Nutrition | 40 | Added sugars, saturated fat, sodium, energy density, trans fat; bonuses for fiber, protein, fruit/veg/nuts |
| Ingredients & additives | 25 | Additives by regulatory status, added-sugar position, undisclosed terms, whole-food main ingredients |
| Processing | 15 | NOVA group (from Open Food Facts, or *estimated* from ingredient markers) |
| Dietary suitability | 10 | How broadly the product suits common diets (US major allergens, high-FODMAP, caffeine, alcohol). General, not personal |
| Product-specific concerns | 10 | Verified recalls and verified product lab reports. Not assessed if none are on file |

The overall score is the weighted mean of **assessed** components. When a component can't be
assessed, its weight is redistributed and confidence drops.

## 3. Nutrition (0–100)

**Reference amount.** Foods are assessed per **100 g**. Beverages are assessed per **12 fl oz
(360 ml)**, the FDA reference amount for most beverages. Per 100 ml, a soda looks mild
(10.6 g sugar). Per 12 fl oz it's ~38 g, which is 76% of the added-sugar Daily Value.

**Negative nutrients** use a linear ramp from 5% DV (no penalty) to 30% DV (full penalty):

| Nutrient | FDA DV | Max penalty |
|---|---|---|
| Added sugars | 50 g | 60 |
| Saturated fat | 20 g | 50 |
| Sodium | 2,300 mg | 50 |

**Added sugars when they aren't reported** (common outside the US):
- If the label reports added sugars, they're used directly (`label_added_sugars`).
- If the ingredient list contains **no added sugar** (no sugar, syrup, honey, dextrose…),
  added sugars = 0, so lactose in milk and fructose in fruit aren't penalised
  (`no_added_sugar_in_ingredients`).
- If the ingredients contain added sugar, total sugars stand in, with a note that this may
  overstate added sugar (`total_sugars_proxy`).

**Energy density:** foods 120→500 kcal/100 g (max −20); beverages 40→200 kcal per 12 fl oz (max −25).
**Trans fat:** >0.2 g per reference amount gives −30.

**Bonuses** (EU Regulation 1924/2006 claim thresholds, which are well defined):
- Fiber: ≥3 g/100 g +5 ("source"), ≥6 g/100 g +10 ("high")
- Protein: ≥12% of energy +4, ≥20% of energy +8
- Fruit/vegetables/legumes/nuts: 40→80% gives 0→+8 (estimate)

## 4. Ingredients & additives (0–100)

| Rule | Points |
|---|---|
| Ingredient with concern level **concern** (banned/revoked in a major jurisdiction, or a strong hazard finding: e.g. E171 titanium dioxide, Red No. 3, BVO, potassium bromate, partially hydrogenated oils, nitrites) | −25 each, max −60 |
| **caution** (mandatory warning label, IARC 2B, consistent animal evidence under study, e.g. Southampton colours, aspartame, sucralose, carrageenan, polysorbate 80) | −10 each, max −40 |
| Added sugar is the first ingredient (water ignored) | −12 |
| Added sugar in the first three ingredients | −6 |
| ≥3 different added sugars | −5 |
| Undisclosed terms ("flavorings", "spices", unspecified "vegetable oil") | −2 each, max −6 |
| Whole-food **beneficial** ingredient among the first three (whole grains, olive oil…) | +3 each, max +9 |

Concern levels live in the ingredient knowledge base. Each one cites its sources, and seeded
entries start as `pending` until an editor verifies them in the admin console.

## 5. Processing

NOVA 1 → 100, NOVA 2 → 85, NOVA 3 → 60, NOVA 4 → 10. If Open Food Facts has no NOVA group,
it's estimated from ultra-processing markers (Monteiro et al., 2019) and labelled *estimated*.
That lowers confidence.

## 6. Dietary suitability (general)

Starts at 100. Each US major allergen: −6 if contained, −2 if "may contain" (max −30).
High-FODMAP ingredients −2 each (max −6), caffeine −5, alcohol −10.

## 7. Product-specific concerns

- **Verified active recall:** component = 0 and the overall score is capped at 0.
- **Verified lab report above threshold:** −40 per exceedance. The finding shows jurisdiction,
  value, unit, threshold, lab and test date.
- **Nothing on file:** *not assessed*. The UI says that no product-specific lab testing is on
  file, and that this means unknown, not safe or unsafe. General research about an ingredient
  is never used to imply that a specific product is contaminated.

## 8. Ceilings (documented caps)

| Cap | Rule |
|---|---|
| Nutrition margin | If nutrition < 50, overall ≤ nutrition + 10. Poor nutrition can't be rescued |
| Ultra-processed | NOVA 4, so overall ≤ 64 (can't be "Excellent") |
| Concern ingredient | Any *concern* ingredient, so overall ≤ 49 |
| Partially hydrogenated oil | overall ≤ 34 |
| Active recall | overall = 0 |

## 9. Grades, colours and confidence

| Score | Grade | Colour |
|---|---|---|
| 75–100 | Excellent | Green |
| 50–74 | Good | Green |
| 35–49 | Mediocre | Amber |
| 0–34 | Poor | Red |
| — | Not enough data | Grey |

**Insufficient data:** no nutrition facts (nutrition is required, because "sugar, water, salt" would
otherwise look good), or less than 55% of core weight assessable.

**Confidence:** *high* = all core components assessed, NOVA not estimated, ≥85% of ingredients
recognised; *medium* = ≥80% coverage and ≥60% recognised; otherwise *low*.

## 10. Calibration (reference cases in `tests/test_engine_units.py`)

| Case | Result |
|---|---|
| Sugar-sweetened cola | ~33, Poor (sugar 76% DV per 12 fl oz) |
| Diet cola | 64, Good (capped by ultra-processing; two sweeteners flagged *caution*) |
| Chocolate-hazelnut spread | ~10, Poor |
| Rolled oats | ~96, Excellent |
| Whole milk | ~40, Mediocre (saturated fat per 12 fl oz; lactose not penalised) |
| Snack cake with partially hydrogenated oil | ~10, Poor |
| Ingredients only, no nutrition | Not enough data |

Known limitation: cheese and similar foods score low because saturated fat and sodium per 100 g
are high, and there's no category-specific adjustment (unlike Nutri-Score 2023). Any category
rules must ship as a new version.

## 11. Changing the methodology

`POST /api/v1/admin/methodologies` (admin only) with a new `version` (e.g. `2026.12-us.2`), the full
config and release notes. The server validates the weights (must cover all five components and
sum to 100), dry-runs the engine, stores flattened `scoring_rules`, and writes an audit log
entry. Activate with `POST /admin/methodologies/{version}/activate`. Stored scores keep their
version. New requests compute and store scores under the active version.

## 12. Commercial independence

No payment, sponsorship or affiliate relationship changes the scoring code path or config.
Sponsored or affiliate placements must be labelled in the UI and are kept out of the alternatives ranking.
