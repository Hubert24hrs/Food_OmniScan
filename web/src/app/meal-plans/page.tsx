"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button, Card, EmptyState, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Plan = { id: string; name: string; start_date: string | null; days: { day: number; meals: unknown[] }[] };

export default function MealPlansPage() {
  const { me, activeProfile } = useRequireAuth();
  const router = useRouter();
  const plans = useApi<Plan[]>(me ? "/meal-plans" : null);
  const [form, setForm] = useState({ days: "7", region: me?.country === "NG" ? "NG" : "", kcal: "", budget: "", preferences: "" });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const go = async (key: string, fn: () => Promise<{ id: string }>) => {
    setBusy(key);
    setError(null);
    try { router.push(`/meal-plans/${(await fn()).id}`); } catch (e) { setError(e); } finally { setBusy(null); }
  };

  return (
    <Page title="Meal planner" subtitle="Plan breakfast, lunch, dinner and snacks for the week, then build your shopping list.">
      <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <Card>
          <SectionTitle><span className="flex items-center gap-2"><Sparkles className="size-5 text-brand" /> Plan with AI</span></SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Days"><select className={inputCls} value={form.days} onChange={(e) => setForm({ ...form, days: e.target.value })}>{[1, 2, 3, 4, 5, 6, 7].map((d) => <option key={d}>{d}</option>)}</select></Field>
            <Field label="Cuisine"><select className={inputCls} value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })}><option value="">Any</option><option value="NG">Nigerian</option><option value="US">American</option><option value="EU">European</option></select></Field>
            <Field label="Calories a day"><input className={inputCls} inputMode="numeric" placeholder="optional" value={form.kcal} onChange={(e) => setForm({ ...form, kcal: e.target.value })} /></Field>
            <Field label={`Weekly budget (${me?.currency || "USD"})`}><input className={inputCls} inputMode="decimal" placeholder="optional" value={form.budget} onChange={(e) => setForm({ ...form, budget: e.target.value })} /></Field>
          </div>
          <Field label="Anything else?"><input className={inputCls} placeholder="e.g. quick weekday dinners, more beans" value={form.preferences} onChange={(e) => setForm({ ...form, preferences: e.target.value })} /></Field>
          <Button className="mt-3 w-full" loading={busy === "ai"} onClick={() => go("ai", () => api("/meal-plans/generate", { body: {
            days: Number(form.days), profile_id: activeProfile?.id, region: form.region || undefined,
            kcal_target: form.kcal ? Number(form.kcal) : undefined, weekly_budget: form.budget ? Number(form.budget) : undefined,
            currency: me?.currency, preferences: form.preferences || undefined } }))}>
            Create my plan
          </Button>
          <p className="mt-2 text-xs text-muted">Follows {activeProfile?.name || "your profile"}&apos;s allergies and diets. AI plans are included with Premium.</p>
          <Button variant="secondary" className="mt-3 w-full" loading={busy === "blank"} onClick={() => go("blank", () => api("/meal-plans", { body: { name: "My week", start_date: new Date().toISOString().slice(0, 10), profile_id: activeProfile?.id, days: Array.from({ length: 7 }, (_, i) => ({ day: i + 1, meals: [] })) } }))}>
            <Plus className="size-4" /> Start a blank plan
          </Button>
          {error ? <div className="mt-3"><ErrorBox error={error} /></div> : null}
        </Card>
        <div>
          <SectionTitle>Your plans</SectionTitle>
          {plans.error ? <ErrorBox error={plans.error} onRetry={plans.reload} /> : null}
          {!plans.data ? <Skeleton className="h-32" /> : plans.data.length === 0 ? <EmptyState title="No meal plans yet" body="Create one with AI or start from a blank week." /> : (
            <ul className="space-y-2">
              {plans.data.map((p) => (
                <li key={p.id}><Link href={`/meal-plans/${p.id}`} className="card block p-4 hover:border-brand">
                  <p className="font-semibold">{p.name}</p>
                  <p className="text-sm text-muted">{p.days.length} day(s) · {p.days.reduce((n, d) => n + d.meals.length, 0)} meals{p.start_date ? ` · from ${p.start_date}` : ""}</p>
                </Link></li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Page>
  );
}
