"use client";

import { useState } from "react";
import { History, MapPin, Package, Share2, ShieldCheck, Utensils } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { Badge, Button, Card, ErrorBox, Field, inputCls, SectionTitle, UpgradeCard } from "./ui";

type Details = {
  brand: string | null;
  manufacturer: { name: string; parent_company: string | null; country: string | null; website: string | null } | null;
  nafdac: { number: string; format_ok: boolean; check_url: string; note: string } | null;
  lab_results: { lab: string; method: string | null; batch: string | null; tested_on: string | null; analyte: string; value: number | null; unit: string; threshold: number | null; threshold_jurisdiction: string | null; exceeds_threshold: boolean | null; note: string }[];
  history: { at: string; action: string; fields: string[]; note: string | null }[];
};
type Prices = { reports: number; where_to_buy: { store: string; city: string | null; country: string }[]; locked: boolean; by_store: { store: string; city: string | null; currency: string; price: number; observed_on: string }[] | null; note: string };

export function ProductActions({ productId, onMessage }: { productId: string; onMessage: (m: string) => void }) {
  const { me, activeProfile } = useAuth();
  const [open, setOpen] = useState<"diary" | "pantry" | null>(null);
  const [servings, setServings] = useState("1");
  const [meal, setMeal] = useState("snack");
  const [expires, setExpires] = useState("");
  const [error, setError] = useState<unknown>(null);
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setError(null);
    try { await fn(); onMessage(ok); setOpen(null); } catch (e) { setError(e); }
  };
  const share = async () => {
    const r = await api<{ path: string }>(`/products/${productId}/share`, { method: "POST" });
    const url = window.location.origin + r.path;
    const canShare = typeof navigator.share === "function";
    try {
      if (canShare) await navigator.share({ title: "Food omniScan report", url });
      else await navigator.clipboard.writeText(url);
      onMessage(canShare ? "Shared." : `Link copied: ${url}`);
    } catch {
      onMessage(`Share this link: ${url}`);
    }
  };

  return (
    <>
      <Button variant="secondary" onClick={share}><Share2 className="size-4" aria-hidden /> Share</Button>
      {me && <Button variant="secondary" onClick={() => setOpen(open === "diary" ? null : "diary")}><Utensils className="size-4" aria-hidden /> Log it</Button>}
      {me && <Button variant="secondary" onClick={() => setOpen(open === "pantry" ? null : "pantry")}><Package className="size-4" aria-hidden /> Pantry</Button>}
      {open && (
        <Card className="w-full">
          {open === "diary" ? (
            <div className="flex flex-wrap items-end gap-2">
              <Field label="Servings"><input className={`${inputCls} w-24`} inputMode="decimal" value={servings} onChange={(e) => setServings(e.target.value)} /></Field>
              <Field label="Meal"><select className={inputCls} value={meal} onChange={(e) => setMeal(e.target.value)}>{["breakfast", "lunch", "dinner", "snack"].map((m) => <option key={m}>{m}</option>)}</select></Field>
              <Button onClick={() => run(() => api("/diary/entries", { body: { product_id: productId, servings: Number(servings) || 1, meal_type: meal, profile_id: activeProfile?.id } }), "Logged in your diary.")}>Log</Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-end gap-2">
              <Field label="Expiry date"><input type="date" className={inputCls} value={expires} onChange={(e) => setExpires(e.target.value)} /></Field>
              <Button onClick={() => run(() => api("/pantry", { body: { product_id: productId, expires_on: expires || null } }), "Added to your pantry.")}>Add to pantry</Button>
            </div>
          )}
          {error ? <div className="mt-3"><ErrorBox error={error} /></div> : null}
        </Card>
      )}
    </>
  );
}

export function ProductDetails({ productId }: { productId: string }) {
  const d = useApi<Details>(`/products/${productId}/details`);
  if (!d.data) return null;
  const x = d.data;
  return (
    <>
      {(x.manufacturer || x.nafdac) && (
        <Card className="text-sm">
          <SectionTitle>Brand &amp; registration</SectionTitle>
          {x.brand && <p><b>Brand:</b> {x.brand}</p>}
          {x.manufacturer && <p><b>Made by:</b> {x.manufacturer.name}{x.manufacturer.parent_company ? ` (part of ${x.manufacturer.parent_company})` : ""}</p>}
          {x.nafdac && (
            <div className="mt-2 rounded-xl bg-surface-2 p-3">
              <p className="flex items-center gap-1.5 font-semibold"><ShieldCheck className="size-4" /> NAFDAC {x.nafdac.number} {!x.nafdac.format_ok && <Badge tone="amber">unusual format</Badge>}</p>
              <p className="mt-1 text-xs text-muted">{x.nafdac.note} <a className="text-brand underline" href={x.nafdac.check_url} target="_blank" rel="noreferrer">NAFDAC Greenbook</a></p>
            </div>
          )}
        </Card>
      )}
      {x.lab_results.length > 0 && (
        <Card className="text-sm">
          <SectionTitle>Lab test results</SectionTitle>
          <ul className="space-y-2">
            {x.lab_results.map((l, i) => (
              <li key={i} className="rounded-xl bg-surface-2 p-3">
                <p className="font-semibold">{l.analyte}: {l.value ?? "not detected"} {l.unit} {l.exceeds_threshold && <Badge tone="red">above limit</Badge>}</p>
                <p className="text-xs text-muted">{l.lab}{l.method ? `, ${l.method}` : ""}{l.batch ? ` · batch ${l.batch}` : ""}{l.tested_on ? ` · ${l.tested_on}` : ""}{l.threshold != null ? ` · limit ${l.threshold} ${l.unit} (${l.threshold_jurisdiction})` : ""}</p>
                <p className="text-xs text-muted">{l.note}</p>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {x.history.length > 0 && (
        <Card className="text-sm">
          <SectionTitle><span className="flex items-center gap-2"><History className="size-4" /> Update history</span></SectionTitle>
          <ul className="space-y-1 text-xs">
            {x.history.slice(0, 6).map((h) => <li key={h.at}>{new Date(h.at).toLocaleDateString("en-US")}: {h.action.replace(".", " ")}{h.fields.length ? ` (${h.fields.join(", ")})` : ""}{h.note ? ` · ${h.note}` : ""}</li>)}
          </ul>
        </Card>
      )}
    </>
  );
}

export function ProductPrices({ productId }: { productId: string }) {
  const { me } = useAuth();
  const p = useApi<Prices>(`/products/${productId}/prices`, [me?.id]);
  const [f, setF] = useState({ price: "", store: "", city: "" });
  const [error, setError] = useState<unknown>(null);
  const [sent, setSent] = useState(false);
  const currency = me?.currency || "USD";
  const country = me?.country || "US";
  if (!p.data) return null;
  return (
    <Card className="text-sm">
      <SectionTitle><span className="flex items-center gap-2"><MapPin className="size-4" /> Prices &amp; where to buy</span></SectionTitle>
      {p.data.reports === 0 ? <p className="text-muted">No prices reported yet.</p> : p.data.locked ? (
        <>
          <p>Seen at {p.data.where_to_buy.map((w) => [w.store, w.city].filter(Boolean).join(", ")).join("; ")}.</p>
          <div className="mt-2"><UpgradeCard title="Compare prices with Plus" error={{ message: `${p.data.reports} price report(s) available.` }} /></div>
        </>
      ) : (
        <ul className="space-y-1">{p.data.by_store!.map((s) => <li key={s.store + s.currency} className="flex justify-between"><span>{s.store}{s.city ? `, ${s.city}` : ""}</span><span className="tabular-nums">{money(s.price, s.currency)}</span></li>)}</ul>
      )}
      <p className="mt-2 text-xs text-muted">{p.data.note}</p>
      {me && !sent && (
        <form className="mt-3 grid grid-cols-2 gap-2" onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            await api(`/products/${productId}/prices`, { body: { price: Number(f.price), currency, store: f.store, city: f.city || null, country } });
            setSent(true);
            p.reload();
          } catch (err) { setError(err); }
        }}>
          <input className={inputCls} inputMode="decimal" required placeholder={`Price (${currency})`} value={f.price} onChange={(e) => setF({ ...f, price: e.target.value })} aria-label="Price" />
          <input className={inputCls} required placeholder="Store" value={f.store} onChange={(e) => setF({ ...f, store: e.target.value })} aria-label="Store" />
          <input className={inputCls} placeholder="City" value={f.city} onChange={(e) => setF({ ...f, city: e.target.value })} aria-label="City" />
          <Button type="submit" variant="secondary">Report price</Button>
        </form>
      )}
      {sent && <p className="mt-2 text-xs text-good">Thanks for reporting a price.</p>}
      {error ? <div className="mt-2"><ErrorBox error={error} /></div> : null}
    </Card>
  );
}

type Reviews = { average: number | null; count: number; reviews: { id: string; rating: number; title: string | null; body: string | null; created_at: string }[] };

export function ProductReviews({ productId }: { productId: string }) {
  const { me } = useAuth();
  const r = useApi<Reviews>(`/products/${productId}/reviews`);
  const [rating, setRating] = useState(0);
  const [text, setText] = useState("");
  const [error, setError] = useState<unknown>(null);
  if (!r.data) return null;
  return (
    <Card className="text-sm">
      <SectionTitle>Community reviews</SectionTitle>
      <p className="text-muted">{r.data.count ? `${r.data.average} / 5 from ${r.data.count} review(s)` : "No reviews yet."} Reviews are opinions and don&apos;t affect the health score.</p>
      <ul className="mt-2 space-y-2">
        {r.data.reviews.slice(0, 5).map((x) => (
          <li key={x.id} className="rounded-xl bg-surface-2 p-2"><span aria-label={`${x.rating} out of 5`}>{"★".repeat(x.rating)}{"☆".repeat(5 - x.rating)}</span>{x.body && <p className="mt-0.5">{x.body}</p>}</li>
        ))}
      </ul>
      {me && (
        <form className="mt-3 space-y-2" onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try { await api(`/products/${productId}/reviews`, { method: "PUT", body: { rating, body: text || null } }); setText(""); r.reload(); } catch (err) { setError(err); }
        }}>
          <div className="flex gap-1" role="radiogroup" aria-label="Your rating">
            {[1, 2, 3, 4, 5].map((n) => <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} className={`text-2xl ${n <= rating ? "text-warn" : "text-muted"}`} onClick={() => setRating(n)}>★</button>)}
          </div>
          <textarea className={`${inputCls} min-h-16 py-2`} placeholder="What did you think? (optional)" maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} aria-label="Your review" />
          <Button type="submit" variant="secondary" disabled={!rating}>Post review</Button>
          {error ? <ErrorBox error={error} /> : null}
        </form>
      )}
    </Card>
  );
}
