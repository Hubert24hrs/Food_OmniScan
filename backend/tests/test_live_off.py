"""Opt-in live tests against the real Open Food Facts API: `pytest -m live`.

Kept to a couple of requests to respect OFF's rate limits.
"""

import pytest

from app.services.ingredient_parser import parse_ingredients
from app.services.knowledge import KnowledgeBase
from app.services.providers import openfoodfacts as off


@pytest.mark.live
def test_real_barcode_lookup_and_parse():
    # Nutella 400 g. A long-standing, well-populated OFF record.
    p = off.get_product("3017620422003")
    assert p is not None and p.name
    assert p.nutrition is not None and p.nutrition.sugars and p.nutrition.sugars > 40
    assert p.ingredients_text
    kb = KnowledgeBase.from_seed()
    st = parse_ingredients(p.ingredients_text)
    matched = [kb.match(x) for x in st.flat()]
    assert sum(1 for m in matched if m.entry) / len(matched) > 0.6


@pytest.mark.live
def test_real_unknown_barcode():
    assert off.get_product("0000000000017") is None
