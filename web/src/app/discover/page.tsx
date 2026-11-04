"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { BookOpen, Mic, Search } from "lucide-react";
import { api } from "@/lib/api";
import type { ProductSummary } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";
import { Button, EmptyState, ErrorBox, inputCls, Page, Skeleton } from "@/components/ui";

type SR = { start: () => void; stop: () => void; onresult: (e: { results: { 0: { transcript: string } }[] }) => void; onend: () => void; lang: string; interimResults: boolean };

export default function Discover() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ProductSummary[] | null>(null);
  const [ings, setIngs] = useState<{ slug: string; name: string; category: string; concern_level: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [listening, setListening] = useState(false);
  const [voice, setVoice] = useState(false);
  const rec = useRef<SR | null>(null);

  const run = async (term: string) => {
    if (term.trim().length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const [p, i] = await Promise.all([
        api<{ results: ProductSummary[]; remote_error: string | null }>("/products/search", { query: { q: term } }),
        api<{ items: typeof ings }>("/ingredients", { query: { q: term, limit: 5 } }),
      ]);
      setResults(p.results);
      setIngs(i.items);
      if (p.remote_error && !p.results.length) setError(new Error("Online product databases are unavailable right now; showing saved products only."));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  const runRef = useRef(run);
  useEffect(() => {
    runRef.current = run;
  });

  useEffect(() => {
    const W = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    const Ctor = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (Ctor) {
      const r = new Ctor();
      r.lang = "en-US";
      r.interimResults = false;
      r.onresult = (e) => {
        const t = e.results[0][0].transcript;
        setQ(t);
        runRef.current(t);
      };
      r.onend = () => setListening(false);
      rec.current = r;
      Promise.resolve().then(() => setVoice(true));
    }
  }, []);

  return (
    <Page title="Discover" subtitle="Search products by name, brand, category or barcode, or look up any ingredient.">
      <form onSubmit={(e) => { e.preventDefault(); run(q); }} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <input className={`${inputCls} pl-9`} placeholder="e.g. greek yogurt, Cheerios, red 40" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        </div>
        {voice && (
          <Button type="button" variant="secondary" aria-label={listening ? "Stop voice search" : "Voice search"} aria-pressed={listening} onClick={() => { if (listening) rec.current?.stop(); else { rec.current?.start(); setListening(true); } }}>
            <Mic className={`size-4 ${listening ? "text-bad" : ""}`} />
          </Button>
        )}
        <Button type="submit" loading={loading}>Search</Button>
      </form>

      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
      {ings.length > 0 && (
        <div className="mt-5 flex flex-wrap gap-2">
          {ings.map((i) => (
            <Link key={i.slug} href={`/ingredients/${i.slug}`} className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1.5 text-sm hover:border-brand">
              <BookOpen className="size-3.5 text-brand" /> {i.name}
            </Link>
          ))}
        </div>
      )}
      <div className="mt-5 space-y-2">
        {loading && [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}
        {!loading && results?.map((p) => <ProductCard key={p.id} p={p} />)}
        {!loading && results && results.length === 0 && <EmptyState title="No products found" body="Try a different spelling, or scan the barcode instead." />}
      </div>
      <p className="mt-6 text-xs text-muted">Product data from Open Food Facts (ODbL) and USDA FoodData Central.</p>
    </Page>
  );
}
