"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { Badge, Button, Card, ErrorBox, Page } from "@/components/ui";

type Plan = { tier: string; monthly_usd: number; annual_usd: number | null; features: string[]; limits: Record<string, number | null>; feature_labels: Record<string, string> };
type Usage = { tier: string; features: Record<string, { kind: string; label: string; limit: number | null; included: boolean; used: number | null }> };
const METERED = new Set(["ai_assistant", "ai_vision", "ai_recipes", "ai_meal_plans", "alternatives", "comparisons"]);

function cell(feature: string, v: number | null | undefined) {
  if (v === 0) return <span className="text-muted">—</span>;
  if (v === null || v === undefined) return METERED.has(feature) ? "Unlimited" : <Check className="mx-auto size-4 text-good" aria-label="Included" />;
  return METERED.has(feature) ? `${v}/mo` : `${v}`;
}

export default function SubscriptionPage() {
  const { me } = useAuth();
  const plans = useApi<Plan[]>("/billing/plans");
  const usage = useApi<Usage>(me ? "/billing/me" : null);
  const [interval, setBilling] = useState<"month" | "year">("month");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const checkout = async (tier: string) => {
    setBusy(tier);
    setError(null);
    try {
      const r = await api<{ url: string }>("/billing/checkout", { body: { tier, interval } });
      window.location.assign(r.url);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  return (
    <Page title="Plans" subtitle="Scanning, scores, allergen alerts and food-safety information are free forever. Upgrade for AI, tracking, planning and family features.">
      <div className="mb-4 inline-flex rounded-2xl border border-line bg-surface p-1">
        {(["month", "year"] as const).map((i) => (
          <button key={i} onClick={() => setBilling(i)} aria-pressed={interval === i} className={`min-h-10 rounded-xl px-4 text-sm font-semibold ${interval === i ? "btn-brand" : "text-muted"}`}>
            {i === "month" ? "Monthly" : "Annual (save ~17%)"}
          </button>
        ))}
      </div>
      {error ? <div className="mb-4"><ErrorBox error={error} /></div> : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.data?.map((p) => {
          const current = usage.data?.tier === p.tier;
          const price = interval === "year" && p.annual_usd ? p.annual_usd : p.monthly_usd;
          return (
            <Card key={p.tier} className={`flex flex-col ${p.tier === "premium" ? "border-brand ring-2 ring-brand/30" : ""}`}>
              <div className="flex items-center justify-between">
                <p className="font-display text-lg font-extrabold capitalize">{p.tier}</p>
                {p.tier === "premium" && <Badge tone="brand">Most popular</Badge>}
                {current && <Badge tone="green">Current</Badge>}
              </div>
              <p className="mt-2 font-display text-3xl font-extrabold">{money(price)}<span className="text-sm font-semibold text-muted">{p.monthly_usd ? `/${interval === "year" ? "yr" : "mo"}` : ""}</span></p>
              <ul className="mt-4 flex-1 space-y-2 text-sm">
                {p.features.map((f) => <li key={f} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-good" />{f}</li>)}
              </ul>
              {p.tier !== "free" && !current && (
                <Button className="mt-4" loading={busy === p.tier} disabled={!me} onClick={() => checkout(p.tier)}>
                  {me ? `Choose ${p.tier}` : "Sign in to upgrade"}
                </Button>
              )}
            </Card>
          );
        })}
      </div>
      {plans.data && plans.data[0]?.feature_labels && (
        <Card className="mt-6 overflow-x-auto">
          <p className="mb-2 font-display font-bold">Compare plans</p>
          <table className="w-full min-w-[36rem] text-sm">
            <thead><tr className="text-left text-xs text-muted"><th className="py-2">Feature</th>{plans.data.map((p) => <th key={p.tier} className="px-2 text-center capitalize">{p.tier}</th>)}</tr></thead>
            <tbody>
              <tr className="border-t border-line"><td className="py-2">Scans, scores, allergen alerts, recalls, food-safety research</td>{plans.data.map((p) => <td key={p.tier} className="text-center"><Check className="mx-auto size-4 text-good" aria-label="Included" /></td>)}</tr>
              {Object.entries(plans.data[0].feature_labels).map(([f, label]) => (
                <tr key={f} className="border-t border-line"><td className="py-2">{label}</td>{plans.data!.map((p) => <td key={p.tier} className="px-2 text-center tabular-nums">{cell(f, p.limits[f])}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      {usage.data && (
        <Card className="mt-6">
          <p className="font-display font-bold">This month&apos;s usage</p>
          <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
            {Object.entries(usage.data.features).filter(([, v]) => v.kind !== "access").map(([k, v]) => (
              <li key={k} className="flex justify-between gap-3 rounded-lg bg-surface-2 px-3 py-1.5">
                <span>{v.label}</span>
                <span className="tabular-nums">{!v.included ? "Not included" : `${v.used !== null ? `${v.used} / ` : ""}${v.limit === null ? "Unlimited" : v.limit}`}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <p className="mt-4 text-xs text-muted">Web payments by Stripe. In the iOS and Android apps, subscriptions use the App Store and Google Play. Health scores are never influenced by advertisers or manufacturers.</p>
    </Page>
  );
}
