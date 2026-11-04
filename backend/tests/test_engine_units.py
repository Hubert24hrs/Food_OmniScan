"""Unit tests: barcode validation, parsing, matching, allergens, nutrition label OCR, scoring, compatibility."""

import pytest

from app.services.allergens import detect_allergens
from app.services.barcode import InvalidBarcode, gtin_check_digit, parse_barcode, upce_to_upca
from app.services.compatibility import ProductFacts, ProfileSpec, evaluate
from app.services.ingredient_parser import parse_ingredients
from app.services.knowledge import KnowledgeBase
from app.services.nutrition import NutritionInput, fop_level, label_to_per100, parse_nutrition_label, percent_dv
from app.services.scoring.default_methodology import DEFAULT_METHODOLOGY as M
from app.services.scoring.engine import ScoringInputs, compute_score

KB = KnowledgeBase.from_seed()


def analyse(text, n=None, nova=None, bev=False, tags=None, traces=None):
    st = parse_ingredients(text) if text else None
    ms = [KB.match(p) for p in st.flat()] if st else []
    al = detect_allergens(st, ms, tags, traces)
    inp = ScoringInputs(nutrition=n, statement=st, matches=ms, nova_group=nova, nova_source="off" if nova else None,
                        allergens=al, is_beverage=bev)
    return st, ms, al, compute_score(inp, M)


# ------------------------------------------------------------------ barcodes
@pytest.mark.parametrize("code,fmt", [("3017620422003", "EAN13"), ("049000000443", "UPCA"), ("96385074", "EAN8"),
                                      ("0049000000443", "EAN13"), ("10049000000440", "GTIN14")])
def test_valid_barcodes(code, fmt):
    assert parse_barcode(code).format == fmt


def test_upc_a_and_ean13_forms_share_gtin14():
    assert parse_barcode("049000000443").gtin14 == parse_barcode("0049000000443").gtin14


def test_upce_expansion():
    assert upce_to_upca("04252614") == "042100005264"
    assert parse_barcode("04252614").format == "UPCE"


@pytest.mark.parametrize("bad", ["3017620422004", "12345", "abc4567890123", "", "049000000444"])
def test_invalid_barcodes(bad):
    with pytest.raises(InvalidBarcode):
        parse_barcode(bad)


def test_check_digit():
    assert gtin_check_digit("301762042200") == 3


# ------------------------------------------------------------------ parsing & matching
def test_nested_parentheses_percent_and_enumbers():
    st = parse_ingredients("Ingredients: Sugar, cocoa butter 12%, emulsifier (E322, E476), milk chocolate "
                           "(sugar, whole milk powder, cocoa mass), vanillin.")
    names = [p.normalized for p in st.ingredients]
    assert names[:2] == ["sugar", "cocoa butter"]
    assert st.ingredients[1].percent == 12.0
    emul = st.ingredients[2]
    assert emul.e_numbers == ["E322", "E476"] or [c.e_numbers for c in emul.children] == [["E322"], ["E476"]]
    assert [c.normalized for c in st.ingredients[3].children] == ["sugar", "whole milk powder", "cocoa mass"]


def test_ins_numbers_in_class_group():
    st = parse_ingredients("Salt, flavour enhancer (621, 627, 631), colour (E150d)")
    matches = [KB.match(p) for p in st.flat()]
    slugs = [m.entry.slug for m in matches if m.entry]
    assert {"msg", "disodium-guanylate", "disodium-inosinate", "caramel-colour-iv", "salt"} <= set(slugs)


def test_precautionary_statement_separated():
    st = parse_ingredients("Oats, sugar. May contain traces of peanuts and sesame.")
    assert [p.normalized for p in st.ingredients] == ["oats", "sugar"]
    assert "peanuts" in st.precautionary_text


def test_us_label_names_match():
    st = parse_ingredients("Sugar, Red 40, Yellow 5, canola oil, high fructose corn syrup")
    slugs = [KB.match(p).entry.slug for p in st.flat()]
    assert slugs == ["sugar", "allura-red", "tartrazine", "rapeseed-oil", "hfcs"]
    assert KB.by_slug["allura-red"].display_name("US").startswith("Red 40")


def test_longest_match_wins_and_class_heading_not_ingredient():
    st = parse_ingredients("Cocoa butter, soy lecithin, emulsifiers: mono- and diglycerides of fatty acids")
    ms = [KB.match(p) for p in st.flat()]
    assert ms[0].entry.slug == "cocoa-butter"
    assert ms[1].entry.slug == "soy-lecithin"
    assert ms[2].method == "class" and ms[2].entry is None
    assert ms[3].entry.slug == "mono-diglycerides"


def test_unknown_ingredient_not_guessed():
    st = parse_ingredients("Zorbleflux extract")
    assert KB.match(st.ingredients[0]).entry is None


def test_ocr_garbage_low_confidence():
    assert parse_ingredients("#@! 1 2 , ;; ~~ 3").confidence < 0.6


# ------------------------------------------------------------------ allergens
def test_allergen_contains_and_may_contain():
    st, ms, al, _ = analyse("Wheat flour, sugar, whey powder, soy lecithin. May contain peanuts.")
    assert al["gluten"].status == "contains"
    assert al["wheat"].status == "contains"
    assert al["milk"].status == "contains"
    assert al["soybeans"].status == "contains"
    assert al["peanuts"].status == "may_contain"
    assert al["sesame"].status == "not_detected"


def test_allergen_false_friends():
    _, _, al, _ = analyse("Coconut milk, cocoa butter, buckwheat, nutmeg, peanut butter")
    assert al["milk"].status == "not_detected"
    assert al["gluten"].status == "not_detected"
    assert al["nuts"].status == "not_detected"
    assert al["peanuts"].status == "contains"


def test_refined_oil_is_may_contain_not_contains():
    _, _, al, _ = analyse("Soybean oil, salt")
    assert al["soybeans"].status == "may_contain"
    assert any(e["source"] == "refined_oil" for e in al["soybeans"].evidence)


def test_gluten_free_claim_not_flagged():
    _, _, al, _ = analyse("Rice flour, gluten-free oats? no: rice, salt")
    assert al["wheat"].status == "not_detected"


def test_unknown_when_no_data():
    _, _, al, _ = analyse(None)
    assert all(f.status == "unknown" for f in al.values())


def test_regional_crayfish_is_crustacean():
    _, _, al, _ = analyse("Pepper, ground crayfish, salt")
    assert al["crustaceans"].status == "contains"


def test_off_tags_used():
    _, _, al, _ = analyse(None, tags=["en:milk"], traces=["en:nuts"])
    assert al["milk"].status == "contains" and al["nuts"].status == "may_contain"


# ------------------------------------------------------------------ nutrition
def test_percent_dv_and_fop():
    assert percent_dv("sodium", 0.46) == 20.0
    assert percent_dv("saturated_fat", 1) == 5.0
    assert fop_level(5) == "low" and fop_level(12) == "medium" and fop_level(20) == "high"


def test_salt_sodium_derivation():
    n = NutritionInput(salt=2.5)
    assert n.sodium == 1.0


US_PANEL = """Nutrition Facts
Serving size 1 cup (240mL)
Calories 150
Total Fat 89 10%
Saturated Fat 5g 25%
Sodium 120mg 5%
Total Carbohydrate 12g 4%
Total Sugars 12g
Includes 0g Added Sugars 0%
Protein 8g"""


def test_us_nutrition_facts_panel_with_ocr_error():
    r = parse_nutrition_label(US_PANEL)
    assert r["basis"] == "serving" and r["serving_size_g"] == 240
    assert r["values"]["fat"] == 8.0  # corrected '89' -> 8 g via %DV
    assert r["values"]["sodium"] == 0.12
    assert r["values"]["added_sugars"] == 0.0
    assert r["values"]["sugars"] == 12.0
    per100 = label_to_per100(r, is_beverage=True)
    assert round(per100.protein, 2) == round(8 / 2.4, 2)


def test_eu_table_per_100g():
    r = parse_nutrition_label("Per 100g\nEnergy 2252kJ / 539kcal\nFat 30.9g\nof which saturates 10.6g\n"
                              "Carbohydrate 57.5g\nof which sugars 56.3g\nProtein 6.3g\nSalt 0.107g")
    assert r["basis"] == "100g"
    assert r["values"]["energy_kcal"] == 539
    assert r["values"]["saturated_fat"] == 10.6 and r["values"]["sugars"] == 56.3


# ------------------------------------------------------------------ scoring
COLA_N = dict(energy_kcal=42, fat=0, saturated_fat=0, carbohydrates=10.6, sugars=10.6, protein=0, salt=0)


def test_score_is_deterministic_and_versioned():
    t = "Carbonated water, sugar, caramel color, phosphoric acid, natural flavors, caffeine"
    a = analyse(t, NutritionInput(**COLA_N, is_beverage=True), 4, True)[3]
    b = analyse(t, NutritionInput(**COLA_N, is_beverage=True), 4, True)[3]
    assert a["overall"] == b["overall"] and a["inputs_hash"] == b["inputs_hash"]
    assert a["methodology_version"] == M["version"]


def test_sugary_soda_scores_poor_with_explained_deductions():
    sc = analyse("Carbonated water, sugar, caramel color, phosphoric acid, natural flavors, caffeine",
                 NutritionInput(**COLA_N, is_beverage=True), 4, True)[3]
    assert sc["grade"] == "poor" and sc["color"] == "red"
    nut = sc["components"]["nutrition"]
    assert nut["basis"].startswith("per 360 ml")
    sugar = next(a for a in nut["adjustments"] if a["code"] == "nutrition.added_sugars")
    assert sugar["points"] < 0 and "Daily Value" in sugar["reason"] and "fda_21cfr101_9" in sugar["source_keys"]
    assert any(c["code"] == "cap.nutrition" for c in sc["caps_applied"])


def test_whole_food_scores_excellent():
    sc = analyse("Wholegrain oats", NutritionInput(energy_kcal=375, fat=8, saturated_fat=1.5, carbohydrates=60,
                                                   sugars=1, fiber=9, protein=11, salt=0.01), 1)[3]
    assert sc["grade"] == "excellent" and sc["confidence"] == "high"


def test_natural_sugar_not_penalised_as_added():
    sc = analyse("Whole milk", NutritionInput(energy_kcal=64, fat=3.6, saturated_fat=2.3, carbohydrates=4.7,
                                              sugars=4.7, protein=3.3, salt=0.1, is_beverage=True), 1, True)[3]
    assert sc["components"]["nutrition"]["sugar_basis"] == "no_added_sugar_in_ingredients"
    assert not any(a["code"] == "nutrition.added_sugars" for a in sc["components"]["nutrition"]["adjustments"])


def test_insufficient_data_without_nutrition():
    sc = analyse("Sugar, water, salt")[3]
    assert sc["overall"] is None and sc["insufficient_data"] and sc["grade"] == "insufficient_data"
    assert sc["components"]["ingredients"]["score"] is not None  # partial info still shown


def test_banned_additive_caps_score_and_explains():
    sc = analyse("Sugar, water, titanium dioxide", NutritionInput(energy_kcal=50, fat=0, saturated_fat=0,
                                                                  carbohydrates=1, sugars=1, protein=0, salt=0), 4)[3]
    assert sc["overall"] <= 49
    adj = [a for a in sc["components"]["ingredients"]["adjustments"] if "titanium" in a["code"]]
    assert adj and "efsa_e171_2021" in adj[0]["source_keys"]


def test_seed_oils_flagged_but_not_penalised():
    sc = analyse("Potatoes, sunflower oil, salt", NutritionInput(energy_kcal=530, fat=33, saturated_fat=3,
                                                                carbohydrates=52, sugars=0.5, protein=6, salt=1.2), 3)[3]
    assert sc["highlights"]["seed_oils"][0]["slug"] == "sunflower-oil"
    assert not any("sunflower" in a["code"] for a in sc["components"]["ingredients"]["adjustments"])


def test_trans_fat_partial_hydrogenation_cap():
    sc = analyse("Flour, sugar, partially hydrogenated soybean oil",
                 NutritionInput(energy_kcal=200, fat=5, saturated_fat=1, trans_fat=1.0, carbohydrates=30, sugars=3,
                                protein=3, salt=0.1), 4)[3]
    assert sc["overall"] <= 34
    assert any(a["code"] == "nutrition.trans_fat" for a in sc["components"]["nutrition"]["adjustments"])


def test_recall_forces_zero():
    st = parse_ingredients("Oats")
    ms = [KB.match(p) for p in st.flat()]
    inp = ScoringInputs(nutrition=NutritionInput(energy_kcal=375, fat=8, saturated_fat=1.5, carbohydrates=60,
                                                 sugars=1, protein=11, salt=0), statement=st, matches=ms,
                        allergens=detect_allergens(st, ms),
                        active_recalls=[{"id": "r1", "title": "Listeria", "authority": "FDA"}])
    sc = compute_score(inp, M)
    assert sc["overall"] == 0 and sc["components"]["product_concerns"]["assessed"]


def test_no_lab_data_is_not_assessed_not_safe():
    sc = analyse("Rice", NutritionInput(energy_kcal=360, fat=1, saturated_fat=0.2, carbohydrates=80, sugars=0,
                                        protein=7, salt=0), 1)[3]
    pc = sc["components"]["product_concerns"]
    assert not pc["assessed"] and "unknown" in pc["notes"][0]


# ------------------------------------------------------------------ compatibility
def facts(text, n=None, labels=None):
    st = parse_ingredients(text) if text else None
    ms = [KB.match(p) for p in st.flat()] if st else []
    return ProductFacts(matches=ms, allergens=detect_allergens(st, ms), nutrition=n, has_ingredients=bool(st),
                        labels_tags=labels or [], ingredient_names=[m.parsed.text for m in ms])


def test_allergen_contains_is_critical_red():
    r = evaluate(ProfileSpec(None, "Kid", allergens=[{"code": "peanuts", "severity": "anaphylaxis"}]),
                 facts("Sugar, groundnuts, salt"))
    assert r["verdict"] == "red" and r["critical_allergen_alerts"][0]["allergen"] == "peanuts"


def test_may_contain_with_severe_allergy_is_red():
    r = evaluate(ProfileSpec(None, "A", allergens=[{"code": "nuts", "severity": "severe", "avoid_traces": True}]),
                 facts("Oats. May contain almonds."))
    assert r["verdict"] == "red"


def test_not_detected_is_never_called_safe():
    r = evaluate(ProfileSpec(None, "A", allergens=[{"code": "milk", "severity": "severe"}]), facts("Oats, salt"))
    assert r["verdict"] == "green"
    assert "isn't a guarantee" in r["reasons"][0]["message"]


def test_no_ingredients_yields_yellow():
    r = evaluate(ProfileSpec(None, "A", allergens=[{"code": "milk"}], diets=["vegan"]), facts(None))
    assert r["verdict"] == "yellow"


def test_vegan_and_vegetarian():
    assert evaluate(ProfileSpec(None, "V", diets=["vegan"]), facts("Sugar, honey"))["verdict"] == "red"
    assert evaluate(ProfileSpec(None, "V", diets=["vegetarian"]), facts("Sugar, gelatine"))["verdict"] == "red"
    assert evaluate(ProfileSpec(None, "V", diets=["vegan"]), facts("Sugar, natural flavouring"))["verdict"] == "yellow"


def test_halal_screen():
    assert evaluate(ProfileSpec(None, "H", diets=["halal"]), facts("Pork, salt"))["verdict"] == "red"
    r = evaluate(ProfileSpec(None, "H", diets=["halal"]), facts("Rice, salt"))
    assert r["verdict"] == "yellow" and "certification" in r["reasons"][0]["message"]


def test_keto_and_low_sodium():
    n = NutritionInput(energy_kcal=400, fat=10, saturated_fat=2, carbohydrates=70, fiber=5, sugars=10, protein=8,
                       sodium=0.6)
    r = evaluate(ProfileSpec(None, "K", diets=["keto", "low_sodium"]), facts("Wheat flour, sugar", n))
    rules = {x["rule"]: x["severity"] for x in r["reasons"]}
    assert rules["diet.keto"] == "red" and rules["diet.low_sodium"] == "red"


def test_custom_avoid_list_names_ingredient():
    r = evaluate(ProfileSpec(None, "A", avoid_terms=["palm oil", "e150d"]), facts("Sugar, palm oil, colour (E150d)"))
    reds = [x for x in r["reasons"] if x["severity"] == "red"]
    assert len(reds) == 2 and any("palm oil" in x["message"] for x in reds)


def test_implausible_zero_added_sugar_is_not_trusted():
    n = NutritionInput(energy_kcal=378, fat=4, saturated_fat=0, carbohydrates=80, sugars=32.4, added_sugars=0,
                       fiber=7, protein=8, salt=1.4)
    sc = analyse("Whole grain oats, sugar, corn starch, honey, brown sugar syrup, salt", n, 4)[3]
    nut = sc["components"]["nutrition"]
    assert nut["sugar_basis"] == "added_sugars_conflict"
    assert any(a["code"] == "nutrition.added_sugars" for a in nut["adjustments"])
