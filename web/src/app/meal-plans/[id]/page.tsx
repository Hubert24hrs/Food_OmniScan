"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ListPlus, Plus, Trash2, X } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, ErrorBox, inputCls, Page, Skeleton } from "@/components/ui";

type Meal = { meal_type: string; title: string; recipe_id: string | null; description?: string | null; estimated_kcal?: number | null };
type Plan = { id: string; name: string; start_date: string | null; profile_id: string | null; days: { day: number; meals: Meal[] }[] };
const MEALS = ["breakfast", "lunch", "dinner", "snack"];

export default function MealPlanPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me } = useRequireAuth();
  const plan = useApi<Plan>(me ? `/meal-plans/${id}` : null);
  const [adding, setAdding] = useState<{ day: number; meal_type: string; title: string } | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const save = async (p: Plan) => {
    setError(null);
    try {
      plan.setData(await api<Plan>(`/meal-plans/${p.id}`, { method: "PUT", body: { name: p.name, start_date: p.start_date, profile_id: p.profile_id, days: p.days } }));
    } catch (e) { setError(e); }
  };

  if (plan.error) return <Page><ErrorBox error={plan.error} onRetry={plan.reload} /></Page>;
  if (!plan.data) return <Page><Skeleton className="h-64" /></Page>;
  const p = plan.data;
  const kcal = (d: { meals: Meal[] }) => d.meals.reduce((n, m) => n + (m.estimated_kcal || 0), 0);

  return (
    <Page title={p.name} subtitle={p.start_date ? `Starting ${p.start_date}` : undefined} actions={
      <div className="flex gap-2">
        <Button variant="secondary" onClick={async () => {
          try {
            const r = await api<{ added: number; meals_without_recipe: string[] }>(`/meal-plans/${p.id}/shopping-list`, { body: {} });
            setMsg(`Added ${r.added} ingredient(s) to a shopping list.${r.meals_without_recipe.length ? ` Meals without a recipe: ${r.meals_without_recipe.join(", ")}.` : ""}`);
          } catch (e) { setError(e); }
        }}><ListPlus className="size-4" /> Shopping list</Button>
        <Button variant="ghost" aria-label="Delete plan" onClick={async () => { await api(`/meal-plans/${p.id}`, { method: "DELETE" }); router.push("/meal-plans"); }}><Trash2 className="size-4" /></Button>
      </div>
    }>
      {msg && <p className="mb-4 rounded-xl bg-surface-2 p-3 text-sm" role="status">{msg} <Link className="text-brand underline" href="/lists">Open lists</Link></p>}
      {error ? <div className="mb-4"><ErrorBox error={error} /></div> : null}
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {p.days.map((d) => (
          <Card key={d.day}>
            <div className="mb-2 flex items-center justify-between">
              <p className="font-display font-bold">Day {d.day}</p>
              {kcal(d) > 0 && <Badge tone="amber">~{Math.round(kcal(d))} kcal (estimate)</Badge>}
            </div>
            {MEALS.map((mt) => (
              <div key={mt} className="border-t border-line py-2 text-sm first:border-0">
                <p className="text-xs font-semibold uppercase text-muted">{mt}</p>
                {d.meals.filter((m) => m.meal_type === mt).map((m, i) => (
                  <div key={m.title + i} className="flex items-center gap-2">
                    <span className="flex-1">{m.recipe_id ? <Link className="text-brand underline" href={`/recipes/${m.recipe_id}`}>{m.title}</Link> : m.title}</span>
                    <button aria-label={`Remove ${m.title}`} className="text-muted hover:text-bad" onClick={() => save({ ...p, days: p.days.map((x) => x.day === d.day ? { ...x, meals: x.meals.filter((y) => y !== m) } : x) })}><X className="size-4" /></button>
                  </div>
                ))}
                {adding?.day === d.day && adding.meal_type === mt ? (
                  <form className="mt-1 flex gap-1" onSubmit={(e) => { e.preventDefault(); if (!adding.title.trim()) return; save({ ...p, days: p.days.map((x) => x.day === d.day ? { ...x, meals: [...x.meals, { meal_type: mt, title: adding.title.trim(), recipe_id: null }] } : x) }); setAdding(null); }}>
                    <input autoFocus className={inputCls} value={adding.title} onChange={(e) => setAdding({ ...adding, title: e.target.value })} aria-label={`Add ${mt}`} />
                    <Button type="submit">Add</Button>
                  </form>
                ) : (
                  <button className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-brand" onClick={() => setAdding({ day: d.day, meal_type: mt, title: "" })}><Plus className="size-3" /> Add</button>
                )}
              </div>
            ))}
          </Card>
        ))}
      </div>
    </Page>
  );
}
