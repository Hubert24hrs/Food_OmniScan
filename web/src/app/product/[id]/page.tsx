"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Flag, GitCompare, Heart, ListPlus, ShieldCheck, Sparkles, Star } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { cachedProduct, cacheProduct } from "@/lib/offline";
import { addToCompare } from "@/lib/compare";
import { prettyTag } from "@/lib/format";
import type { Analysis, Product } from "@/lib/types";
import { AnalysisView } from "@/components/AnalysisView";
import { NutritionFacts } from "@/components/NutritionFacts";
import { ProductThumb } from "@/components/ProductCard";
import { Alternatives } from "@/components/Alternatives";
import { Badge, Button, Card, ErrorBox, Page, SectionTitle, Skeleton } from "@/components/ui";

type Resp = { product: Product; analysis: Analysis };

export default function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const [data, setData] = useState<Resp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [offlineCopy, setOfflineCopy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    const pre = sessionStorage.getItem(`omniscan.p.${id}`);
    if (pre) {
      setData(JSON.parse(pre));
      sessionStorage.removeItem(`omniscan.p.${id}`);
      return;
    }
    try {
      const r = await api<Resp>(`/products/${id}`);
      setData(r);
      cacheProduct(id, r);
    } catch (e) {
      const c = cachedProduct<Resp>(id);
      if (c && (e as ApiError).status === 0) {
        setData(c);
        setOfflineCopy(true);
      } else setError(e);
    }
  }, [id]);

  useEffect(() => {
    Promise.resolve().then(load);
  }, [load]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    if (!me) return setMsg("Sign in to save products.");
    try {
      await fn();
      setMsg(ok);
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  if (error) return <Page><ErrorBox error={error} onRetry={load} /></Page>;
  if (!data) return <Page><Skeleton className="h-28" /><Skeleton className="mt-4 h-72" /><Skeleton className="mt-4 h-52" /></Page>;
  const p = data.product;

  return (
    <Page>
      {offlineCopy && <p className="mb-3 rounded-xl bg-warn-soft p-3 text-sm text-warn">Showing a saved offline copy.</p>}
      <header className="mb-4 flex items-start gap-4">
        <ProductThumb src={p.image_url} alt={p.name || "Product"} />
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-2xl font-extrabold leading-tight">{p.name || "Unnamed product"}</h1>
          <p className="text-sm text-muted">{[p.brand, p.quantity, p.category || prettyTag(p.categories.at(-1))].filter(Boolean).join(" · ")}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {p.barcodes.map((b) => <Badge key={b.barcode} tone="grey">{b.format} {b.barcode}</Badge>)}
            {p.provenance.verified_at && <Badge tone="green"><ShieldCheck className="size-3.5" /> Verified</Badge>}
          </div>
        </div>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => act(() => api("/favourites", { body: { product_id: p.id } }), "Saved to favorites")}>
          <Heart className="size-4" aria-hidden /> Save
        </Button>
        <Button variant="secondary" onClick={() => act(() => api("/favourites", { body: { product_id: p.id, list_type: "trusted" } }), "Marked as trusted")}>
          <Star className="size-4" aria-hidden /> Trusted
        </Button>
        <Button variant="secondary" onClick={() => act(async () => {
          const lists = await api<{ id: string }[]>("/shopping-lists");
          const lid = lists[0]?.id || (await api<{ id: string }>("/shopping-lists", { body: { name: "Groceries" } })).id;
          await api(`/shopping-lists/${lid}/items`, { body: { product_id: p.id } });
        }, "Added to your shopping list")}>
          <ListPlus className="size-4" aria-hidden /> Add to list
        </Button>
        <Button variant="secondary" onClick={() => { addToCompare(p.id); setMsg("Added to comparison. Open Compare to view."); }}>
          <GitCompare className="size-4" aria-hidden /> Compare
        </Button>
        <Link href={`/assistant?product=${p.id}`} className="inline-flex min-h-11 items-center gap-2 rounded-xl px-3 text-sm font-semibold text-brand">
          <Sparkles className="size-4" aria-hidden /> Ask AI
        </Link>
      </div>
      {msg && <p className="mb-4 rounded-xl bg-surface-2 p-3 text-sm" role="status">{msg}</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <AnalysisView analysis={data.analysis} />
        <aside className="space-y-4">
          <Card>
            <SectionTitle>Nutrition Facts</SectionTitle>
            <NutritionFacts product={p} />
          </Card>
          <Card className="text-sm">
            <SectionTitle>Data sources</SectionTitle>
            <p>{p.provenance.attribution || `Source: ${p.provenance.source}`}</p>
            {p.provenance.source_url && <a className="mt-1 block text-brand underline" href={p.provenance.source_url} target="_blank" rel="noreferrer">View source record</a>}
            <p className="mt-2 text-xs text-muted">License: {p.provenance.license || "n/a"}. Last updated {p.provenance.last_synced_at ? new Date(p.provenance.last_synced_at).toLocaleDateString("en-US") : "n/a"}. Completeness {Math.round(p.completeness * 100)}%.</p>
            {Object.keys(p.provenance.fields || {}).length > 0 && (
              <p className="mt-1 text-xs text-muted">Fields: {Object.entries(p.provenance.fields).map(([k, v]) => `${k} (${v})`).join(", ")}</p>
            )}
            {p.packaging && <p className="mt-2 text-xs"><b>Packaging:</b> {p.packaging}</p>}
            <Link href={`/report/${p.id}`} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-muted hover:text-ink">
              <Flag className="size-3.5" /> Report incorrect information
            </Link>
          </Card>
        </aside>
      </div>

      <div className="mt-6">
        <Alternatives productId={p.id} />
      </div>
    </Page>
  );
}
