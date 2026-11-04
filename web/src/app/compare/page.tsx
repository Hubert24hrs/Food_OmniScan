"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, X } from "lucide-react";
import { api } from "@/lib/api";
import { compareIds, removeFromCompare } from "@/lib/compare";
import { ComparisonTable, type CompareResult } from "@/components/ComparisonTable";
import { Button, EmptyState, ErrorBox, LinkButton, Page, Skeleton } from "@/components/ui";

const OBJ: [string, string][] = [["overall", "Best overall"], ["lowest_sugar", "Lowest sugar"], ["lowest_sodium", "Lowest sodium"], ["lowest_saturated_fat", "Lowest sat fat"], ["highest_protein", "Highest protein"], ["highest_fiber", "Highest fiber"], ["lowest_calories", "Fewest calories"], ["fewest_additives", "Fewest additives"]];

export default function ComparePage() {
  const [ids, setIds] = useState<string[]>([]);
  const [objective, setObjective] = useState("overall");
  const [r, setR] = useState<CompareResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    Promise.resolve().then(() => setIds(compareIds()));
  }, []);
  const run = useCallback(async () => {
    if (ids.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      setR(await api<CompareResult>("/compare", { body: { product_ids: ids, objective } }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [ids, objective]);
  useEffect(() => {
    Promise.resolve().then(run);
  }, [run]);

  if (ids.length < 2)
    return <Page title="Compare"><EmptyState title="Pick at least two products" body="Tap “Compare” on any product page to add it here (up to 6)." action={<LinkButton href="/scan">Scan a product</LinkButton>} /></Page>;

  return (
    <Page title="Compare" actions={r?.share_token ? (
      <Button variant="secondary" onClick={async () => { await navigator.clipboard.writeText(`${location.origin}/compare/share/${r.share_token}`); setCopied(true); }}>
        <Copy className="size-4" /> {copied ? "Link copied" : "Share report"}
      </Button>
    ) : null}>
      <div className="mb-4 flex flex-wrap gap-2">
        {OBJ.map(([k, l]) => (
          <button key={k} onClick={() => setObjective(k)} aria-pressed={objective === k} className={`min-h-9 rounded-full border px-3 text-sm ${objective === k ? "border-brand bg-brand-soft font-semibold" : "border-line"}`}>{l}</button>
        ))}
      </div>
      {error ? <ErrorBox error={error} onRetry={run} /> : null}
      {loading && !r ? <Skeleton className="h-96" /> : r && <ComparisonTable r={r} />}
      <div className="mt-3 flex flex-wrap gap-2">
        {r?.products.map((p) => (
          <button key={p.product.id} onClick={() => { removeFromCompare(p.product.id); setIds(compareIds()); }} className="inline-flex items-center gap-1 rounded-full bg-surface-2 px-3 py-1 text-xs">
            <X className="size-3" /> Remove {p.product.name}
          </button>
        ))}
      </div>
      {r?.notes.map((n) => <p key={n} className="mt-2 text-xs text-muted">{n}</p>)}
    </Page>
  );
}
