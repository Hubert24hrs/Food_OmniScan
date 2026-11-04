"use client";

import Link from "next/link";
import { useState } from "react";
import { Trophy } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { ProductThumb } from "@/components/ProductCard";
import { MiniScore } from "@/components/score";
import type { Color } from "@/lib/types";
import { Badge, EmptyState, ErrorBox, inputCls, Page, Skeleton, UpgradeCard } from "@/components/ui";

type Cat = { code: string; name: string; products: number };
type Row = { id: string; name: string | null; brand: string | null; image_url: string | null; score: number; color: Color; rank: number };
type Ranking = { total: number; results: Row[]; locked: boolean; criteria: string; methodology_version: string };

export default function RankingsPage() {
  const cats = useApi<Cat[]>("/categories");
  const [cat, setCat] = useState("");
  const [country, setCountry] = useState("");
  const code = cat || cats.data?.[0]?.code || "";
  const r = useApi<Ranking>(code ? `/rankings?category=${encodeURIComponent(code)}${country ? `&country=${country}` : ""}` : null, [code, country]);

  return (
    <Page title="Category rankings" subtitle="Products ranked by their overall health score. Products without enough data aren't ranked.">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <select className={inputCls} value={code} onChange={(e) => setCat(e.target.value)} aria-label="Category">
          {cats.data?.map((c) => <option key={c.code} value={c.code}>{c.name} ({c.products})</option>)}
        </select>
        <select className={`${inputCls} sm:w-48`} value={country} onChange={(e) => setCountry(e.target.value)} aria-label="Country">
          <option value="">All countries</option><option value="US">United States</option><option value="NG">Nigeria</option><option value="GB">United Kingdom</option><option value="FR">France</option>
        </select>
      </div>
      {cats.error || r.error ? <ErrorBox error={cats.error || r.error} /> : null}
      {cats.data && cats.data.length === 0 && <EmptyState title="No categories yet" body="Rankings appear as products are scanned and added." />}
      {code && !r.data ? <Skeleton className="h-60" /> : r.data && (
        <>
          <p className="mb-3 text-xs text-muted">{r.data.criteria} Methodology {r.data.methodology_version}.</p>
          {r.data.results.length === 0 ? <EmptyState title="No ranked products" body="None of these products have enough data to score yet." /> : (
            <ol className="space-y-2">
              {r.data.results.map((p) => (
                <li key={p.id}>
                  <Link href={`/product/${p.id}`} className="card flex items-center gap-3 p-3 hover:border-brand">
                    <span className="w-8 text-center font-display text-lg font-extrabold text-muted">{p.rank === 1 ? <Trophy className="mx-auto size-5 text-warn" aria-label="Best in category" /> : p.rank}</span>
                    <ProductThumb src={p.image_url} alt={p.name || "Product"} />
                    <span className="min-w-0 flex-1"><span className="block truncate font-semibold">{p.name || "Unnamed"}</span><span className="text-sm text-muted">{p.brand}</span></span>
                    {p.rank === 1 && <Badge tone="green">Best in category</Badge>}
                    <MiniScore score={p.score} color={p.color} />
                  </Link>
                </li>
              ))}
            </ol>
          )}
          {r.data.locked && <div className="mt-4"><UpgradeCard title={`Showing the top ${r.data.results.length} of ${r.data.total}`} error={{ message: "Full rankings are included with Plus." }} /></div>}
        </>
      )}
    </Page>
  );
}
