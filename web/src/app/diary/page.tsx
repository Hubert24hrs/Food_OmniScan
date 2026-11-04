"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { nf } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Entry = { id: string; meal_type: string; description: string; quantity_g: number | null; energy_kcal: number | null; protein: number | null; carbohydrates: number | null; fat: number | null; fiber: number | null; is_estimate: boolean; source: string };
type Day = { day: string; entries: Entry[]; totals: Record<string, number> & { includes_estimates: boolean }; goals: Record<string, number> };
type Summary = { series: { day: string; energy_kcal: number }[]; average_logged_day: Record<string, number> | null; days_logged: number };
const MEALS = ["breakfast", "lunch", "dinner", "snack"];

export default function DiaryPage() {
  const { me, activeProfile } = useRequireAuth();
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const d = useApi<Day>(me ? `/diary?day=${day}${activeProfile ? `&profile_id=${activeProfile.id}` : ""}` : null, [day, activeProfile?.id]);
  const s = useApi<Summary>(me ? `/diary/summary?days=7${activeProfile ? `&profile_id=${activeProfile.id}` : ""}` : null, [activeProfile?.id, d.data]);
  const [form, setForm] = useState({ meal_type: "lunch", description: "", energy_kcal: "", protein: "", carbohydrates: "", fat: "", fiber: "" });
  const [error, setError] = useState<unknown>(null);

  const add = async () => {
    setError(null);
    try {
      const num = (v: string) => (v === "" ? null : Number(v));
      await api("/diary/entries", { body: { day, profile_id: activeProfile?.id, meal_type: form.meal_type, description: form.description, energy_kcal: num(form.energy_kcal), protein: num(form.protein), carbohydrates: num(form.carbohydrates), fat: num(form.fat), fiber: num(form.fiber) } });
      setForm({ ...form, description: "", energy_kcal: "", protein: "", carbohydrates: "", fat: "", fiber: "" });
      d.reload();
    } catch (e) { setError(e); }
  };
  const goal = d.data?.goals?.kcal || 2000;
  const max = Math.max(goal, ...(s.data?.series.map((x) => x.energy_kcal) || [0]));

  return (
    <Page title="Food diary" subtitle={activeProfile ? `Tracking for ${activeProfile.name}` : undefined} actions={<input type="date" className={inputCls} value={day} onChange={(e) => setDay(e.target.value)} aria-label="Day" />}>
      {d.error ? <ErrorBox error={d.error} onRetry={d.reload} /> : null}
      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          <Card>
            <SectionTitle>Today&apos;s totals</SectionTitle>
            {!d.data ? <Skeleton className="h-16" /> : (
              <div className="grid grid-cols-3 gap-3 text-center sm:grid-cols-5">
                {[["Calories", "energy_kcal", ""], ["Protein", "protein", "g"], ["Carbs", "carbohydrates", "g"], ["Fat", "fat", "g"], ["Fiber", "fiber", "g"]].map(([l, k, u]) => (
                  <div key={k} className="rounded-xl bg-surface-2 p-2">
                    <p className="text-xs text-muted">{l}</p>
                    <p className="font-display text-lg font-extrabold tabular-nums">{nf(d.data!.totals[k], 0)}{u}</p>
                  </div>
                ))}
              </div>
            )}
            {d.data?.totals.includes_estimates && <p className="mt-2 text-xs text-warn">Includes estimated entries. Estimates aren&apos;t laboratory-measured values.</p>}
          </Card>
          {MEALS.map((m) => {
            const entries = d.data?.entries.filter((e) => e.meal_type === m) || [];
            return (
              <Card key={m}>
                <SectionTitle>{m[0].toUpperCase() + m.slice(1)}</SectionTitle>
                {entries.length === 0 ? <p className="text-sm text-muted">Nothing logged.</p> : (
                  <ul className="divide-y divide-line text-sm">
                    {entries.map((e) => (
                      <li key={e.id} className="flex items-center gap-2 py-2">
                        <span className="flex-1">{e.description}{e.quantity_g ? <span className="text-muted"> · {nf(e.quantity_g, 0)} g</span> : null} {e.is_estimate && <Badge tone="amber">estimate</Badge>}</span>
                        <span className="tabular-nums text-muted">{nf(e.energy_kcal, 0)} kcal</span>
                        <button aria-label={`Delete ${e.description}`} className="text-muted hover:text-bad" onClick={async () => { await api(`/diary/entries/${e.id}`, { method: "DELETE" }); d.reload(); }}><Trash2 className="size-4" /></button>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            );
          })}
        </div>
        <div className="space-y-4">
          <Card>
            <SectionTitle>Add a food</SectionTitle>
            <p className="mb-3 text-xs text-muted">Scanned products can be logged from history with exact label values. Enter other foods here.</p>
            <div className="space-y-2">
              <Field label="Meal"><select className={inputCls} value={form.meal_type} onChange={(e) => setForm({ ...form, meal_type: e.target.value })}>{MEALS.map((m) => <option key={m}>{m}</option>)}</select></Field>
              <Field label="Food"><input className={inputCls} placeholder="e.g. Jollof rice, 1 cup" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
              <div className="grid grid-cols-2 gap-2">
                {(["energy_kcal", "protein", "carbohydrates", "fat", "fiber"] as const).map((k) => (
                  <Field key={k} label={k === "energy_kcal" ? "Calories" : k[0].toUpperCase() + k.slice(1) + " (g)"}>
                    <input className={inputCls} inputMode="decimal" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
                  </Field>
                ))}
              </div>
              {error ? <ErrorBox error={error} /> : null}
              <Button onClick={add} disabled={!form.description.trim()} className="w-full">Log food</Button>
            </div>
          </Card>
          <Card>
            <SectionTitle>Last 7 days</SectionTitle>
            <div className="flex h-32 items-end gap-2" role="img" aria-label="Calories per day for the last 7 days">
              {s.data?.series.map((x) => (
                <div key={x.day} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t-md bg-brand" style={{ height: `${(x.energy_kcal / max) * 100}%`, minHeight: x.energy_kcal ? 4 : 0 }} title={`${x.day}: ${Math.round(x.energy_kcal)} kcal`} />
                  <span className="text-[10px] text-muted">{new Date(x.day + "T12:00").toLocaleDateString("en-US", { weekday: "narrow" })}</span>
                </div>
              ))}
            </div>
            {s.data?.average_logged_day && <p className="mt-2 text-sm text-muted">Average on logged days: {nf(s.data.average_logged_day.energy_kcal, 0)} kcal · {nf(s.data.average_logged_day.protein, 0)} g protein</p>}
          </Card>
        </div>
      </div>
    </Page>
  );
}
