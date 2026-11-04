"use client";

import { useState } from "react";
import { gToOz, mlToFlOz, nf } from "@/lib/format";
import type { Nutrients, Product, Score } from "@/lib/types";

// FDA Daily Values (21 CFR 101.9), adults & children 4+
const DV: Record<string, number> = { fat: 78, saturated_fat: 20, cholesterol_mg: 300, sodium_mg: 2300, carbohydrates: 275, fiber: 28, added_sugars: 50, protein: 50 };

function pct(key: string, v: number | null | undefined) {
  if (v === null || v === undefined || !DV[key]) return null;
  return Math.round((v / DV[key]) * 100);
}

export function NutritionFacts({ product }: { product: Product }) {
  const n = product.nutrition;
  const serving = n?.serving_size_g || null;
  const [mode, setMode] = useState<"serving" | "100">(serving ? "serving" : "100");
  if (!n) {
    return <p className="text-sm text-muted">No nutrition facts on record. Scan the nutrition label to add them.</p>;
  }
  const unit = product.is_beverage ? "ml" : "g";
  const v: Nutrients = mode === "serving" && n.per_serving ? n.per_serving : n.per_100;
  const sodiumMg = v.sodium !== null && v.sodium !== undefined ? v.sodium * 1000 : null;
  const row = (label: string, value: number | null | undefined, u: string, dvKey?: string, indent = 0, bold = true) => {
    const p = dvKey ? pct(dvKey, dvKey === "sodium_mg" ? sodiumMg : value) : null;
    return (
      <div className={`flex justify-between border-t border-black/70 py-1 dark:border-white/50 ${indent ? "pl-4" : ""}`}>
        <span>
          <span className={bold && !indent ? "font-extrabold" : ""}>{label}</span> {value === null || value === undefined ? "—" : `${nf(value, u === "mg" ? 0 : 1)}${u}`}
        </span>
        <span className="font-extrabold tabular-nums">{p === null ? "" : `${p}%`}</span>
      </div>
    );
  };
  return (
    <div>
      <div className="mb-3 inline-flex rounded-xl border border-line p-1 text-sm" role="tablist" aria-label="Nutrition basis">
        {serving && (
          <button role="tab" aria-selected={mode === "serving"} onClick={() => setMode("serving")} className={`rounded-lg px-3 py-1.5 font-semibold ${mode === "serving" ? "bg-brand text-white dark:text-[#06201d]" : "text-muted"}`}>
            Per serving
          </button>
        )}
        <button role="tab" aria-selected={mode === "100"} onClick={() => setMode("100")} className={`rounded-lg px-3 py-1.5 font-semibold ${mode === "100" ? "bg-brand text-white dark:text-[#06201d]" : "text-muted"}`}>
          Per 100 {unit}
        </button>
      </div>
      <div className="max-w-xs border-2 border-black bg-white p-2 font-sans text-[13px] leading-tight text-black dark:border-white dark:bg-[#0b1412] dark:text-white" aria-label="Nutrition Facts">
        <p className="font-display text-3xl font-black tracking-tight">Nutrition Facts</p>
        <div className="flex justify-between border-b-8 border-black pb-1 font-bold dark:border-white">
          <span>Serving size</span>
          <span>
            {mode === "serving" && serving
              ? product.serving_size || `${serving}${unit} (${nf(product.is_beverage ? mlToFlOz(serving) : gToOz(serving))} ${product.is_beverage ? "fl oz" : "oz"})`
              : `100${unit} (${nf(product.is_beverage ? mlToFlOz(100) : gToOz(100))} ${product.is_beverage ? "fl oz" : "oz"})`}
          </span>
        </div>
        <div className="flex items-end justify-between border-b-4 border-black py-1 dark:border-white">
          <span className="text-lg font-black">Calories</span>
          <span className="text-3xl font-black tabular-nums">{v.energy_kcal === null || v.energy_kcal === undefined ? "—" : Math.round(v.energy_kcal)}</span>
        </div>
        <p className="py-0.5 text-right text-xs font-bold">% Daily Value*</p>
        {row("Total Fat", v.fat, "g", "fat")}
        {row("Saturated Fat", v.saturated_fat, "g", "saturated_fat", 1)}
        {row("Trans Fat", v.trans_fat, "g", undefined, 1)}
        {row("Cholesterol", v.cholesterol_mg, "mg", "cholesterol_mg")}
        {row("Sodium", sodiumMg, "mg", "sodium_mg")}
        {row("Total Carbohydrate", v.carbohydrates, "g", "carbohydrates")}
        {row("Dietary Fiber", v.fiber, "g", "fiber", 1)}
        {row("Total Sugars", v.sugars, "g", undefined, 1)}
        <div className="flex justify-between border-t border-black/70 py-1 pl-8 dark:border-white/50">
          <span>Includes {v.added_sugars === null || v.added_sugars === undefined ? "—" : `${nf(v.added_sugars)}g`} Added Sugars</span>
          <span className="font-extrabold">{pct("added_sugars", v.added_sugars) === null ? "" : `${pct("added_sugars", v.added_sugars)}%`}</span>
        </div>
        <div className="border-b-8 border-black dark:border-white">{row("Protein", v.protein, "g")}</div>
        {(n.micros_per_100 || []).map((m) => {
          const f = mode === "serving" && serving ? serving / 100 : 1;
          return (
            <div key={m.key} className="flex justify-between border-b border-black/30 py-0.5 dark:border-white/30">
              <span>{m.label} {nf(m.amount * f, 1)}{m.unit}</span>
              <span>{Math.round(m.pct_dv * f)}%</span>
            </div>
          );
        })}
        <p className="pt-1 text-[10px] leading-snug">
          * The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice.
        </p>
      </div>
      <p className="mt-2 text-xs text-muted">
        Source: {n.source === "usda" ? "USDA FoodData Central" : n.source === "off" ? "Open Food Facts" : n.source}. EU equivalents: salt {nf(v.salt, 2)} g, energy {nf(v.energy_kj, 0)} kJ.
      </p>
    </div>
  );
}

const lvl = { low: "bg-good-soft text-good", medium: "bg-warn-soft text-warn", high: "bg-bad-soft text-bad" } as const;

export function NutritionInfoBox({ fop }: { fop: Score["front_of_pack"] }) {
  if (!fop) return null;
  const items: [string, keyof typeof fop][] = [["Sat Fat", "saturated_fat"], ["Sodium", "sodium"], ["Added Sugars", "added_sugars"]];
  return (
    <div className="rounded-2xl border border-line p-3">
      <p className="text-xs font-bold uppercase tracking-wide text-muted">Nutrition Info · {fop.basis}</p>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {items.map(([label, key]) => {
          const it = fop[key] as { pct_dv: number | null; level: "low" | "medium" | "high" | null };
          return (
            <div key={key} className={`rounded-xl p-2 text-center ${it.level ? lvl[it.level] : "bg-grey-soft text-grey"}`}>
              <p className="text-xs font-semibold">{label}</p>
              <p className="font-display text-base font-extrabold">{it.level ? (it.level === "medium" ? "Med" : it.level[0].toUpperCase() + it.level.slice(1)) : "n/a"}</p>
              <p className="text-[11px] font-semibold opacity-80">{it.pct_dv === null ? "not reported" : `${Math.round(it.pct_dv)}% DV`}</p>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] text-muted">Low ≤5% DV · High ≥20% DV (FDA proposed front-of-package format)</p>
    </div>
  );
}
