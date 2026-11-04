"use client";

import Link from "next/link";
import { useState } from "react";
import { Search } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { Badge, ErrorBox, inputCls, Page, Skeleton } from "@/components/ui";

type Item = { slug: string; name: string; category: string; concern_level: string; e_number: string | null; function: string | null };
const TONE = { beneficial: "green", neutral: "grey", caution: "amber", concern: "red", unknown: "grey" } as const;

export default function IngredientsPage() {
  const [q, setQ] = useState("");
  const [concern, setConcern] = useState("");
  const [category, setCategory] = useState("");
  const path = `/ingredients?limit=200${q.length > 1 ? `&q=${encodeURIComponent(q)}` : ""}${concern ? `&concern=${concern}` : ""}${category ? `&category=${category}` : ""}`;
  const r = useApi<{ items: Item[]; categories: string[] }>(path, [path]);
  return (
    <Page title="Ingredient encyclopedia" subtitle="What each ingredient is, why it's used and what regulators say. US names first, with E-numbers.">
      <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
          <input className={`${inputCls} pl-9`} placeholder="Search: Red 40, E471, carrageenan, egusi…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search ingredients" />
        </div>
        <select className={inputCls} value={concern} onChange={(e) => setConcern(e.target.value)} aria-label="Concern level">
          <option value="">All concern levels</option>
          {Object.keys(TONE).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className={inputCls} value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {r.data?.categories.map((c) => <option key={c} value={c}>{c.replace(/_/g, " ")}</option>)}
        </select>
      </div>
      {r.error ? <ErrorBox error={r.error} /> : null}
      {r.loading && !r.data && <Skeleton className="h-64" />}
      <ul className="grid gap-2 sm:grid-cols-2">
        {r.data?.items.map((i) => (
          <li key={i.slug}>
            <Link href={`/ingredients/${i.slug}`} className="card flex items-center justify-between gap-3 p-3 hover:border-brand/50">
              <span className="min-w-0">
                <span className="block truncate font-semibold">{i.name}</span>
                <span className="block truncate text-xs text-muted">{[i.e_number, i.category.replace(/_/g, " "), i.function].filter(Boolean).join(" · ")}</span>
              </span>
              <Badge tone={TONE[i.concern_level as keyof typeof TONE] || "grey"}>{i.concern_level}</Badge>
            </Link>
          </li>
        ))}
      </ul>
    </Page>
  );
}
