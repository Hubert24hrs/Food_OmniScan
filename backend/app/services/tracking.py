"""Nutrition targets, period reports and intake insights.

Insights describe intake against the user's own targets ("lower than your target on most days").
They never diagnose a deficiency or a condition.
"""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FoodDiary, MealEntry, Product, WaterLog
from app.services.nutrition import FDA_DV, MICROS
from app.services.product_service import product_summary

# FDA Daily Values for a 2,000-calorie reference diet. Users can change any of them.
DEFAULT_TARGETS = {
    "energy_kcal": 2000,
    "protein": FDA_DV["protein"],
    "carbohydrates": FDA_DV["carbohydrates"],
    "fat": FDA_DV["fat"],
    "fiber": FDA_DV["fiber"],
    "sodium_mg": FDA_DV["sodium_mg"],
    "water_ml": 2000,
}
TARGET_KEYS = (*DEFAULT_TARGETS, "sugars", "weight_goal_kg")
# Which way is good: "min" = reach at least the target, "max" = stay under it.
DIRECTION = {
    "energy_kcal": "range",
    "protein": "min",
    "fiber": "min",
    "water_ml": "min",
    "carbohydrates": "range",
    "fat": "max",
    "sodium_mg": "max",
    "sugars": "max",
}
LABELS = {
    "energy_kcal": "Calories",
    "protein": "Protein",
    "carbohydrates": "Carbohydrates",
    "fat": "Fat",
    "fiber": "Fiber",
    "sodium_mg": "Sodium",
    "sugars": "Sugars",
    "water_ml": "Water",
}
NUTR = ("energy_kcal", "protein", "carbohydrates", "fat", "fiber", "sugars", "sodium")


def targets_for(goals: dict | None) -> dict:
    t = dict(DEFAULT_TARGETS)
    for k, v in (goals or {}).items():
        if k in TARGET_KEYS and isinstance(v, int | float) and v >= 0:
            t[k] = v
    return t


def day_totals(entries: list[MealEntry]) -> dict:
    tot = {k: 0.0 for k in NUTR}
    for e in entries:
        for k in NUTR:
            v = getattr(e, k)
            if v is not None:
                tot[k] += v
    out = {k: round(v, 1) for k, v in tot.items() if k != "sodium"}
    out["sodium_mg"] = round(tot["sodium"] * 1000)
    return out


def micro_totals(entries: list[MealEntry]) -> dict:
    tot: dict[str, float] = {}
    for e in entries:
        for k, v in (e.micros or {}).items():
            tot[k] = tot.get(k, 0.0) + v
    return {
        k: {"label": MICROS[k][0], "unit": MICROS[k][1], "amount": round(v, 2), "pct_dv": round(v / MICROS[k][2] * 100)}
        for k, v in tot.items()
        if k in MICROS
    }


def water_total(db: Session, profile_id: str, day: date) -> int:
    rows = db.scalars(select(WaterLog.ml).where(WaterLog.profile_id == profile_id, WaterLog.day == day)).all()
    return int(sum(rows))


def period_report(db: Session, profile_id: str, start: date, end: date, goals: dict | None) -> dict:
    """Per-day totals and averages over logged days, plus top foods and score of logged products."""
    targets = targets_for(goals)
    diaries = db.scalars(
        select(FoodDiary).where(FoodDiary.profile_id == profile_id, FoodDiary.day >= start, FoodDiary.day <= end)
    ).all()
    by_day = {d.day: d.entries for d in diaries if d.entries}
    days = []
    cur = start
    while cur <= end:
        entries = by_day.get(cur, [])
        days.append(
            {
                "day": cur.isoformat(),
                "logged": bool(entries),
                "totals": day_totals(entries) if entries else None,
                "water_ml": water_total(db, profile_id, cur),
            }
        )
        cur += timedelta(days=1)
    logged = [d for d in days if d["logged"]]
    averages = None
    if logged:
        keys = logged[0]["totals"].keys()
        averages = {k: round(sum(d["totals"][k] for d in logged) / len(logged), 1) for k in keys}
    all_entries = [e for es in by_day.values() for e in es]
    foods = Counter(e.description for e in all_entries)
    product_ids = [e.product_id for e in all_entries if e.product_id]
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days_logged": len(logged),
        "days_in_period": len(days),
        "days": days,
        "averages": averages,
        "targets": targets,
        "top_foods": [{"name": n, "times": c} for n, c in foods.most_common(5)],
        "products_logged": len(set(product_ids)),
        "includes_estimates": any(e.is_estimate for e in all_entries),
        "micros": micro_totals(all_entries) if all_entries else {},
    }


def insights(report: dict) -> list[dict]:
    """Plain-language patterns against the user's targets. Needs at least 3 logged days."""
    out: list[dict] = []
    logged = [d for d in report["days"] if d["logged"]]
    if len(logged) < 3:
        return [
            {
                "kind": "info",
                "nutrient": None,
                "message": "Log at least 3 days to see patterns in your eating.",
            }
        ]
    t = report["targets"]
    for k, direction in DIRECTION.items():
        target = t.get(k)
        if not target:
            continue
        vals = [d["water_ml"] for d in report["days"]] if k == "water_ml" else [d["totals"].get(k, 0) for d in logged]
        n = len(vals)
        low = sum(1 for v in vals if v < 0.7 * target)
        high = sum(1 for v in vals if v > 1.15 * target)
        label = LABELS[k]
        if direction in ("min", "range") and low >= max(2, n * 0.6):
            out.append(
                {
                    "kind": "low",
                    "nutrient": k,
                    "message": f"{label} was below 70% of your target on {low} of {n} days. "
                    "This may be worth looking at; it isn't a diagnosis.",
                }
            )
        if direction in ("max", "range") and high >= max(2, n * 0.6):
            out.append(
                {
                    "kind": "high",
                    "nutrient": k,
                    "message": f"{label} was above your target on {high} of {n} days.",
                }
            )
    for k, m in report.get("micros", {}).items():
        avg_pct = m["pct_dv"] / len(logged)
        if avg_pct < 50:
            out.append(
                {
                    "kind": "low",
                    "nutrient": k,
                    "message": f"Logged {m['label'].lower()} averaged about {round(avg_pct)}% of the Daily Value. "
                    "Logged foods may not list every vitamin and mineral, so this can understate intake.",
                }
            )
    if report["includes_estimates"]:
        out.append(
            {
                "kind": "info",
                "nutrient": None,
                "message": "Some entries are AI or manual estimates, so these patterns are approximate.",
            }
        )
    if not out:
        out.append({"kind": "good", "nutrient": None, "message": "Your logged days were close to your targets."})
    return out


def scored_product_mix(db: Session, product_ids: list[str]) -> dict:
    """Share of logged products by score colour (for 'food choice patterns')."""
    colors = Counter()
    for pid in set(product_ids):
        p = db.get(Product, pid)
        if p:
            colors[product_summary(db, p)["color"]] += 1
    return dict(colors)
