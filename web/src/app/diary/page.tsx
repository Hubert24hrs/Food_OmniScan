"use client";

import { useRef, useState } from "react";
import { Camera, Droplets, Lightbulb, Scale, Target, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { nf } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton, UpgradeCard, isPlanError } from "@/components/ui";

type Entry = { id: string; meal_type: string; description: string; quantity_g: number | null; energy_kcal: number | null; protein: number | null; carbohydrates: number | null; fat: number | null; fiber: number | null; is_estimate: boolean; source: string };
type Micro = { label: string; unit: string; amount: number; pct_dv: number };
type Day = {
  day: string; entries: Entry[]; totals: Record<string, number> & { includes_estimates: boolean }; goals: Record<string, number>;
  targets: Record<string, number>; water: { total_ml: number; logs: { id: string; ml: number }[] }; micros: Record<string, Micro> | null; micros_locked: boolean;
};
type Summary = { series: { day: string; energy_kcal: number }[]; average_logged_day: Record<string, number> | null; days_logged: number };
type Report = { period: string; days_logged: number; days_in_period: number; averages: Record<string, number> | null; targets: Record<string, number>; top_foods: { name: string; times: number }[]; includes_estimates: boolean };
type Insights = { insights: { kind: string; message: string }[]; product_score_mix: Record<string, number>; disclaimer: string };
type MealItem = { name: string; preparation: string | null; portion_g: number; energy_kcal: number; protein_g: number; carbs_g: number; fat_g: number; fiber_g: number; confidence: number };
const MEALS = ["breakfast", "lunch", "dinner", "snack"];
const TOTALS: [string, string, string][] = [["Calories", "energy_kcal", ""], ["Protein", "protein", "g"], ["Carbs", "carbohydrates", "g"], ["Fat", "fat", "g"], ["Fiber", "fiber", "g"], ["Sodium", "sodium_mg", "mg"]];

function Bar({ value, target }: { value: number; target: number }) {
  const pct = target ? Math.min(100, (value / target) * 100) : 0;
  return <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full bg-brand" style={{ width: `${pct}%` }} /></div>;
}

export default function DiaryPage() {
  const { me, activeProfile } = useRequireAuth();
  const [day, setDay] = useState(() => new Date().toISOString().slice(0, 10));
  const pq = activeProfile ? `&profile_id=${activeProfile.id}` : "";
  const d = useApi<Day>(me ? `/diary?day=${day}${pq}` : null, [day, activeProfile?.id]);
  const s = useApi<Summary>(me ? `/diary/summary?days=7${pq}` : null, [activeProfile?.id, d.data]);
  const [form, setForm] = useState({ meal_type: "lunch", description: "", energy_kcal: "", protein: "", carbohydrates: "", fat: "", fiber: "" });
  const [error, setError] = useState<unknown>(null);
  const [tab, setTab] = useState<"week" | "month" | "insights" | null>(null);
  const [report, setReport] = useState<Report | Insights | null>(null);
  const [reportErr, setReportErr] = useState<unknown>(null);
  const [editGoals, setEditGoals] = useState(false);
  const [goals, setGoals] = useState<Record<string, string>>({});
  const [weight, setWeight] = useState("");
  const [meal, setMeal] = useState<{ items: MealItem[]; meal_type: string; notes?: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const run = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    setError(null);
    try { await fn(); d.reload(); } catch (e) { setError(e); } finally { setBusy(null); }
  };
  const num = (v: string) => (v === "" ? null : Number(v));
  const add = () => run("add", async () => {
    await api("/diary/entries", { body: { day, profile_id: activeProfile?.id, meal_type: form.meal_type, description: form.description, energy_kcal: num(form.energy_kcal), protein: num(form.protein), carbohydrates: num(form.carbohydrates), fat: num(form.fat), fiber: num(form.fiber) } });
    setForm({ ...form, description: "", energy_kcal: "", protein: "", carbohydrates: "", fat: "", fiber: "" });
  });
  const openTab = async (t: "week" | "month" | "insights") => {
    setTab(t);
    setReport(null);
    setReportErr(null);
    try {
      setReport(t === "insights" ? await api<Insights>(`/diary/insights?days=30${pq}`) : await api<Report>(`/diary/report?period=${t}${pq}`));
    } catch (e) { setReportErr(e); }
  };
  const photo = async (file: File) => {
    setBusy("photo");
    setError(null);
    try {
      const fd = new FormData();
      fd.append("task", "meal");
      fd.append("image", file);
      const r = await api<{ extracted: { items: MealItem[]; notes?: string } }>("/analysis/image", { form: fd });
      setMeal({ items: r.extracted.items || [], meal_type: form.meal_type, notes: r.extracted.notes });
    } catch (e) { setError(e); } finally { setBusy(null); }
  };

  const t = d.data?.targets || {};
  const max = Math.max(t.energy_kcal || 2000, ...(s.data?.series.map((x) => x.energy_kcal) || [0]));

  return (
    <Page title="Food diary" subtitle={activeProfile ? `Tracking for ${activeProfile.name}` : undefined} actions={<input type="date" className={inputCls} value={day} onChange={(e) => setDay(e.target.value)} aria-label="Day" />}>
      {d.error ? <ErrorBox error={d.error} onRetry={d.reload} /> : null}
      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <div className="space-y-4">
          <Card>
            <SectionTitle action={<button className="inline-flex items-center gap-1 text-sm font-semibold text-brand" onClick={() => { setEditGoals(!editGoals); setGoals(Object.fromEntries(Object.entries(t).map(([k, v]) => [k, String(v)]))); }}><Target className="size-4" /> Targets</button>}>Today&apos;s totals</SectionTitle>
            {!d.data ? <Skeleton className="h-16" /> : (
              <div className="grid grid-cols-3 gap-3 text-center sm:grid-cols-6">
                {TOTALS.map(([l, k, u]) => (
                  <div key={k} className="rounded-xl bg-surface-2 p-2">
                    <p className="text-xs text-muted">{l}</p>
                    <p className="font-display text-lg font-extrabold tabular-nums">{nf(d.data!.totals[k], 0)}{u}</p>
                    {t[k] ? <><Bar value={d.data!.totals[k] || 0} target={t[k]} /><p className="mt-0.5 text-[10px] text-muted">of {nf(t[k], 0)}</p></> : null}
                  </div>
                ))}
              </div>
            )}
            {d.data?.totals.includes_estimates && <p className="mt-2 text-xs text-warn">Includes estimated entries. Estimates aren&apos;t laboratory-measured values.</p>}
            {editGoals && (
              <form className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4" onSubmit={(e) => { e.preventDefault(); run("goals", async () => {
                await api("/diary/goals", { method: "PUT", body: { profile_id: activeProfile?.id, goals: Object.fromEntries(Object.entries(goals).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)])) } });
                setEditGoals(false);
              }); }}>
                {[["energy_kcal", "Calories"], ["protein", "Protein g"], ["carbohydrates", "Carbs g"], ["fat", "Fat g"], ["fiber", "Fiber g"], ["sodium_mg", "Sodium mg"], ["water_ml", "Water ml"], ["weight_goal_kg", "Goal weight kg"]].map(([k, l]) => (
                  <Field key={k} label={l}><input className={inputCls} inputMode="decimal" value={goals[k] || ""} onChange={(e) => setGoals({ ...goals, [k]: e.target.value })} /></Field>
                ))}
                <Button type="submit" className="col-span-2 sm:col-span-4" loading={busy === "goals"}>Save targets</Button>
                <p className="col-span-2 text-xs text-muted sm:col-span-4">Defaults are FDA Daily Values for a 2,000-calorie diet. Set your own, ideally with a health professional.</p>
              </form>
            )}
          </Card>

          {d.data && (
            <Card>
              <SectionTitle>Vitamins &amp; minerals</SectionTitle>
              {d.data.micros_locked ? <UpgradeCard title="Vitamin and mineral tracking is included with Plus" error={{ message: "See how logged foods add up against Daily Values." }} /> : Object.keys(d.data.micros || {}).length === 0 ? (
                <p className="text-sm text-muted">Log scanned products to track vitamins and minerals. Only values printed on the label are counted.</p>
              ) : (
                <ul className="grid gap-2 sm:grid-cols-2">
                  {Object.entries(d.data.micros!).map(([k, m]) => (
                    <li key={k} className="text-sm"><span className="flex justify-between"><span>{m.label}</span><span className="tabular-nums text-muted">{nf(m.amount, 1)} {m.unit} · {m.pct_dv}%</span></span><Bar value={m.pct_dv} target={100} /></li>
                  ))}
                </ul>
              )}
            </Card>
          )}

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
                        <button aria-label={`Delete ${e.description}`} className="text-muted hover:text-bad" onClick={() => run("del", () => api(`/diary/entries/${e.id}`, { method: "DELETE" }))}><Trash2 className="size-4" /></button>
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
            <SectionTitle><span className="flex items-center gap-2"><Droplets className="size-5 text-brand" /> Water</span></SectionTitle>
            <p className="font-display text-2xl font-extrabold tabular-nums">{nf(d.data?.water.total_ml, 0)} ml <span className="text-sm font-semibold text-muted">of {nf(t.water_ml, 0)} ml</span></p>
            <Bar value={d.data?.water.total_ml || 0} target={t.water_ml || 2000} />
            <div className="mt-3 flex flex-wrap gap-2">
              {[250, 500, 750].map((ml) => <Button key={ml} variant="secondary" onClick={() => run("water", () => api("/diary/water", { body: { ml, day, profile_id: activeProfile?.id } }))}>+{ml} ml</Button>)}
              {d.data?.water.logs.length ? <Button variant="ghost" onClick={() => run("water", () => api(`/diary/water/${d.data!.water.logs.at(-1)!.id}`, { method: "DELETE" }))}>Undo</Button> : null}
            </div>
          </Card>

          <Card>
            <SectionTitle><span className="flex items-center gap-2"><Camera className="size-5 text-brand" /> Log a meal from a photo</span></SectionTitle>
            <p className="text-sm text-muted">AI identifies the foods and estimates portions and calories, including Nigerian dishes like jollof rice or egusi. You review everything before it&apos;s logged.</p>
            <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={(e) => e.target.files?.[0] && photo(e.target.files[0])} />
            <Button variant="secondary" className="mt-3 w-full" loading={busy === "photo"} onClick={() => fileRef.current?.click()}>Take or choose a photo</Button>
            {meal && (
              <div className="mt-3 space-y-2">
                {meal.items.length === 0 && <p className="text-sm">No foods recognised. Try a clearer, top-down photo.</p>}
                {meal.items.map((it, i) => (
                  <div key={i} className="flex items-center gap-2 rounded-xl bg-surface-2 p-2 text-sm">
                    <span className="flex-1"><b>{it.name}</b>{it.preparation ? ` (${it.preparation})` : ""}<span className="block text-xs text-muted">~{nf(it.portion_g, 0)} g · {nf(it.energy_kcal, 0)} kcal · {nf(it.protein_g, 0)} g protein</span></span>
                    <button className="text-muted hover:text-bad" aria-label={`Remove ${it.name}`} onClick={() => setMeal({ ...meal, items: meal.items.filter((_, j) => j !== i) })}><Trash2 className="size-4" /></button>
                  </div>
                ))}
                {meal.items.length > 0 && (
                  <Button className="w-full" loading={busy === "bulk"} onClick={() => run("bulk", async () => {
                    await api("/diary/entries/bulk", { body: { entries: meal.items.map((it) => ({ day, profile_id: activeProfile?.id, meal_type: meal.meal_type, description: it.name.slice(0, 200), quantity_g: it.portion_g || null, energy_kcal: it.energy_kcal, protein: it.protein_g, carbohydrates: it.carbs_g, fat: it.fat_g, fiber: it.fiber_g, is_estimate: true })) } });
                    setMeal(null);
                  })}>Log {meal.items.length} item(s) as estimates</Button>
                )}
                <p className="text-xs text-warn">Photo estimates can be well off. Adjust portions if you know them.</p>
              </div>
            )}
          </Card>

          <Card>
            <SectionTitle>Add a food</SectionTitle>
            <p className="mb-3 text-xs text-muted">Log scanned products from their product page with exact label values. Enter other foods here.</p>
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
              <Button onClick={add} loading={busy === "add"} disabled={!form.description.trim()} className="w-full">Log food</Button>
            </div>
          </Card>
          {error ? <ErrorBox error={error} /> : null}

          <Card>
            <SectionTitle><span className="flex items-center gap-2"><Scale className="size-5 text-brand" /> Weight</span></SectionTitle>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); run("weight", async () => { await api("/diary/weight", { method: "PUT", body: { weight_kg: Number(weight), day, profile_id: activeProfile?.id } }); setWeight(""); }); }}>
              <input className={inputCls} inputMode="decimal" placeholder="kg" value={weight} onChange={(e) => setWeight(e.target.value)} aria-label="Weight in kilograms" />
              <Button type="submit" disabled={!weight}>Save</Button>
            </form>
            {t.weight_goal_kg ? <p className="mt-2 text-xs text-muted">Goal: {t.weight_goal_kg} kg</p> : null}
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
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => openTab("week")}>Weekly report</Button>
              <Button variant="secondary" onClick={() => openTab("month")}>Monthly report</Button>
              <Button variant="secondary" onClick={() => openTab("insights")}><Lightbulb className="size-4" /> Insights</Button>
            </div>
            {tab && reportErr ? <div className="mt-3">{isPlanError(reportErr) ? <UpgradeCard error={reportErr} /> : <ErrorBox error={reportErr} />}</div> : null}
            {tab && report && "insights" in report && (
              <div className="mt-3 space-y-2 text-sm">
                {report.insights.map((i) => <p key={i.message} className={`rounded-xl p-2 ${i.kind === "low" || i.kind === "high" ? "bg-warn-soft" : "bg-surface-2"}`}>{i.message}</p>)}
                {Object.keys(report.product_score_mix).length > 0 && <p className="text-xs text-muted">Logged products by score: {Object.entries(report.product_score_mix).map(([c, n]) => `${n} ${c}`).join(", ")}</p>}
                <p className="text-xs text-muted">{report.disclaimer}</p>
              </div>
            )}
            {tab && report && "averages" in report && (
              <div className="mt-3 text-sm">
                <p className="font-semibold">{report.days_logged} of {report.days_in_period} days logged</p>
                {report.averages ? (
                  <ul className="mt-1 space-y-0.5">{TOTALS.map(([l, k, u]) => <li key={k} className="flex justify-between"><span>{l}</span><span className="tabular-nums">{nf(report.averages![k], 0)}{u} / {nf(report.targets[k], 0)}{u}</span></li>)}</ul>
                ) : <p className="text-muted">Nothing logged in this period.</p>}
                {report.top_foods.length > 0 && <p className="mt-2 text-xs text-muted">Most logged: {report.top_foods.map((f) => f.name).join(", ")}</p>}
              </div>
            )}
          </Card>
        </div>
      </div>
    </Page>
  );
}
