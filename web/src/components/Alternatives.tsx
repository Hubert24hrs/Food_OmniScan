"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp, Leaf } from "lucide-react";
import { api } from "@/lib/api";
import type { ProductSummary } from "@/lib/types";
import { ProductCard } from "./ProductCard";
import { Badge, Button, Card, EmptyState, ErrorBox, SectionTitle, Skeleton } from "./ui";

type Alt = { product: ProductSummary; score: number; score_delta: number | null; reasons: { better: string[]; not_better: string[]; ingredients_removed: string[] }; compatibility: { verdict: string; profile_name: string }[]; sold_in_country?: boolean };
type Resp = { alternatives: Alt[]; objective_label: string; price_comparison: string };

const OBJECTIVES: [string, string][] = [
  ["overall", "Best overall"], ["lowest_sugar", "Less sugar"], ["lowest_sodium", "Less sodium"], ["lowest_saturated_fat", "Less sat fat"],
  ["highest_protein", "More protein"], ["fewest_additives", "Fewer additives"],
];

export function Alternatives({ productId }: { productId: string }) {
  const [objective, setObjective] = useState("overall");
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const load = async (obj: string) => {
    setObjective(obj);
    setLoading(true);
    setError(null);
    try {
      setData(await api<Resp>(`/products/${productId}/alternatives`, { query: { objective: obj } }));
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <SectionTitle>Healthier alternatives</SectionTitle>
      <div className="mb-3 flex flex-wrap gap-2">
        {OBJECTIVES.map(([k, l]) => (
          <button key={k} onClick={() => load(k)} aria-pressed={data !== null && objective === k} className={`min-h-9 rounded-full border px-3 text-sm font-medium ${data && objective === k ? "border-brand bg-brand-soft text-brand-strong dark:text-brand" : "border-line"}`}>
            {l}
          </button>
        ))}
      </div>
      {!data && !loading && !error && (
        <Button variant="secondary" onClick={() => load("overall")}>
          <Leaf className="size-4" aria-hidden /> Find better options in this category
        </Button>
      )}
      {loading && <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-20" />)}</div>}
      {error ? <ErrorBox error={error} onRetry={() => load(objective)} /> : null}
      {data && !loading && (data.alternatives.length === 0 ? (
        <EmptyState title="No clearly better match found" body="We only suggest products that score meaningfully better and fit your profiles. Try another goal above." />
      ) : (
        <div className="space-y-3">
          {data.alternatives.map((a) => (
            <div key={a.product.id} className="rounded-2xl border border-line p-2">
              <ProductCard p={a.product} right={<span className="flex flex-col items-end gap-1">{a.score_delta !== null && <Badge tone="green">+{a.score_delta}</Badge>}{a.sold_in_country && <Badge tone="brand">Sold in your country</Badge>}</span>} />
              <div className="grid gap-2 p-2 text-sm sm:grid-cols-2">
                <ul className="space-y-0.5">
                  {a.reasons.better.slice(0, 4).map((r) => <li key={r} className="flex gap-1.5 text-good"><ArrowUp className="mt-0.5 size-3.5 shrink-0" />{r}</li>)}
                </ul>
                <ul className="space-y-0.5">
                  {a.reasons.not_better.slice(0, 3).map((r) => <li key={r} className="flex gap-1.5 text-warn"><ArrowDown className="mt-0.5 size-3.5 shrink-0" />{r}</li>)}
                </ul>
              </div>
            </div>
          ))}
          <p className="text-xs text-muted">{data.price_comparison}</p>
        </div>
      ))}
    </Card>
  );
}
