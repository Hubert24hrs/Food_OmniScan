"use client";

import { FlaskConical, Info } from "lucide-react";
import { useApi } from "@/lib/useApi";
import { SourceList, type Source } from "@/components/SourceList";
import { Card, ErrorBox, Page, SectionTitle, Skeleton } from "@/components/ui";

type Topic = { slug: string; title: string; summary: string; where_found: string[]; reduce_exposure: string[]; sources: Source[] };
type Resp = { risk_explainer: Record<string, string>; topics: Topic[] };

export default function SafetyPage() {
  const r = useApi<Resp>("/safety/topics");
  return (
    <Page title="Food safety research" subtitle="Contaminants explained by food category, with the evidence behind each statement.">
      {r.error ? <ErrorBox error={r.error} onRetry={r.reload} /> : !r.data ? <Skeleton className="h-60" /> : (
        <div className="space-y-4">
          <Card className="border-brand/30 bg-brand-soft">
            <p className="flex items-center gap-2 font-display font-bold"><Info className="size-5 text-brand" /> Hazard, exposure and risk</p>
            <ul className="mt-2 space-y-1 text-sm">
              {["hazard", "exposure", "risk"].map((k) => <li key={k}>{r.data!.risk_explainer[k]}</li>)}
            </ul>
            <p className="mt-2 text-sm font-semibold">{r.data.risk_explainer.product_rule}</p>
          </Card>
          {r.data.topics.map((t) => (
            <Card key={t.slug} id={t.slug}>
              <SectionTitle><span className="flex items-center gap-2"><FlaskConical className="size-5 text-brand" /> {t.title}</span></SectionTitle>
              <p className="text-sm">{t.summary}</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div><p className="text-sm font-semibold">Where it&apos;s been found (by food type)</p><ul className="mt-1 list-disc pl-5 text-sm">{t.where_found.map((w) => <li key={w}>{w}</li>)}</ul></div>
                <div><p className="text-sm font-semibold">What you can do</p><ul className="mt-1 list-disc pl-5 text-sm">{t.reduce_exposure.map((w) => <li key={w}>{w}</li>)}</ul></div>
              </div>
              <div className="mt-3 border-t border-line pt-3"><SourceList sources={t.sources} /></div>
            </Card>
          ))}
        </div>
      )}
    </Page>
  );
}
