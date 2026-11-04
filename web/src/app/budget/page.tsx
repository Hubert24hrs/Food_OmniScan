"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button, Card, EmptyState, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Summary = { month: string; currency: string; budget: number | null; spent: number; remaining: number | null; by_store: Record<string, number>; other_currencies: Record<string, number>; purchases: number; shared: boolean };
type Purchase = { id: string; name: string; quantity: string | null; price: number; currency: string; store: string | null; purchased_on: string };

export default function BudgetPage() {
  const { me } = useRequireAuth();
  const [month, setMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const s = useApi<Summary>(me ? `/budget?month=${month}` : null, [month]);
  const list = useApi<Purchase[]>(me ? "/purchases" : null, [s.data?.spent]);
  const cur = s.data?.currency || me?.currency || "USD";
  const [b, setB] = useState("");
  const [f, setF] = useState({ name: "", price: "", store: "", purchased_on: "", add_to_pantry: false, expires_on: "" });
  const [error, setError] = useState<unknown>(null);
  const run = async (fn: () => Promise<unknown>) => { setError(null); try { await fn(); s.reload(); list.reload(); } catch (e) { setError(e); } };
  const pct = s.data?.budget ? Math.min(100, (s.data.spent / s.data.budget) * 100) : 0;

  return (
    <Page title="Grocery budget" subtitle={s.data?.shared ? "Shared with your household." : "Track what you spend on food each month."} actions={<input type="month" className={inputCls} value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Month" />}>
      {s.error ? <ErrorBox error={s.error} onRetry={s.reload} /> : !s.data ? <Skeleton className="h-40" /> : (
        <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
          <div className="space-y-4">
            <Card>
              <SectionTitle>{new Date(month + "-15").toLocaleDateString("en-US", { month: "long", year: "numeric" })}</SectionTitle>
              <p className="font-display text-3xl font-extrabold">{money(s.data.spent, cur)}<span className="text-base font-semibold text-muted">{s.data.budget ? ` of ${money(s.data.budget, cur)}` : " spent"}</span></p>
              {s.data.budget ? (
                <>
                  <div className="mt-3 h-3 overflow-hidden rounded-full bg-surface-2" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
                    <div className={`h-full ${pct >= 100 ? "bg-bad" : pct >= 85 ? "bg-warn" : "bg-good"}`} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="mt-1 text-sm text-muted">{s.data.remaining! >= 0 ? `${money(s.data.remaining!, cur)} left` : `${money(-s.data.remaining!, cur)} over budget`}</p>
                </>
              ) : null}
              {Object.keys(s.data.by_store).length > 0 && (
                <ul className="mt-3 space-y-1 text-sm">{Object.entries(s.data.by_store).map(([k, v]) => <li key={k} className="flex justify-between"><span>{k}</span><span className="tabular-nums">{money(v, cur)}</span></li>)}</ul>
              )}
              {Object.keys(s.data.other_currencies).length > 0 && <p className="mt-2 text-xs text-muted">Also spent: {Object.entries(s.data.other_currencies).map(([c, v]) => money(v, c)).join(", ")}</p>}
            </Card>
            <Card>
              <SectionTitle>Shopping history</SectionTitle>
              {!list.data ? <Skeleton className="h-20" /> : list.data.length === 0 ? <EmptyState title="No purchases yet" /> : (
                <ul className="divide-y divide-line text-sm">
                  {list.data.map((p) => (
                    <li key={p.id} className="flex items-center gap-2 py-2">
                      <span className="flex-1">{p.name}<span className="block text-xs text-muted">{p.purchased_on}{p.store ? ` · ${p.store}` : ""}</span></span>
                      <span className="tabular-nums">{money(p.price, p.currency)}</span>
                      <button aria-label={`Delete ${p.name}`} className="text-muted hover:text-bad" onClick={() => run(() => api(`/purchases/${p.id}`, { method: "DELETE" }))}><Trash2 className="size-4" /></button>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
          <div className="space-y-4">
            <Card>
              <SectionTitle>Log a purchase</SectionTitle>
              <div className="space-y-2">
                <Field label="Item"><input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
                <div className="grid grid-cols-2 gap-2">
                  <Field label={`Price (${cur})`}><input className={inputCls} inputMode="decimal" value={f.price} onChange={(e) => setF({ ...f, price: e.target.value })} /></Field>
                  <Field label="Store"><input className={inputCls} value={f.store} onChange={(e) => setF({ ...f, store: e.target.value })} /></Field>
                </div>
                <Field label="Date"><input type="date" className={inputCls} value={f.purchased_on} onChange={(e) => setF({ ...f, purchased_on: e.target.value })} /></Field>
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.add_to_pantry} onChange={(e) => setF({ ...f, add_to_pantry: e.target.checked })} /> Also add to pantry</label>
                {f.add_to_pantry && <Field label="Expiry date"><input type="date" className={inputCls} value={f.expires_on} onChange={(e) => setF({ ...f, expires_on: e.target.value })} /></Field>}
                <Button className="w-full" disabled={!f.name.trim() || !f.price} onClick={() => run(async () => {
                  await api("/purchases", { body: { name: f.name, price: Number(f.price), currency: cur, store: f.store || null, purchased_on: f.purchased_on || null, add_to_pantry: f.add_to_pantry, expires_on: f.expires_on || null } });
                  setF({ name: "", price: "", store: "", purchased_on: "", add_to_pantry: false, expires_on: "" });
                })}>Log purchase</Button>
              </div>
            </Card>
            <Card>
              <SectionTitle>Monthly budget</SectionTitle>
              <div className="flex gap-2">
                <input className={inputCls} inputMode="decimal" placeholder={s.data.budget ? String(s.data.budget) : "Amount"} value={b} onChange={(e) => setB(e.target.value)} aria-label="Monthly budget" />
                <Button disabled={!b} onClick={() => run(async () => { await api("/budget", { method: "PUT", body: { monthly_amount: Number(b), currency: cur } }); setB(""); })}>Save</Button>
              </div>
            </Card>
          </div>
        </div>
      )}
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
    </Page>
  );
}
