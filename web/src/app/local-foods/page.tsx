"use client";

import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/useApi";
import { Badge, Card, Chip, ErrorBox, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Food = { slug: string; name: string; kind: string; names: Record<string, string>; description: string; main_ingredients: string[]; preparation: string; nutrition_notes: string; recipe_id: string | null };
type Resp = { foods: Food[]; ingredient_names: Record<string, string>[]; note: string };
const KINDS = [["", "All"], ["dish", "Dishes"], ["swallow", "Swallows"], ["snack", "Snacks"], ["drink", "Drinks"], ["staple", "Staples"], ["side", "Sides"]];
const LANG: Record<string, string> = { pidgin: "Pidgin", yoruba: "Yoruba", igbo: "Igbo", hausa: "Hausa" };

export default function LocalFoodsPage() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const r = useApi<Resp>(`/local-foods?${new URLSearchParams({ ...(q ? { q } : {}), ...(kind ? { kind } : {}) })}`, [q, kind]);
  return (
    <Page title="Nigerian foods" subtitle="Familiar dishes and ingredients, how they're cooked, and what that means for nutrition.">
      <input className={`${inputCls} mb-3`} placeholder="Search in English, Pidgin, Yoruba, Igbo or Hausa" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search local foods" />
      <div className="mb-4 flex flex-wrap gap-2">{KINDS.map(([k, l]) => <Chip key={k} active={kind === k} onClick={() => setKind(k)}>{l}</Chip>)}</div>
      {r.error ? <ErrorBox error={r.error} onRetry={r.reload} /> : !r.data ? <Skeleton className="h-60" /> : (
        <>
          <div className="grid gap-3 md:grid-cols-2">
            {r.data.foods.map((f) => (
              <Card key={f.slug}>
                <div className="flex items-start justify-between gap-2">
                  <p className="font-display text-lg font-bold">{f.name}</p>
                  <Badge tone="brand" className="capitalize">{f.kind}</Badge>
                </div>
                {Object.keys(f.names).length > 0 && <p className="mt-1 text-xs text-muted">{Object.entries(f.names).map(([k, v]) => `${LANG[k] || k}: ${v}`).join(" · ")}</p>}
                <p className="mt-2 text-sm">{f.description}</p>
                <p className="mt-2 text-sm"><b>Cooking:</b> {f.preparation}. {f.nutrition_notes}</p>
                <p className="mt-1 text-xs text-muted">Main ingredients: {f.main_ingredients.join(", ")}</p>
                {f.recipe_id && <Link href={`/recipes/${f.recipe_id}`} className="mt-2 inline-block text-sm font-semibold text-brand underline">See the recipe</Link>}
              </Card>
            ))}
          </div>
          <Card className="mt-4">
            <SectionTitle>Ingredient names</SectionTitle>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs text-muted"><tr><th className="py-1 pr-3">English</th><th className="pr-3">Yoruba</th><th className="pr-3">Igbo</th><th>Hausa</th></tr></thead>
                <tbody>{r.data.ingredient_names.map((n) => <tr key={n.name} className="border-t border-line"><td className="py-1 pr-3 font-semibold">{n.name}</td><td className="pr-3">{n.yoruba || "—"}</td><td className="pr-3">{n.igbo || "—"}</td><td>{n.hausa || "—"}</td></tr>)}</tbody>
              </table>
            </div>
          </Card>
          <p className="mt-3 text-xs text-muted">{r.data.note}</p>
        </>
      )}
    </Page>
  );
}
