"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { CalendarDays, Check, Crown, Languages, LockKeyhole, Refrigerator, Sparkles, Tag, Users } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { money } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { Badge, Button, Card, ErrorBox, IconTile, Page } from "@/components/ui";

type Plan = { tier: string; monthly_usd: number; annual_usd: number | null; features: string[]; limits: Record<string, number | null>; feature_labels: Record<string, string> };
type Usage = { tier: string; features: Record<string, { kind: string; label: string; limit: number | null; included: boolean; used: number | null }> };
const METERED = new Set(["ai_assistant", "ai_vision", "ai_recipes", "ai_meal_plans", "alternatives", "comparisons"]);
const TIERS = new Set(["plus", "premium", "family"]);

const BENEFITS = [
  { icon: CalendarDays, t: "AI meal plans", b: "Weekly plans with Nigerian, US and European dishes" },
  { icon: Sparkles, t: "Much more AI", b: "Up to 500 questions and 300 photo reads a month" },
  { icon: Check, t: "Vitamins, minerals & reports", b: "Weekly and monthly nutrition reports" },
  { icon: Refrigerator, t: "Pantry & expiry reminders", b: "Use food before it goes off" },
  { icon: Tag, t: "Budget & price comparison", b: "See where it is cheaper" },
  { icon: Languages, t: "Assistant in your language", b: "Pidgin, Yoruba, Igbo, Hausa, French, Spanish" },
  { icon: Users, t: "Family sharing", b: "Shared pantry, lists and budget (Family)" },
];

function cell(feature: string, v: number | null | undefined) {
  if (v === 0) return <span className="text-muted">—</span>;
  if (v === null || v === undefined) return METERED.has(feature) ? "Unlimited" : <Check className="mx-auto size-4 text-good" aria-label="Included" />;
  return METERED.has(feature) ? `${v}/mo` : `${v}`;
}

const cap = (t: string) => t[0].toUpperCase() + t.slice(1);

function Plans() {
  const { me } = useAuth();
  const params = useSearchParams();
  const reason = params.get("reason");
  const wanted = params.get("tier");
  const status = params.get("status");
  const plans = useApi<Plan[]>("/billing/plans");
  const usage = useApi<Usage>(me ? "/billing/me" : null);
  const [interval, setBilling] = useState<"month" | "year">("year");
  const [selected, setSelected] = useState(wanted && TIERS.has(wanted) ? wanted : "premium");
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

  const current = usage.data?.tier || me?.tier || "free";
  const premium = plans.data?.find((p) => p.tier === "premium");
  const saving = premium?.annual_usd ? Math.round((1 - premium.annual_usd / (premium.monthly_usd * 12)) * 100) : 17;

  return (
    <Page>
      <section className="rise overflow-hidden rounded-3xl bg-gradient-to-br from-[#15803d] to-[#16a34a] p-6 text-white sm:p-8">
        <div className="flex items-center justify-between gap-3">
          <Crown className="size-9" aria-hidden />
          <span className="rounded-full bg-white px-3 py-1 text-xs font-extrabold text-[#15803d]">{cap(current)} plan</span>
        </div>
        <h1 className="mt-4 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">Unlock the full Food omniScan</h1>
        <p className="mt-2 max-w-xl text-white/90">Smarter meals, much more AI, and the whole family covered. Scanning, scores, allergen alerts and recalls stay free for everyone.</p>
        {reason && (
          <p role="status" className="mt-4 flex items-start gap-2 rounded-2xl bg-[#fee2e2] p-3 text-sm font-semibold text-[#7f1d1d]">
            <LockKeyhole className="mt-0.5 size-4 shrink-0" aria-hidden /> {reason}
          </p>
        )}
        {status === "success" && <p role="status" className="mt-4 rounded-2xl bg-white/95 p-3 text-sm font-semibold text-[#15803d]">Thank you! Your plan updates within a minute.</p>}
      </section>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {BENEFITS.map((b, i) => (
          <div key={b.t} className="flex gap-3 rounded-2xl border border-line bg-surface p-3">
            <IconTile index={i} size="sm"><b.icon className="size-5" aria-hidden /></IconTile>
            <div>
              <p className="text-sm font-bold">{b.t}</p>
              <p className="text-xs text-muted">{b.b}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 inline-flex rounded-2xl border border-line bg-surface p-1">
        {(["month", "year"] as const).map((i) => (
          <button key={i} onClick={() => setBilling(i)} aria-pressed={interval === i} className={`min-h-10 rounded-xl px-4 text-sm font-semibold ${interval === i ? "btn-brand" : "text-muted"}`}>
            {i === "month" ? "Monthly" : `Yearly · save ${saving}%`}
          </button>
        ))}
      </div>
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
      {plans.error ? <div className="mt-4"><ErrorBox error={plans.error} onRetry={plans.reload} /></div> : null}
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.data?.map((p) => {
          const isCurrent = current === p.tier;
          const yearly = interval === "year" && !!p.annual_usd;
          const price = yearly ? p.annual_usd! : p.monthly_usd;
          const isSelected = selected === p.tier;
          return (
            <Card
              key={p.tier}
              onClick={() => TIERS.has(p.tier) && setSelected(p.tier)}
              className={`flex cursor-pointer flex-col transition-shadow ${isSelected ? "border-brand ring-2 ring-brand/40" : ""}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-display text-lg font-extrabold capitalize">{p.tier}</p>
                {p.tier === "premium" && <Badge tone="tomato">Most popular</Badge>}
                {isCurrent && <Badge tone="green">Your plan</Badge>}
              </div>
              <p className="mt-2 font-display text-3xl font-extrabold">
                {money(price)}
                <span className="text-sm font-semibold text-muted">{p.monthly_usd ? `/${yearly ? "year" : "month"}` : ""}</span>
              </p>
              {yearly && <p className="text-xs font-bold text-brand">{money(price / 12)} a month</p>}
              <ul className="mt-4 flex-1 space-y-2 text-sm">
                {p.features.map((f) => <li key={f} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-good" />{f}</li>)}
              </ul>
              {p.tier !== "free" && !isCurrent && (
                me ? (
                  <Button className={`mt-4 ${isSelected ? "btn-accent" : ""}`} variant={isSelected ? "primary" : "secondary"} loading={busy === p.tier} onClick={() => checkout(p.tier)}>
                    Get {cap(p.tier)}
                  </Button>
                ) : (
                  <Link href="/login?next=/subscription" className="btn-accent mt-4 inline-flex min-h-11 items-center justify-center rounded-xl px-4 text-sm font-bold">
                    Sign in to get {cap(p.tier)}
                  </Link>
                )
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
          <p className="font-display font-bold">Your allowance this month</p>
          <ul className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
            {Object.entries(usage.data.features).filter(([, v]) => v.kind !== "access").map(([k, v]) => {
              const pct = v.included && v.limit ? Math.min(100, ((v.used || 0) / v.limit) * 100) : 0;
              return (
                <li key={k} className="rounded-lg bg-surface-2 px-3 py-2">
                  <span className="flex justify-between gap-3">
                    <span>{v.label}</span>
                    <span className="tabular-nums">{!v.included ? "Not included" : `${v.used !== null ? `${v.used} / ` : ""}${v.limit === null ? "Unlimited" : v.limit}`}</span>
                  </span>
                  {v.kind === "metered" && v.included && v.limit ? (
                    <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-line">
                      <span className={`block h-full rounded-full ${pct >= 80 ? "bg-accent" : "bg-brand"}`} style={{ width: `${pct}%` }} />
                    </span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Card>
      )}
      <p className="mt-4 text-xs text-muted">
        Web payments by Stripe; renews automatically, cancel any time. In the Android and iOS apps, subscriptions use Google Play and the App Store.
        Health scores are never influenced by advertisers or manufacturers. <Link href="/terms" className="underline">Terms</Link> · <Link href="/privacy" className="underline">Privacy</Link>
      </p>
    </Page>
  );
}

export default function SubscriptionPage() {
  return (
    <Suspense fallback={null}>
      <Plans />
    </Suspense>
  );
}
