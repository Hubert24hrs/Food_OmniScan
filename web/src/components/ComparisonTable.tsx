import Link from "next/link";
import { Trophy } from "lucide-react";
import { nf } from "@/lib/format";
import type { ProductSummary } from "@/lib/types";
import { ProductThumb } from "./ProductCard";
import { MiniScore, VerdictPill } from "./score";

export type CompareResult = {
  objective_label: string;
  best: { product_id: string; name: string; objective: string } | null;
  products: { product: ProductSummary; additives_of_concern: string[]; allergens_contains: string[]; sugar_is_total: boolean; basis: string; compatibility?: { profile_name: string; verdict: "green" | "yellow" | "red" }[] }[];
  rows: { key: string; label: string; unit: string; values: (number | null)[] }[];
  notes: string[];
  share_token?: string;
};

const LOWER_BETTER = new Set(["nova_group", "energy_kcal", "added_sugars", "saturated_fat", "sodium_mg", "additive_count"]);

export function ComparisonTable({ r }: { r: CompareResult }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-line">
      <table className="w-full min-w-[36rem] text-sm">
        <thead>
          <tr className="bg-surface-2">
            <th className="p-3 text-left font-semibold">Per 100 g / 100 ml</th>
            {r.products.map((p) => (
              <th key={p.product.id} className="p-3 text-left align-top font-semibold">
                <Link href={`/product/${p.product.id}`} className="flex items-center gap-2 hover:text-brand">
                  <ProductThumb src={p.product.image_url} alt="" />
                  <span className="line-clamp-2">{p.product.name}</span>
                </Link>
                {r.best?.product_id === p.product.id && <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-good-soft px-2 py-0.5 text-xs text-good"><Trophy className="size-3" /> {r.objective_label}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {r.rows.map((row) => {
            const vals = row.values.filter((v): v is number => v !== null);
            const best = vals.length ? (LOWER_BETTER.has(row.key) ? Math.min(...vals) : Math.max(...vals)) : null;
            return (
              <tr key={row.key} className="border-t border-line">
                <td className="p-3 font-medium">{row.label}</td>
                {row.values.map((v, i) => (
                  <td key={i} className={`p-3 tabular-nums ${v !== null && v === best && vals.length > 1 ? "font-bold text-good" : ""}`}>
                    {row.key === "score" ? <MiniScore score={v} color={r.products[i].product.color} /> : v === null ? "—" : `${nf(v)}${row.unit}`}
                  </td>
                ))}
              </tr>
            );
          })}
          <tr className="border-t border-line align-top">
            <td className="p-3 font-medium">Additives of concern</td>
            {r.products.map((p) => <td key={p.product.id} className="p-3 text-xs">{p.additives_of_concern.join(", ") || "None"}</td>)}
          </tr>
          <tr className="border-t border-line align-top">
            <td className="p-3 font-medium">Contains allergens</td>
            {r.products.map((p) => <td key={p.product.id} className="p-3 text-xs">{p.allergens_contains.join(", ") || "None detected"}</td>)}
          </tr>
          {r.products[0]?.compatibility?.length ? (
            <tr className="border-t border-line align-top">
              <td className="p-3 font-medium">Your profile</td>
              {r.products.map((p) => <td key={p.product.id} className="p-3">{p.compatibility?.map((c) => <VerdictPill key={c.profile_name} verdict={c.verdict} />)}</td>)}
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
