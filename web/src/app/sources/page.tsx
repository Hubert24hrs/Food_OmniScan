"use client";

import { useApi } from "@/lib/useApi";
import { Badge, Card, ErrorBox, Page, Skeleton } from "@/components/ui";

type Src = { key: string; title: string; authors: string | null; publisher: string | null; year: number | null; url: string | null; doi: string | null; source_type: string; evidence_quality: string; summary: string | null; verified: boolean };

export default function SourcesPage() {
  const { data, error } = useApi<Src[]>("/sources");
  return (
    <Page title="Research & regulatory sources" subtitle="Every score deduction cites one of these. We list regulations, agency opinions and peer-reviewed studies, and label evidence quality honestly.">
      {error ? <ErrorBox error={error} /> : null}
      {!data && !error && <Skeleton className="h-64" />}
      <div className="space-y-3">
        {data?.map((s) => (
          <Card key={s.key} id={s.key} className="scroll-mt-24 text-sm">
            <p className="font-semibold">{s.url ? <a href={s.url} target="_blank" rel="noreferrer" className="text-brand underline">{s.title}</a> : s.title}</p>
            <p className="text-muted">{[s.authors, s.publisher, s.year, s.doi ? `doi:${s.doi}` : null].filter(Boolean).join(" · ")}</p>
            <div className="mt-1 flex flex-wrap gap-1">
              <Badge tone="grey">{s.key}</Badge>
              <Badge tone="grey">{s.source_type.replace(/_/g, " ")}</Badge>
              <Badge tone={s.evidence_quality === "high" ? "green" : s.evidence_quality === "moderate" ? "brand" : "amber"}>{s.evidence_quality} evidence</Badge>
              {!s.verified && <Badge tone="amber">pending editorial check</Badge>}
            </div>
            {s.summary && <p className="mt-2">{s.summary}</p>}
          </Card>
        ))}
      </div>
    </Page>
  );
}
