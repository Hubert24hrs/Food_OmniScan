"use client";

import { useParams } from "next/navigation";
import { useApi } from "@/lib/useApi";
import { Badge, Card, ErrorBox, Page, SectionTitle, Skeleton } from "@/components/ui";

type Src = { key: string; title: string; publisher: string | null; year: number | null; url: string | null; evidence_quality: string; source_type: string; summary: string | null; verified: boolean };
type Ing = {
  slug: string; name: string; international_name: string; category: string; function: string | null; plain_language: string | null;
  concern_level: string; concern_summary: string | null; e_number: string | null; vegan: string; vegetarian: string; halal_concern: string;
  allergen: string | null; fodmap: string | null; flags: string[]; regulatory_notes: { jurisdiction: string; note: string }[]; synonyms: string[];
  verification_status: string; sources: Src[];
};
const TONE = { beneficial: "green", neutral: "grey", caution: "amber", concern: "red", unknown: "grey" } as const;
const yn = (v: string) => (v === "yes" ? "Yes" : v === "no" ? "No" : "Depends on source");

export default function IngredientPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: i, error } = useApi<Ing>(`/ingredients/${slug}`);
  if (error) return <Page><ErrorBox error={error} /></Page>;
  if (!i) return <Page><Skeleton className="h-64" /></Page>;
  return (
    <Page>
      <header className="mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="font-display text-3xl font-extrabold">{i.name}</h1>
          <Badge tone={TONE[i.concern_level as keyof typeof TONE] || "grey"}>{i.concern_level}</Badge>
        </div>
        <p className="mt-1 text-muted">{[i.international_name !== i.name ? i.international_name : null, i.e_number, i.category.replace(/_/g, " ")].filter(Boolean).join(" · ")}</p>
      </header>
      <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
        <div className="space-y-4">
          <Card>
            <SectionTitle>What it is</SectionTitle>
            <p><b>Why it&apos;s used:</b> {i.function || "Not documented yet."}</p>
            {i.plain_language && <p className="mt-2">{i.plain_language}</p>}
            {i.concern_summary && <p className={`mt-3 rounded-xl p-3 text-sm ${i.concern_level === "concern" ? "bg-bad-soft text-bad" : i.concern_level === "caution" ? "bg-warn-soft text-warn" : "bg-surface-2"}`}>{i.concern_summary}</p>}
          </Card>
          {i.regulatory_notes.length > 0 && (
            <Card>
              <SectionTitle>Regulatory status</SectionTitle>
              <ul className="space-y-2 text-sm">
                {i.regulatory_notes.map((n, k) => <li key={k}><Badge tone="brand">{n.jurisdiction}</Badge> {n.note}</li>)}
              </ul>
            </Card>
          )}
          <Card>
            <SectionTitle>Sources & evidence</SectionTitle>
            {i.sources.length === 0 ? <p className="text-sm text-muted">No sources cited for this entry yet.</p> : (
              <ul className="space-y-3 text-sm">
                {i.sources.map((s) => (
                  <li key={s.key} id={s.key}>
                    <p className="font-semibold">{s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="text-brand underline">{s.title}</a> : s.title}</p>
                    <p className="text-muted">{[s.publisher, s.year].filter(Boolean).join(", ")}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Badge tone="grey">{s.source_type.replace(/_/g, " ")}</Badge>
                      <Badge tone={s.evidence_quality === "high" ? "green" : s.evidence_quality === "moderate" ? "brand" : "amber"}>{s.evidence_quality} evidence</Badge>
                      {!s.verified && <Badge tone="amber">pending editorial check</Badge>}
                    </div>
                    {s.summary && <p className="mt-1">{s.summary}</p>}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
        <div className="space-y-4">
          <Card className="text-sm">
            <SectionTitle>Diet suitability</SectionTitle>
            <dl className="grid grid-cols-2 gap-y-1.5">
              <dt className="text-muted">Vegan</dt><dd>{yn(i.vegan)}</dd>
              <dt className="text-muted">Vegetarian</dt><dd>{yn(i.vegetarian)}</dd>
              <dt className="text-muted">Halal</dt><dd>{i.halal_concern === "no" ? "No known concern" : i.halal_concern === "yes" ? "Not halal" : "Depends on source"}</dd>
              <dt className="text-muted">Allergen</dt><dd>{i.allergen || "None"}</dd>
              <dt className="text-muted">FODMAP</dt><dd>{i.fodmap || "Not classified"}</dd>
            </dl>
          </Card>
          {i.synonyms.length > 0 && (
            <Card className="text-sm">
              <SectionTitle>Also listed as</SectionTitle>
              <p className="text-muted">{i.synonyms.join(", ")}</p>
            </Card>
          )}
          <p className="text-xs text-muted">Entry status: {i.verification_status === "verified" ? "verified by our editorial team" : "seeded from regulatory sources, pending editorial verification"}.</p>
        </div>
      </div>
    </Page>
  );
}
