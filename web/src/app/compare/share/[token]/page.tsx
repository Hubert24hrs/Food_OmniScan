"use client";

import { useParams } from "next/navigation";
import { useApi } from "@/lib/useApi";
import { ComparisonTable, type CompareResult } from "@/components/ComparisonTable";
import { ErrorBox, Page, Skeleton } from "@/components/ui";

export default function SharedComparison() {
  const { token } = useParams<{ token: string }>();
  const { data, error } = useApi<CompareResult & { created_at: string }>(`/compare/${token}`);
  return (
    <Page title="Shared comparison" subtitle={data ? `${data.objective_label} · created ${new Date(data.created_at).toLocaleDateString("en-US")}` : undefined}>
      {error ? <ErrorBox error={error} /> : data ? <ComparisonTable r={data} /> : <Skeleton className="h-96" />}
      <p className="mt-3 text-xs text-muted">Scores reflect the methodology at the time of sharing. Personal compatibility isn&apos;t included in shared reports.</p>
    </Page>
  );
}
