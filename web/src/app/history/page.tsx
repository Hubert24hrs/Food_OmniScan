"use client";

import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import type { ProductSummary } from "@/lib/types";
import { ProductCard } from "@/components/ProductCard";
import { EmptyState, ErrorBox, LinkButton, Page, Skeleton } from "@/components/ui";

type Hist = { id: string; product: ProductSummary; last_scanned_at: string; scan_count: number };

export default function HistoryPage() {
  const { me } = useRequireAuth();
  const h = useApi<Hist[]>(me ? "/history?limit=200" : null);
  return (
    <Page title="Scan history" subtitle="Every product you've scanned, newest first.">
      {h.error ? <ErrorBox error={h.error} onRetry={h.reload} /> : null}
      {h.loading && <div className="space-y-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)}</div>}
      {h.data?.length === 0 && <EmptyState title="No scans yet" action={<LinkButton href="/scan">Start scanning</LinkButton>} />}
      <div className="space-y-2">
        {h.data?.map((x) => (
          <ProductCard
            key={x.id}
            p={x.product}
            sub={`${dateTime(x.last_scanned_at)}${x.scan_count > 1 ? ` · ${x.scan_count}×` : ""}`}
            right={
              <button aria-label={`Remove ${x.product.name} from history`} className="rounded-lg p-2 text-muted hover:text-bad" onClick={async () => { await api(`/history/${x.id}`, { method: "DELETE" }); h.setData(h.data!.filter((y) => y.id !== x.id)); }}>
                <Trash2 className="size-4" />
              </button>
            }
          />
        ))}
      </div>
    </Page>
  );
}
