"use client";

import { useState } from "react";
import { Check, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Item = { id: string; name: string; quantity: string | null; location: string; expires_on: string | null; days_left: number | null; status: "expired" | "soon" | "ok" | null; shared: boolean };
const LOC = ["fridge", "freezer", "cupboard"];

function ExpiryBadge({ i }: { i: Item }) {
  if (i.status === null) return null;
  if (i.status === "expired") return <Badge tone="red">Expired</Badge>;
  if (i.status === "soon") return <Badge tone="amber">{i.days_left === 0 ? "Today" : `${i.days_left} day(s)`}</Badge>;
  return <Badge tone="green">{i.days_left} days</Badge>;
}

export default function PantryPage() {
  const { me } = useRequireAuth();
  const items = useApi<Item[]>(me ? "/pantry" : null);
  const [form, setForm] = useState({ name: "", quantity: "", location: "cupboard", expires_on: "" });
  const [error, setError] = useState<unknown>(null);
  const [loc, setLoc] = useState("");

  const add = async () => {
    setError(null);
    try {
      await api("/pantry", { body: { name: form.name, quantity: form.quantity || null, location: form.location, expires_on: form.expires_on || null } });
      setForm({ ...form, name: "", quantity: "", expires_on: "" });
      items.reload();
    } catch (e) { setError(e); }
  };
  const act = async (fn: () => Promise<unknown>) => { try { await fn(); items.reload(); } catch (e) { setError(e); } };
  const shown = (items.data || []).filter((i) => !loc || i.location === loc);

  return (
    <Page title="Pantry" subtitle="What's at home, sorted by what expires first. We'll remind you a few days before.">
      {items.error ? <ErrorBox error={items.error} onRetry={items.reload} /> : (
        <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
          <div>
            <div className="mb-3 flex flex-wrap gap-2">
              {["", ...LOC].map((l) => <button key={l} onClick={() => setLoc(l)} aria-pressed={loc === l} className={`min-h-10 rounded-full border px-3.5 text-sm capitalize ${loc === l ? "border-brand bg-brand-soft" : "border-line"}`}>{l || "All"}</button>)}
            </div>
            {!items.data ? <Skeleton className="h-40" /> : shown.length === 0 ? <EmptyState title="Nothing here yet" body="Add what you have, or log a purchase from the budget page with 'add to pantry'." /> : (
              <Card>
                <ul className="divide-y divide-line">
                  {shown.map((i) => (
                    <li key={i.id} className="flex items-center gap-2 py-2.5 text-sm">
                      <span className="flex-1">
                        <span className="font-semibold">{i.name}</span>{i.quantity && <span className="text-muted"> · {i.quantity}</span>}
                        <span className="block text-xs capitalize text-muted">{i.location}{i.shared ? " · shared" : ""}{i.expires_on ? ` · best before ${i.expires_on}` : ""}</span>
                      </span>
                      <ExpiryBadge i={i} />
                      <button aria-label={`Mark ${i.name} used up`} className="rounded-lg p-2 text-muted hover:text-good" onClick={() => act(() => api(`/pantry/${i.id}`, { method: "PATCH", body: { used_up: true } }))}><Check className="size-4" /></button>
                      <button aria-label={`Delete ${i.name}`} className="rounded-lg p-2 text-muted hover:text-bad" onClick={() => act(() => api(`/pantry/${i.id}`, { method: "DELETE" }))}><Trash2 className="size-4" /></button>
                    </li>
                  ))}
                </ul>
              </Card>
            )}
          </div>
          <Card>
            <SectionTitle>Add an item</SectionTitle>
            <div className="space-y-2">
              <Field label="Item"><input className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Garri, 2 kg" /></Field>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Quantity"><input className={inputCls} value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
                <Field label="Where"><select className={inputCls} value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })}>{LOC.map((l) => <option key={l}>{l}</option>)}</select></Field>
              </div>
              <Field label="Expiry or best-before date"><input type="date" className={inputCls} value={form.expires_on} onChange={(e) => setForm({ ...form, expires_on: e.target.value })} /></Field>
              <Button className="w-full" disabled={!form.name.trim()} onClick={add}>Add to pantry</Button>
            </div>
          </Card>
        </div>
      )}
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
    </Page>
  );
}
