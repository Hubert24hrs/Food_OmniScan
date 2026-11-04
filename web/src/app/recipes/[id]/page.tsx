"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { Clock, ListPlus, Sparkles, Trash2, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { nf } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { VerdictPill } from "@/components/score";
import { Badge, Button, Card, ErrorBox, Page, SectionTitle, Skeleton } from "@/components/ui";

const NUTRIENT_LABEL: Record<string, [string, string]> = {
  energy_kcal: ["Calories", ""], protein: ["Protein", " g"], carbohydrates: ["Carbs", " g"], fat: ["Fat", " g"],
  fiber: ["Fiber", " g"], sugars: ["Sugars", " g"], sodium_mg: ["Sodium", " mg"],
};
type Ingredient = { name: string; quantity: number | null; unit: string | null; note: string | null };
type Compat = {
  profiles: { profile_name: string; verdict: "green" | "yellow" | "red"; reasons: { severity: string; message: string }[] }[];
  allergens: { code: string; name: string; status: string }[];
  substitutions: { because: string; replace: string[]; with: string }[];
  note: string;
};
type Recipe = {
  id: string; title: string; description: string | null; cuisine: string | null; servings: number; time_minutes: number | null;
  ingredients: Ingredient[]; steps: string[]; preparation_notes: string | null; diet_tags: string[]; tags: string[];
  nutrition_per_serving: Record<string, number> | null; nutrition_is_estimate: boolean; ai_generated: boolean; mine: boolean;
  compatibility: Compat | null; notice?: string;
};

export default function RecipePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me, activeProfile } = useAuth();
  const r = useApi<Recipe>(`/recipes/${id}${activeProfile ? `?profile_ids=${activeProfile.id}` : ""}`, [activeProfile?.id]);
  const [servings, setServings] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    setMsg(null);
    try { await fn(); } catch (e) { setError(e); } finally { setBusy(null); }
  };

  if (r.error) return <Page><ErrorBox error={r.error} onRetry={r.reload} /></Page>;
  if (!r.data) return <Page><Skeleton className="h-64" /></Page>;
  const x = r.data;
  const n = servings || x.servings;
  const factor = n / x.servings;
  const c = x.compatibility;

  return (
    <Page title={x.title} subtitle={x.description || undefined}>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {x.cuisine && <Badge tone="brand">{x.cuisine}</Badge>}
        {x.time_minutes && <Badge><Clock className="size-3" /> {x.time_minutes} min</Badge>}
        {x.ai_generated && <Badge tone="amber">AI-generated</Badge>}
        {x.diet_tags.map((d) => <Badge key={d} tone="green">{d.replace("_", " ")}</Badge>)}
      </div>
      {x.notice && <p className="mb-4 rounded-xl bg-warn-soft p-3 text-sm text-warn">{x.notice}</p>}

      {c && (
        <Card className="mb-4">
          <SectionTitle>For {c.profiles.map((p) => p.profile_name).join(", ")}</SectionTitle>
          <div className="space-y-2">
            {c.profiles.map((p) => (
              <div key={p.profile_name}>
                <VerdictPill verdict={p.verdict} name={p.profile_name} />
                <ul className="mt-1 space-y-0.5 text-sm">
                  {p.reasons.filter((q) => q.severity !== "green").map((q) => <li key={q.message}>{q.message}</li>)}
                </ul>
              </div>
            ))}
          </div>
          {c.substitutions.length > 0 && (
            <div className="mt-3 rounded-xl bg-surface-2 p-3 text-sm">
              <p className="font-semibold">Suggested swaps</p>
              <ul className="mt-1 list-disc pl-5">
                {c.substitutions.map((s) => <li key={s.because + s.with}>Replace {s.replace.join(", ")} with {s.with} <span className="text-muted">({s.because.replace("_", " ")})</span></li>)}
              </ul>
            </div>
          )}
          <p className="mt-2 text-xs text-muted">{c.note}</p>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-[1fr_1.3fr]">
        <Card>
          <SectionTitle action={
            <label className="flex items-center gap-1 text-sm"><Users className="size-4" />
              <input type="number" min={1} max={50} className="w-16 rounded-lg border border-line bg-surface px-2 py-1" value={n} onChange={(e) => setServings(Math.max(1, Number(e.target.value) || 1))} aria-label="Servings" />
            </label>
          }>Ingredients</SectionTitle>
          <ul className="space-y-1.5 text-sm">
            {x.ingredients.map((i) => (
              <li key={i.name} className="flex gap-2">
                <span className="w-20 shrink-0 tabular-nums text-muted">{i.quantity != null ? `${nf(i.quantity * factor, 2)} ${i.unit || ""}` : ""}</span>
                <span>{i.name}{i.note && <span className="text-muted"> ({i.note})</span>}</span>
              </li>
            ))}
          </ul>
          <Button variant="secondary" className="mt-4 w-full" loading={busy === "list"} disabled={!me} onClick={() => run("list", async () => {
            const res = await api<{ added: number }>(`/recipes/${x.id}/shopping-list`, { body: { servings: n } });
            setMsg(`Added ${res.added} item(s) to a new shopping list.`);
          })}><ListPlus className="size-4" /> Add ingredients to a shopping list</Button>
        </Card>
        <div className="space-y-4">
          <Card>
            <SectionTitle>Method</SectionTitle>
            <ol className="list-decimal space-y-2 pl-5 text-sm">{x.steps.map((s) => <li key={s}>{s}</li>)}</ol>
            {x.preparation_notes && <p className="mt-3 rounded-xl bg-surface-2 p-3 text-sm"><b>How cooking affects nutrition:</b> {x.preparation_notes}</p>}
          </Card>
          <Card>
            <SectionTitle>Nutrition per serving</SectionTitle>
            {x.nutrition_per_serving ? (
              <>
                <div className="grid grid-cols-3 gap-2 text-center text-sm">
                  {Object.entries(x.nutrition_per_serving).map(([k, v]) => (
                    <div key={k} className="rounded-xl bg-surface-2 p-2"><p className="text-xs text-muted">{NUTRIENT_LABEL[k]?.[0] || k}</p><p className="font-bold tabular-nums">{nf(v, 0)}{NUTRIENT_LABEL[k]?.[1] ?? ""}</p></div>
                  ))}
                </div>
                <p className="mt-2 text-xs text-warn">Rough AI estimate from typical ingredients, not a measurement.</p>
              </>
            ) : (
              <div>
                <p className="text-sm text-muted">No nutrition values yet. We don&apos;t invent numbers; you can request an AI estimate.</p>
                <Button variant="secondary" className="mt-2" loading={busy === "est"} disabled={!me} onClick={() => run("est", async () => { await api(`/recipes/${x.id}/nutrition-estimate`, { method: "POST" }); r.reload(); })}>
                  <Sparkles className="size-4" /> Estimate with AI
                </Button>
              </div>
            )}
          </Card>
        </div>
      </div>
      {msg && <p className="mt-4 rounded-xl bg-surface-2 p-3 text-sm" role="status">{msg}</p>}
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
      {x.mine && (
        <Button variant="ghost" className="mt-4 text-bad" onClick={() => run("del", async () => { await api(`/recipes/${x.id}`, { method: "DELETE" }); router.push("/recipes"); })}>
          <Trash2 className="size-4" /> Delete my recipe
        </Button>
      )}
    </Page>
  );
}
