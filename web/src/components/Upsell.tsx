"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Crown } from "lucide-react";
import { PAYWALL_EVENT, type PaywallDetail } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";

type Usage = { tier: string; features: Record<string, { kind: string; label: string; limit: number | null; used: number | null }> };

/** Takes people to the plans when an action they started needs a plan or their allowance has run out. */
export function PaywallListener() {
  const router = useRouter();
  useEffect(() => {
    const go = (e: Event) => {
      const d = (e as CustomEvent<PaywallDetail>).detail || {};
      const q = new URLSearchParams();
      if (d.message) q.set("reason", d.message);
      if (d.required_tier) q.set("tier", d.required_tier);
      router.push(`/subscription?${q}`);
    };
    window.addEventListener(PAYWALL_EVENT, go);
    return () => window.removeEventListener(PAYWALL_EVENT, go);
  }, [router]);
  return null;
}

/** Red crown button in the header for anyone not on a paid plan. */
export function UpgradeButton() {
  const { me, loading } = useAuth();
  if (loading || (me && me.tier !== "free")) return null;
  return (
    <Link href="/subscription" className="btn-accent inline-flex min-h-9 items-center gap-1.5 rounded-full px-3 text-sm font-bold">
      <Crown className="size-4 icon-pop" aria-hidden /> <span>Go Premium</span>
    </Link>
  );
}

/** Dashboard card for free users: what Premium adds and the allowance closest to running out. */
export function UpgradeBanner() {
  const { me } = useAuth();
  const usage = useApi<Usage>(me && me.tier === "free" ? "/billing/me" : null);
  if (!me || me.tier !== "free") return null;
  const metered = Object.values(usage.data?.features || {})
    .filter((f) => f.kind === "metered" && typeof f.limit === "number" && f.limit > 0)
    .map((f) => ({ label: f.label, used: f.used || 0, limit: f.limit as number }))
    .sort((a, b) => a.limit - a.used - (b.limit - b.used));
  const a = metered[0];
  return (
    <section className="mt-4 overflow-hidden rounded-2xl bg-accent p-5 text-white shadow-sm">
      <div className="flex flex-wrap items-center gap-3">
        <Crown className="size-7 shrink-0" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-display text-lg font-extrabold">Get more with Premium</p>
          <p className="text-sm text-white/90">AI meal plans, vitamins &amp; reports, pantry, budget and price comparison. Plans from $3.99.</p>
        </div>
        <Link href="/subscription" className="inline-flex min-h-10 items-center rounded-xl bg-white px-4 text-sm font-extrabold text-[#dc2626]">
          See plans
        </Link>
      </div>
      {a && (
        <div className="mt-3">
          <p className="text-xs font-bold">
            {Math.max(0, a.limit - a.used)} of {a.limit} free {/^[A-Z]{2}/.test(a.label) ? a.label : a.label[0].toLowerCase() + a.label.slice(1)} left this month
          </p>
          <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/25">
            <div className="h-full rounded-full bg-white" style={{ width: `${Math.min(100, (a.used / a.limit) * 100)}%` }} />
          </div>
        </div>
      )}
    </section>
  );
}
