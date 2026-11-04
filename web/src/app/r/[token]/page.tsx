"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useApi } from "@/lib/useApi";
import type { Analysis, Product } from "@/lib/types";
import { AnalysisView } from "@/components/AnalysisView";
import { NutritionFacts } from "@/components/NutritionFacts";
import { ProductThumb } from "@/components/ProductCard";
import { Card, ErrorBox, LinkButton, Page, SectionTitle, Skeleton } from "@/components/ui";

export default function SharedReportPage() {
  const { token } = useParams<{ token: string }>();
  const r = useApi<{ product: Product; analysis: Analysis }>(`/shared/${token}`);
  if (r.error) return <Page><ErrorBox error={r.error} /></Page>;
  if (!r.data) return <Page><Skeleton className="h-72" /></Page>;
  const p = r.data.product;
  return (
    <Page>
      <p className="mb-3 rounded-xl bg-surface-2 p-3 text-sm">Someone shared this Food omniScan report with you. It doesn&apos;t include their personal allergy or diet checks. <Link href={`/product/${p.id}`} className="font-semibold text-brand underline">Check it against your own profile</Link></p>
      <header className="mb-4 flex items-start gap-4">
        <ProductThumb src={p.image_url} alt={p.name || "Product"} />
        <div><h1 className="font-display text-2xl font-extrabold">{p.name || "Unnamed product"}</h1><p className="text-sm text-muted">{[p.brand, p.quantity].filter(Boolean).join(" · ")}</p></div>
      </header>
      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <AnalysisView analysis={r.data.analysis} />
        <Card><SectionTitle>Nutrition Facts</SectionTitle><NutritionFacts product={p} /></Card>
      </div>
      <LinkButton className="mt-6" href="/scan">Scan your own food</LinkButton>
    </Page>
  );
}
