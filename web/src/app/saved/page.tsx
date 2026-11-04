"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { ProductSummary } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";
import { EmptyState, ErrorBox, Page, Skeleton } from "@/components/ui";

type Fav = { id: string; note: string | null; product: ProductSummary };
const TABS: [string, string][] = [["favourite", "Favorites"], ["trusted", "Trusted"], ["incompatible", "Not for me"]];

export default function SavedPage() {
  const { me } = useRequireAuth();
  const [tab, setTab] = useState("favourite");
  const f = useApi<Fav[]>(me ? `/favourites?list_type=${tab}` : null, [tab]);
  return (
    <Page title="Saved products">
      <div className="mb-4 inline-flex rounded-2xl border border-line bg-surface p-1" role="tablist">
        {TABS.map(([k, l]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`min-h-10 rounded-xl px-4 text-sm font-semibold ${tab === k ? "btn-brand" : "text-muted"}`}>{l}</button>
        ))}
      </div>
      {f.error ? <ErrorBox error={f.error} onRetry={f.reload} /> : null}
      {f.loading && <Skeleton className="h-20" />}
      {f.data?.length === 0 && <EmptyState title="Nothing saved here yet" body="Use Save or Trusted on a product page." />}
      <div className="space-y-2">
        {f.data?.map((x) => (
          <ProductCard key={x.id} p={x.product} sub={x.note || undefined} right={
            <button aria-label="Remove" className="rounded-lg p-2 text-muted hover:text-bad" onClick={async () => { await api(`/favourites/${x.id}`, { method: "DELETE" }); f.reload(); }}>
              <Trash2 className="size-4" />
            </button>
          } />
        ))}
      </div>
    </Page>
  );
}
