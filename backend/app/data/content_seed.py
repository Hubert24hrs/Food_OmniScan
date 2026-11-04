"""Editorial seed content: recipes, local food glossary, food-safety topics, articles, substitutions.

Rules for this file:
- No invented numbers. Recipes carry no nutrition values; users can request an AI estimate, which is
  labelled as an estimate. Nutrient values for regional dishes belong in a food composition table
  (see the fao_wafct_2019 source), not here.
- Local-language names are included only where commonly used, and are marked for editorial review.
- Food-safety topics describe category-level evidence. They never say a specific product is contaminated.
"""


def _ing(name, quantity=None, unit=None, note=None):
    return {"name": name, "quantity": quantity, "unit": unit, "note": note}


RECIPES: list[dict] = [
    {
        "title": "Jollof rice",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Rice cooked in a tomato and pepper base, the party staple across West Africa.",
        "servings": 6,
        "time_minutes": 75,
        "tags": ["nigerian", "west-african", "rice", "one-pot", "party"],
        "diet_tags": ["dairy_free", "gluten_free"],
        "ingredients": [
            _ing("long-grain parboiled rice", 3, "cups"),
            _ing("plum tomatoes", 4, None),
            _ing("red bell peppers (tatashe)", 2, None),
            _ing("scotch bonnet pepper (ata rodo)", 1, None, "to taste"),
            _ing("onions", 2, None),
            _ing("tomato paste", 2, "tbsp"),
            _ing("vegetable oil", 0.33, "cup"),
            _ing("chicken stock", 3, "cups", "low-sodium if possible"),
            _ing("bay leaves", 2, None),
            _ing("curry powder", 1, "tsp"),
            _ing("dried thyme", 1, "tsp"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Blend the tomatoes, bell peppers, scotch bonnet and one onion until smooth.",
            "Fry the other onion, sliced, in the oil. Add the tomato paste and fry for 3-4 minutes.",
            "Add the blended base and cook until reduced and the oil rises to the top, about 20-25 minutes.",
            "Stir in the stock, bay leaves, curry, thyme and salt. Add the washed rice.",
            "Cover tightly and cook on low heat until the rice is tender, adding a little water if needed.",
        ],
        "preparation_notes": "Most of the fat comes from the frying oil, so using less oil lowers calories "
        "noticeably. Stock cubes and seasoning powders add a lot of sodium; low-sodium stock and herbs help.",
    },
    {
        "title": "Egusi soup",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "A thick soup of ground melon seeds with leafy greens, eaten with a swallow such as eba "
        "or pounded yam.",
        "servings": 6,
        "time_minutes": 60,
        "tags": ["nigerian", "soup", "swallow"],
        "diet_tags": ["dairy_free", "gluten_free"],
        "ingredients": [
            _ing("ground egusi (melon seeds)", 2, "cups"),
            _ing("palm oil", 0.33, "cup"),
            _ing("spinach or bitter leaf", 4, "cups", "washed and chopped"),
            _ing("beef or goat meat", 500, "g"),
            _ing("stockfish or dried fish", 1, "cup", "optional"),
            _ing("ground crayfish", 2, "tbsp"),
            _ing("onion", 1, None),
            _ing("scotch bonnet pepper", 1, None, "to taste"),
            _ing("seasoning cube", 1, None, "optional; high in sodium"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Boil the meat with onion and seasoning until tender. Keep the stock.",
            "Mix the ground egusi with a little water into a paste.",
            "Heat the palm oil, add the egusi paste and fry, stirring, for about 10 minutes.",
            "Add the stock, meat, fish, crayfish and pepper, and simmer for 15 minutes.",
            "Stir in the greens and cook for 5 more minutes.",
        ],
        "preparation_notes": "Egusi seeds are rich in fat and protein. Palm oil is high in saturated fat, so "
        "the amount used matters. Adding more greens increases fibre without much extra energy.",
    },
    {
        "title": "Moi moi",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Steamed bean pudding made from peeled black-eyed beans blended with peppers.",
        "servings": 8,
        "time_minutes": 90,
        "tags": ["nigerian", "beans", "steamed", "high-protein"],
        "diet_tags": ["vegetarian", "dairy_free", "gluten_free"],
        "ingredients": [
            _ing("black-eyed beans (peeled)", 3, "cups"),
            _ing("red bell peppers", 2, None),
            _ing("onion", 1, None),
            _ing("scotch bonnet pepper", 1, None),
            _ing("vegetable oil or palm oil", 0.25, "cup"),
            _ing("boiled eggs", 3, None, "optional; omit for vegan"),
            _ing("ground crayfish", 2, "tbsp", "optional; omit for vegetarian"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Soak the beans and rub off the skins.",
            "Blend the beans with the peppers and onion, adding water a little at a time, to a smooth batter.",
            "Stir in the oil and salt (and crayfish if using).",
            "Pour into greased ramekins, foil or leaves, add egg slices if using, and seal.",
            "Steam for 45-60 minutes until set.",
        ],
        "preparation_notes": "Steaming adds no frying fat, so moi moi is usually lower in fat than akara made "
        "from the same beans. Beans provide protein and fibre.",
    },
    {
        "title": "Akara (bean fritters)",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Deep-fried fritters of blended black-eyed beans, a popular breakfast with pap or bread.",
        "servings": 4,
        "time_minutes": 45,
        "tags": ["nigerian", "beans", "breakfast", "fried"],
        "diet_tags": ["vegan", "vegetarian", "dairy_free", "gluten_free"],
        "ingredients": [
            _ing("black-eyed beans (peeled)", 2, "cups"),
            _ing("onion", 1, None),
            _ing("scotch bonnet pepper", 1, None),
            _ing("salt", None, None, "to taste"),
            _ing("vegetable oil", None, None, "for deep frying"),
        ],
        "steps": [
            "Soak and peel the beans, then blend with the onion and pepper using very little water.",
            "Whisk the batter for a few minutes to make it light, and add salt.",
            "Drop spoonfuls into hot oil and fry until golden on both sides. Drain on paper.",
        ],
        "preparation_notes": "Deep frying makes the fritters absorb oil, raising fat and calories compared "
        "with steamed moi moi. Air-frying or shallow-frying lowers the oil absorbed.",
    },
    {
        "title": "Efo riro",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Yoruba-style rich vegetable stew of leafy greens in a pepper base.",
        "servings": 4,
        "time_minutes": 45,
        "tags": ["nigerian", "yoruba", "greens", "stew", "swallow"],
        "diet_tags": ["dairy_free", "gluten_free"],
        "ingredients": [
            _ing("spinach (efo tete or shoko)", 6, "cups", "chopped"),
            _ing("red bell peppers", 2, None),
            _ing("scotch bonnet pepper", 1, None),
            _ing("onion", 1, None),
            _ing("palm oil", 0.25, "cup"),
            _ing("locust beans (iru)", 1, "tbsp"),
            _ing("assorted meat or fish", 400, "g"),
            _ing("ground crayfish", 1, "tbsp"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Blend the peppers and half the onion coarsely and boil down until thick.",
            "Fry the remaining onion and the iru in palm oil, then add the pepper base and fry for 10 minutes.",
            "Add the cooked meat or fish and crayfish, then the greens. Cook for 3-5 minutes only.",
        ],
        "preparation_notes": "Short cooking keeps more of the vitamin C and folate in the greens. Iru (fermented "
        "locust beans) adds savoury flavour, which can reduce the need for seasoning cubes.",
    },
    {
        "title": "Beans and fried plantain (ewa and dodo)",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Stewed beans served with sweet fried ripe plantain.",
        "servings": 4,
        "time_minutes": 90,
        "tags": ["nigerian", "beans", "plantain", "high-fibre"],
        "diet_tags": ["vegan", "vegetarian", "dairy_free", "gluten_free"],
        "ingredients": [
            _ing("brown or black-eyed beans", 2, "cups"),
            _ing("palm oil", 3, "tbsp"),
            _ing("onion", 1, None),
            _ing("blended tomato and pepper", 1, "cup"),
            _ing("ripe plantains", 2, None),
            _ing("vegetable oil", None, None, "for frying the plantain"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Boil the beans until soft (a pressure cooker shortens this).",
            "Fry the onion in palm oil, add the tomato-pepper blend and cook down. Stir into the beans.",
            "Slice the plantain diagonally and fry until golden.",
        ],
        "preparation_notes": "Beans are a good source of fibre and plant protein. Frying the plantain adds "
        "fat; roasting it (boli) or baking it is a lower-fat option.",
    },
    {
        "title": "Fish pepper soup",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "A light, spicy broth flavoured with pepper soup spice.",
        "servings": 4,
        "time_minutes": 40,
        "tags": ["nigerian", "soup", "light", "high-protein"],
        "diet_tags": ["dairy_free", "gluten_free", "pescatarian", "low_carb"],
        "ingredients": [
            _ing("catfish or other firm fish", 700, "g", "cut into steaks"),
            _ing("pepper soup spice mix", 2, "tbsp"),
            _ing("onion", 1, None),
            _ing("scotch bonnet pepper", 1, None),
            _ing("scent leaf (efirin) or basil", 1, "handful"),
            _ing("water", 6, "cups"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Bring the water to a boil with the onion, pepper and spice mix.",
            "Add the fish and simmer gently for 15 minutes without stirring hard.",
            "Add the scent leaf at the end.",
        ],
        "preparation_notes": "Boiling with no added oil keeps this low in fat. Check the spice mix label for "
        "added salt.",
    },
    {
        "title": "Yam porridge (asaro)",
        "cuisine": "Nigerian",
        "region": "NG",
        "description": "Yam cubes cooked soft in a pepper and palm oil sauce.",
        "servings": 4,
        "time_minutes": 45,
        "tags": ["nigerian", "yam", "one-pot"],
        "diet_tags": ["dairy_free", "gluten_free"],
        "ingredients": [
            _ing("yam", 1, "kg", "peeled and cubed"),
            _ing("palm oil", 3, "tbsp"),
            _ing("blended pepper and onion", 1, "cup"),
            _ing("ground crayfish", 1, "tbsp", "optional"),
            _ing("spinach", 2, "cups", "optional"),
            _ing("salt", None, None, "to taste"),
        ],
        "steps": [
            "Cover the yam with water and boil until almost soft.",
            "Add the pepper blend, palm oil and crayfish and simmer until the yam starts to break down.",
            "Mash some pieces to thicken, then stir in the spinach.",
        ],
        "preparation_notes": "Yam is mainly starch. Adding greens and a protein side makes a more balanced meal.",
    },
    {
        "title": "Overnight oats with berries",
        "cuisine": "American",
        "region": "US",
        "description": "No-cook breakfast of rolled oats soaked overnight.",
        "servings": 1,
        "time_minutes": 5,
        "tags": ["breakfast", "no-cook", "high-fibre"],
        "diet_tags": ["vegetarian"],
        "ingredients": [
            _ing("rolled oats", 0.5, "cup"),
            _ing("milk or unsweetened plant milk", 0.5, "cup"),
            _ing("plain Greek yogurt", 0.25, "cup"),
            _ing("chia seeds", 1, "tbsp"),
            _ing("mixed berries", 0.5, "cup"),
        ],
        "steps": [
            "Stir the oats, milk, yogurt and chia together in a jar.",
            "Refrigerate overnight. Top with berries before eating.",
        ],
        "preparation_notes": "Plain yogurt and fruit sweeten without added sugar. Oats provide beta-glucan fibre.",
    },
    {
        "title": "Red lentil soup",
        "cuisine": "Mediterranean",
        "region": "EU",
        "description": "Simple, filling lentil soup with cumin and lemon.",
        "servings": 4,
        "time_minutes": 35,
        "tags": ["soup", "high-fibre", "budget"],
        "diet_tags": ["vegan", "vegetarian", "dairy_free", "gluten_free"],
        "ingredients": [
            _ing("red lentils", 1, "cup"),
            _ing("olive oil", 2, "tbsp"),
            _ing("onion", 1, None),
            _ing("carrot", 1, None),
            _ing("garlic", 2, "cloves"),
            _ing("ground cumin", 1, "tsp"),
            _ing("vegetable stock", 5, "cups", "low-sodium if possible"),
            _ing("lemon", 0.5, None),
        ],
        "steps": [
            "Soften the onion, carrot and garlic in the oil. Add the cumin.",
            "Add the lentils and stock and simmer for 20 minutes.",
            "Blend partly and finish with lemon juice.",
        ],
        "preparation_notes": "Lentils give protein and fibre for little fat. Stock is the main sodium source.",
    },
    {
        "title": "Chickpea and vegetable salad",
        "cuisine": "Mediterranean",
        "region": "EU",
        "description": "Chickpeas, cucumber, tomato and herbs with an olive oil dressing.",
        "servings": 2,
        "time_minutes": 15,
        "tags": ["salad", "no-cook", "lunch"],
        "diet_tags": ["vegan", "vegetarian", "dairy_free", "gluten_free"],
        "ingredients": [
            _ing("cooked chickpeas", 1.5, "cups", "rinsed if canned"),
            _ing("cucumber", 1, None),
            _ing("tomatoes", 2, None),
            _ing("red onion", 0.5, None),
            _ing("parsley", 1, "handful"),
            _ing("extra-virgin olive oil", 2, "tbsp"),
            _ing("lemon juice", 1, "tbsp"),
        ],
        "steps": ["Chop the vegetables and herbs.", "Toss everything with the oil and lemon juice."],
        "preparation_notes": "Rinsing canned chickpeas removes some of the added salt.",
    },
    {
        "title": "Chicken and vegetable stir-fry",
        "cuisine": "Asian-inspired",
        "region": "US",
        "description": "Quick stir-fry with lean chicken and lots of vegetables.",
        "servings": 2,
        "time_minutes": 25,
        "tags": ["dinner", "high-protein", "quick"],
        "diet_tags": ["dairy_free", "high_protein"],
        "ingredients": [
            _ing("chicken breast", 300, "g", "sliced"),
            _ing("broccoli", 2, "cups"),
            _ing("bell pepper", 1, None),
            _ing("garlic", 2, "cloves"),
            _ing("ginger", 1, "tbsp", "grated"),
            _ing("reduced-sodium soy sauce", 2, "tbsp", "contains wheat and soy"),
            _ing("vegetable oil", 1, "tbsp"),
        ],
        "steps": [
            "Stir-fry the chicken in the oil until cooked, then set aside.",
            "Stir-fry the vegetables, garlic and ginger for 3-4 minutes.",
            "Return the chicken, add the soy sauce and toss.",
        ],
        "preparation_notes": "Soy sauce is the main sodium source; reduced-sodium versions cut it substantially. "
        "Use tamari labelled gluten-free for a gluten-free version.",
    },
]


# Local food glossary. Names are as commonly used; `names_reviewed` stays False until an editor checks them.
LOCAL_FOODS: list[dict] = [
    {
        "slug": "jollof-rice",
        "name": "Jollof rice",
        "kind": "dish",
        "names": {"pidgin": "jollof", "yoruba": "jollof", "igbo": "jollof", "hausa": "jollof"},
        "description": "Rice cooked in a tomato, pepper and onion base with oil and stock.",
        "main_ingredients": ["rice", "tomato", "pepper", "onion", "vegetable oil", "stock"],
        "preparation": "Fried base, then simmered",
        "nutrition_notes": "Mostly starch from rice. Fat depends on the oil used; sodium depends on stock "
        "cubes and seasoning.",
        "recipe_title": "Jollof rice",
    },
    {
        "slug": "egusi-soup",
        "name": "Egusi soup",
        "kind": "dish",
        "names": {"yoruba": "efo elegusi", "igbo": "ofe egwusi", "hausa": "miyan agushi"},
        "description": "Soup of ground melon seeds, palm oil, greens and meat or fish.",
        "main_ingredients": ["melon seeds", "palm oil", "leafy greens", "meat or fish", "crayfish"],
        "preparation": "Fried then simmered",
        "nutrition_notes": "Rich in fat and protein from the seeds. Palm oil adds saturated fat.",
        "recipe_title": "Egusi soup",
    },
    {
        "slug": "moi-moi",
        "name": "Moi moi",
        "kind": "dish",
        "names": {"yoruba": "moinmoin"},
        "description": "Steamed pudding of blended peeled beans and peppers.",
        "main_ingredients": ["black-eyed beans", "pepper", "onion", "oil"],
        "preparation": "Steamed",
        "nutrition_notes": "Good source of plant protein and fibre; steaming adds no frying fat.",
        "recipe_title": "Moi moi",
    },
    {
        "slug": "akara",
        "name": "Akara",
        "kind": "dish",
        "names": {"yoruba": "akara", "hausa": "kosai"},
        "description": "Deep-fried fritters of blended black-eyed beans.",
        "main_ingredients": ["black-eyed beans", "onion", "pepper", "vegetable oil"],
        "preparation": "Deep-fried",
        "nutrition_notes": "Same beans as moi moi, but frying adds a lot of fat.",
        "recipe_title": "Akara (bean fritters)",
    },
    {
        "slug": "eba",
        "name": "Eba",
        "kind": "swallow",
        "names": {"pidgin": "eba", "yoruba": "eba", "igbo": "eba"},
        "description": "Dough made by stirring garri (roasted grated cassava) into hot water.",
        "main_ingredients": ["garri (cassava)"],
        "preparation": "Mixed with hot water",
        "nutrition_notes": "Almost all starch with little protein. Eat with protein- and vegetable-rich soups.",
    },
    {
        "slug": "amala",
        "name": "Amala",
        "kind": "swallow",
        "names": {"yoruba": "amala"},
        "description": "Dark swallow made from yam flour (elubo); cassava and plantain versions exist.",
        "main_ingredients": ["yam flour"],
        "preparation": "Stirred into boiling water",
        "nutrition_notes": "Mainly starch. Usually eaten with ewedu and gbegiri soups.",
    },
    {
        "slug": "pounded-yam",
        "name": "Pounded yam",
        "kind": "swallow",
        "names": {"yoruba": "iyan"},
        "description": "Boiled yam pounded into a smooth, stretchy dough.",
        "main_ingredients": ["yam"],
        "preparation": "Boiled and pounded",
        "nutrition_notes": "Starchy. Instant 'poundo' flours may differ from fresh yam; check the label.",
    },
    {
        "slug": "efo-riro",
        "name": "Efo riro",
        "kind": "dish",
        "names": {"yoruba": "efo riro"},
        "description": "Rich vegetable stew of leafy greens in a pepper base with palm oil.",
        "main_ingredients": ["spinach", "pepper", "palm oil", "locust beans", "meat or fish"],
        "preparation": "Fried base, greens briefly cooked",
        "nutrition_notes": "Greens add fibre, vitamins and minerals; palm oil adds saturated fat.",
        "recipe_title": "Efo riro",
    },
    {
        "slug": "suya",
        "name": "Suya",
        "kind": "dish",
        "names": {"hausa": "suya", "pidgin": "suya"},
        "description": "Skewered grilled beef coated in a spiced groundnut powder (yaji).",
        "main_ingredients": ["beef", "groundnut powder", "spices", "onion"],
        "preparation": "Grilled over open flame",
        "nutrition_notes": "High in protein. Contains peanuts. Charred meat forms compounds that agencies "
        "advise limiting.",
    },
    {
        "slug": "puff-puff",
        "name": "Puff-puff",
        "kind": "snack",
        "names": {"pidgin": "puff-puff"},
        "description": "Deep-fried sweet dough balls.",
        "main_ingredients": ["wheat flour", "sugar", "yeast", "vegetable oil"],
        "preparation": "Deep-fried",
        "nutrition_notes": "High in refined starch, added sugar and fat. Contains gluten.",
    },
    {
        "slug": "zobo",
        "name": "Zobo",
        "kind": "drink",
        "names": {"pidgin": "zobo", "hausa": "zobo", "yoruba": "isapa"},
        "description": "Drink made from dried hibiscus (roselle) petals, often with ginger and pineapple.",
        "main_ingredients": ["hibiscus petals", "ginger", "sugar (often)"],
        "preparation": "Boiled and steeped",
        "nutrition_notes": "Unsweetened zobo is low in calories; added sugar varies widely between makers.",
    },
    {
        "slug": "kunu",
        "name": "Kunu",
        "kind": "drink",
        "names": {"hausa": "kunu"},
        "description": "Northern Nigerian drink of millet, sorghum or maize with spices.",
        "main_ingredients": ["millet or sorghum", "ginger", "sugar (often)"],
        "preparation": "Soaked, blended, strained",
        "nutrition_notes": "Grain-based; sugar content depends on preparation.",
    },
    {
        "slug": "garri",
        "name": "Garri",
        "kind": "staple",
        "names": {"pidgin": "garri", "yoruba": "gaari", "igbo": "garri", "hausa": "gari"},
        "description": "Granules of fermented, roasted grated cassava, eaten as eba or soaked in water.",
        "main_ingredients": ["cassava"],
        "preparation": "Fermented and roasted",
        "nutrition_notes": "Mostly starch. Proper fermentation and roasting reduce cyanogenic compounds in cassava.",
    },
    {
        "slug": "ogbono-soup",
        "name": "Ogbono soup",
        "kind": "dish",
        "names": {"igbo": "ofe ogbono", "yoruba": "obe apon"},
        "description": "Draw soup thickened with ground wild mango (ogbono) seeds.",
        "main_ingredients": ["ogbono seeds", "palm oil", "meat or fish", "greens"],
        "preparation": "Simmered",
        "nutrition_notes": "Seeds add fat; palm oil adds saturated fat.",
    },
    {
        "slug": "dodo",
        "name": "Dodo (fried plantain)",
        "kind": "side",
        "names": {"yoruba": "dodo", "pidgin": "dodo"},
        "description": "Sliced ripe plantain fried until caramelised.",
        "main_ingredients": ["ripe plantain", "vegetable oil"],
        "preparation": "Fried",
        "nutrition_notes": "Ripe plantain has natural sugars and potassium; frying adds fat. Roasted plantain "
        "(boli) is lower in fat.",
    },
]

# Common ingredients with regional names, used for label and recipe recognition. Pending editorial review.
LOCAL_INGREDIENT_NAMES: list[dict] = [
    {"name": "Rice", "yoruba": "iresi", "igbo": "osikapa", "hausa": "shinkafa"},
    {"name": "Beans (cowpea)", "yoruba": "ewa", "igbo": "agwa", "hausa": "wake"},
    {"name": "Yam", "yoruba": "isu", "igbo": "ji", "hausa": "doya"},
    {"name": "Cassava", "yoruba": "gbaguda", "igbo": "akpu", "hausa": "rogo"},
    {"name": "Maize", "yoruba": "agbado", "igbo": "oka", "hausa": "masara"},
    {"name": "Sorghum (guinea corn)", "yoruba": "oka baba", "hausa": "dawa"},
    {"name": "Palm oil", "yoruba": "epo pupa", "igbo": "mmanu nkwu", "hausa": "manja"},
    {"name": "Groundnut (peanut)", "yoruba": "epa", "igbo": "ahu ekere", "hausa": "gyada"},
    {"name": "Melon seed", "yoruba": "egusi", "igbo": "egwusi", "hausa": "agushi"},
    {"name": "Okra", "yoruba": "ila", "igbo": "okwuru", "hausa": "kubewa"},
    {"name": "Pepper", "yoruba": "ata", "igbo": "ose", "hausa": "barkono"},
    {"name": "Onion", "yoruba": "alubosa", "igbo": "yabasi", "hausa": "albasa"},
    {"name": "Salt", "yoruba": "iyo", "igbo": "nnu", "hausa": "gishiri"},
    {"name": "Fish", "yoruba": "eja", "igbo": "azu", "hausa": "kifi"},
    {"name": "Egg", "yoruba": "eyin", "igbo": "akwa", "hausa": "kwai"},
    {"name": "Meat", "yoruba": "eran", "igbo": "anu", "hausa": "nama"},
    {"name": "Water", "yoruba": "omi", "igbo": "mmiri", "hausa": "ruwa"},
    {"name": "Bitter leaf", "yoruba": "ewuro", "igbo": "onugbu", "hausa": "shiwaka"},
    {"name": "Locust beans", "yoruba": "iru", "hausa": "dawadawa"},
]


SAFETY_TOPICS: list[dict] = [
    {
        "slug": "heavy-metals",
        "title": "Heavy metals: lead, cadmium, arsenic and mercury",
        "summary": "Metals occur naturally in soil and water and can end up in crops, rice, cocoa, root "
        "vegetables and fish. Regulators set limits and work to lower levels over time.",
        "where_found": [
            "Rice and rice-based foods (inorganic arsenic)",
            "Cocoa and dark chocolate, leafy and root vegetables (cadmium, lead)",
            "Large predatory fish such as shark, swordfish and king mackerel (mercury)",
            "Some baby foods and spices (lead), which FDA's Closer to Zero plan targets",
        ],
        "reduce_exposure": [
            "Eat a varied diet rather than large amounts of any single food.",
            "Cook rice in plenty of water and drain it, which lowers inorganic arsenic.",
            "Choose lower-mercury fish such as sardines, salmon and tilapia, especially in pregnancy.",
        ],
        "source_keys": ["fda_closer_to_zero", "fda_lead_in_food", "fda_epa_fish_advice"],
    },
    {
        "slug": "microplastics",
        "title": "Microplastics",
        "summary": "Tiny plastic particles have been found in seafood, salt, bottled water and other foods. "
        "Measurement methods are still developing, and agencies say the evidence is too limited to judge "
        "health risk.",
        "where_found": ["Seafood, especially shellfish eaten whole", "Sea salt", "Bottled and tap water"],
        "reduce_exposure": [
            "Don't heat food in plastic containers; use glass or ceramic.",
            "Evidence on health effects is limited; avoid alarmist claims about any single product.",
        ],
        "source_keys": ["efsa_microplastics_2016", "who_microplastics_2019"],
    },
    {
        "slug": "pesticides",
        "title": "Pesticide residues",
        "summary": "Agencies test foods every year against legal residue limits. Most samples are within the "
        "limits. Results are published by food type, not by brand.",
        "where_found": ["Fresh fruit and vegetables", "Grains", "Imported produce (tested at the border)"],
        "reduce_exposure": [
            "Wash and, where suitable, peel fruit and vegetables.",
            "Eating more fruit and vegetables still outweighs residue concerns for most people.",
        ],
        "source_keys": ["fda_pesticide_monitoring", "efsa_pesticide_residues"],
    },
    {
        "slug": "glyphosate",
        "title": "Glyphosate",
        "summary": "A widely used herbicide. IARC classed it as 'probably carcinogenic' (a hazard rating), while "
        "EFSA's 2023 review found no critical areas of concern for human health at authorised uses. "
        "These are different questions: hazard is whether something can cause harm, risk is whether it is "
        "likely to at real exposure levels.",
        "where_found": ["Grains such as oats and wheat", "Legumes"],
        "reduce_exposure": ["Organic-certified foods restrict synthetic herbicide use."],
        "source_keys": ["iarc_vol112_glyphosate", "efsa_glyphosate_2023"],
    },
    {
        "slug": "aflatoxins",
        "title": "Aflatoxins",
        "summary": "Toxins made by moulds on poorly dried or stored groundnuts, maize and other crops. "
        "They are a known human carcinogen and an important food-safety issue in warm, humid climates, "
        "including parts of West Africa.",
        "where_found": ["Groundnuts and groundnut products", "Maize", "Some spices and dried foods"],
        "reduce_exposure": [
            "Discard mouldy, shrivelled or discoloured nuts and grains.",
            "Buy from sellers who store produce dry, and keep it dry at home.",
        ],
        "source_keys": ["iarc_aflatoxins"],
    },
]


RISK_EXPLAINER = {
    "hazard": "Hazard: whether a substance can cause harm under some conditions.",
    "exposure": "Exposure: how much of it a person actually takes in, and how often.",
    "risk": "Risk: the chance of harm at real exposure levels. A hazard with very low exposure can be low risk.",
    "product_rule": "A study finding a contaminant in a food category does not mean a particular brand or "
    "product is contaminated. Food omniScan shows a product test result only when a verified lab report "
    "for that product exists.",
}


ARTICLES: list[dict] = [
    {
        "slug": "hazard-vs-risk",
        "title": "Hazard, exposure and risk: what the headlines leave out",
        "topic": "safety",
        "summary": "Why 'linked to cancer' doesn't tell you how risky a food is.",
        "body": "A hazard is something that can cause harm. Risk is the chance that it actually will, which "
        "depends on exposure: how much and how often.\n\nIARC classifications describe hazard, not risk. For "
        "example, processed meat and aflatoxins are both Group 1, but the size of the risk from typical "
        "exposure differs a lot.\n\nFood omniScan separates the two. Scores reflect nutrition, ingredients and "
        "processing. Contaminant information is shown as category-level research unless a verified lab test "
        "exists for the specific product.",
        "source_keys": ["iarc_vol114_processed_meat", "iarc_aflatoxins", "iarc_vol112_glyphosate"],
    },
    {
        "slug": "total-vs-added-sugars",
        "title": "Total sugars vs added sugars",
        "topic": "nutrition",
        "summary": "Why the Nutrition Facts label lists both, and which one matters most.",
        "body": "Total sugars include sugar naturally in fruit and milk. Added sugars are sugars and syrups added "
        "during processing. The FDA Daily Value for added sugars is 50 g, and WHO recommends keeping free "
        "sugars under 10% of energy.\n\nLook for added sugars by many names: cane sugar, glucose syrup, "
        "dextrose, honey, fruit juice concentrate. Food omniScan flags these in the ingredient list.",
        "source_keys": ["fda_21cfr101_9", "who_sugars_2015"],
    },
    {
        "slug": "what-is-ultra-processed",
        "title": "What 'ultra-processed' means",
        "topic": "processing",
        "summary": "The NOVA system in plain language.",
        "body": "NOVA sorts foods into four groups: 1 unprocessed or minimally processed, 2 culinary ingredients "
        "(oils, sugar, salt), 3 processed foods (canned vegetables, cheese, fresh bread), and 4 "
        "ultra-processed products made largely from industrial ingredients and additives.\n\nNOVA describes "
        "processing, not nutrition. Some group 4 foods are reasonable choices, which is why Food omniScan "
        "weighs processing as one part of the score rather than the whole score.",
        "source_keys": ["monteiro_2019_upf"],
    },
    {
        "slug": "reading-nutrition-facts",
        "title": "Reading a Nutrition Facts label in 30 seconds",
        "topic": "nutrition",
        "summary": "Serving size first, then the 5/20 rule.",
        "body": "1. Check the serving size: every number on the label is for that amount.\n2. Use %DV: 5% or "
        "less is low, 20% or more is high.\n3. Aim high for fiber, vitamin D, calcium, iron and potassium; "
        "aim low for saturated fat, sodium and added sugars.",
        "source_keys": ["fda_5_20_rule", "fda_21cfr101_9"],
    },
    {
        "slug": "contains-vs-may-contain",
        "title": "'Contains' vs 'may contain'",
        "topic": "ingredients",
        "summary": "Declared allergens and precautionary statements are different.",
        "body": "'Contains' lists allergens that are ingredients. 'May contain' or 'made in a facility that "
        "also handles' is a voluntary precautionary statement about possible cross-contact. For severe "
        "allergies, treat precautionary statements seriously and follow your allergist's advice.\n\nFood "
        "omniScan shows these as separate statuses, and an unknown status when the label data is missing.",
        "source_keys": ["us_falcpa_faster", "eu_reg_1169_2011"],
    },
    {
        "slug": "nigerian-food-labels",
        "title": "Reading Nigerian food labels and NAFDAC numbers",
        "topic": "african",
        "region": "NG",
        "summary": "What a NAFDAC registration number tells you, and how to check one.",
        "body": "Packaged food sold in Nigeria should carry a NAFDAC registration number. You can look it up "
        "in the NAFDAC Greenbook to see whether the product is registered.\n\nA registration number shows "
        "the product was registered; it isn't a health rating. Read the ingredient list and nutrition panel "
        "too. Many local products list energy in kJ and kcal per 100 g.",
        "source_keys": ["nafdac_greenbook"],
    },
    {
        "slug": "cooking-methods-nigerian-dishes",
        "title": "How cooking methods change Nigerian dishes",
        "topic": "african",
        "region": "NG",
        "summary": "Steamed moi moi vs fried akara, boiled vs fried plantain.",
        "body": "The same ingredient can end up very different depending on how it's cooked. Beans steamed as "
        "moi moi add little fat, while deep-fried akara absorbs oil. Roasted plantain (boli) has much less fat "
        "than fried dodo.\n\nPalm oil and seasoning cubes are the biggest swing factors in soups and stews: "
        "palm oil for saturated fat, cubes for sodium. Short cooking of greens keeps more vitamins.",
        "source_keys": ["fao_wafct_2019", "who_sodium_2012"],
    },
    {
        "slug": "seed-oils-evidence",
        "title": "Seed oils: what the evidence says",
        "topic": "ingredients",
        "summary": "A balanced look at a hotly debated topic.",
        "body": "Seed oils such as soybean, sunflower and corn oil are high in polyunsaturated fat. Major health "
        "bodies recommend replacing saturated fat with unsaturated fats, including these oils. Concerns raised "
        "online about omega-6 fats are not well supported by clinical evidence.\n\nWhat matters more is the "
        "food the oil comes in: deep-fried and ultra-processed foods are worth limiting regardless of the oil. "
        "Partially hydrogenated oils, a source of trans fat, are different and are no longer allowed in the "
        "US food supply.",
        "source_keys": ["fda_pho_2015", "monteiro_2019_upf"],
    },
]


# Recipe ingredient substitutions for allergies and diets (culinary guidance, not medical advice).
SUBSTITUTIONS: dict[str, list[dict]] = {
    "milk": [
        {"for": ["milk", "cream"], "use": "oat, soy or rice milk (check for added sugar)"},
        {"for": ["butter"], "use": "plant-based spread or vegetable oil"},
        {"for": ["yogurt"], "use": "unsweetened soy or coconut yogurt"},
    ],
    "eggs": [{"for": ["egg", "eggs"], "use": "1 tbsp ground flax + 3 tbsp water per egg (baking)"}],
    "peanuts": [
        {"for": ["peanut", "groundnut"], "use": "sunflower seed butter or toasted pumpkin seeds"},
    ],
    "tree_nuts": [{"for": ["almond", "cashew", "walnut"], "use": "toasted seeds (sunflower, pumpkin)"}],
    "gluten": [
        {"for": ["wheat flour", "flour"], "use": "rice, cassava or plantain flour (check for gluten-free label)"},
        {"for": ["soy sauce"], "use": "tamari labelled gluten-free"},
        {"for": ["couscous", "bulgur"], "use": "rice or quinoa"},
    ],
    "soy": [{"for": ["soy sauce"], "use": "coconut aminos"}, {"for": ["tofu"], "use": "chickpeas"}],
    "fish": [{"for": ["fish", "stockfish", "crayfish"], "use": "mushrooms or smoked paprika for savoury depth"}],
    "crustaceans": [{"for": ["crayfish", "shrimp", "prawn"], "use": "dried mushrooms or iru (locust beans)"}],
    "sesame": [{"for": ["sesame", "tahini"], "use": "sunflower seed butter"}],
    "low_sodium": [
        {"for": ["seasoning cube", "stock cube", "bouillon", "salt"], "use": "herbs, spices, iru or low-sodium stock"},
    ],
    "vegan": [
        {"for": ["meat", "beef", "goat meat", "chicken"], "use": "beans, mushrooms or tofu"},
        {"for": ["fish", "stockfish", "crayfish"], "use": "mushrooms or seaweed for savoury flavour"},
        {"for": ["honey"], "use": "date syrup"},
    ],
}
