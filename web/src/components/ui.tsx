"use client";

import Link from "next/link";
import { AlertTriangle, Inbox, Loader2, Lock } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
const variants: Record<Variant, string> = {
  primary: "btn-brand ",
  secondary: "bg-surface border border-line text-ink hover:border-brand hover:text-brand",
  ghost: "text-ink hover:bg-surface-2",
  danger: "bg-bad text-white hover:opacity-90",
};
const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-4 min-h-11 text-sm font-semibold transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0";

export function Button({ variant = "primary", loading, children, className = "", ...p }: ComponentProps<"button"> & { variant?: Variant; loading?: boolean }) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} disabled={loading || p.disabled} {...p}>
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}

export function LinkButton({ variant = "primary", className = "", ...p }: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={`${base} ${variants[variant]} ${className}`} {...p} />;
}

export function Card({ className = "", ...p }: ComponentProps<"div">) {
  return <div className={`card p-4 sm:p-5 ${className}`} {...p} />;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="font-display text-lg font-bold tracking-tight">{children}</h2>
      {action}
    </div>
  );
}

const tones = {
  green: "bg-good-soft text-good",
  lime: "bg-ok-soft text-ok",
  amber: "bg-warn-soft text-warn",
  red: "bg-bad-soft text-bad",
  grey: "bg-grey-soft text-grey",
  brand: "bg-brand-soft text-brand-strong dark:text-brand",
  tomato: "bg-accent-soft text-accent",
  orange: "bg-orange-soft text-orange",
  sun: "bg-sun-soft text-[#a16207] dark:text-sun",
};
export function Badge({ tone = "grey", children, className = "" }: { tone?: keyof typeof tones; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]} ${className}`}>{children}</span>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-muted" role="status">
      <Loader2 className="size-5 animate-spin" aria-hidden /> {label}…
    </div>
  );
}

export function EmptyState({ title, body, action, icon }: { title: string; body?: string; action?: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-line px-6 py-12 text-center">
      <div className="icon-float rounded-full bg-brand-soft p-3 text-brand">{icon || <Inbox className="size-6" aria-hidden />}</div>
      <p className="font-display text-base font-bold">{title}</p>
      {body && <p className="max-w-sm text-sm text-muted">{body}</p>}
      {action}
    </div>
  );
}

type PlanDetail = { code?: string; required_tier?: string | null; message?: string };

/** True when the API says the feature needs a paid plan or the monthly allowance is used up. */
export function isPlanError(error: unknown): boolean {
  const code = (error as { code?: string })?.code;
  return code === "upgrade_required" || code === "quota_exceeded" || code === "plan_limit";
}

export function UpgradeCard({ error, title }: { error?: unknown; title?: string }) {
  const d = ((error as { detail?: PlanDetail })?.detail || {}) as PlanDetail;
  const tier = d.required_tier;
  return (
    <div role="status" className="flex items-start gap-3 rounded-2xl border border-brand/30 bg-brand-soft p-4 text-sm">
      <Lock className="mt-0.5 size-5 shrink-0 text-brand" aria-hidden />
      <div className="flex-1">
        <p className="font-semibold">{title || (tier ? `Included with ${tier[0].toUpperCase() + tier.slice(1)}` : "Plan limit reached")}</p>
        <p className="mt-0.5 text-muted">{(error as Error)?.message || d.message}</p>
      </div>
      <Link href="/subscription" className="rounded-lg px-3 py-1 font-semibold text-brand underline">See plans</Link>
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  if (isPlanError(error)) return <UpgradeCard error={error} />;
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-bad/30 bg-bad-soft p-4 text-sm text-bad">
      <AlertTriangle className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div className="flex-1">
        <p className="font-semibold">Something went wrong</p>
        <p className="mt-0.5 opacity-90">{msg}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="rounded-lg px-3 py-1 font-semibold underline">
          Retry
        </button>
      )}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-muted">{hint}</span>}
    </label>
  );
}

export const inputCls =
  "w-full rounded-xl border border-line bg-surface px-3 min-h-11 text-sm text-ink placeholder:text-muted transition-colors focus:shadow-glow";

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`min-h-10 rounded-full border px-3.5 text-sm font-medium transition-all ${active ? "border-transparent btn-brand" : "border-line bg-surface text-ink hover:border-brand hover:text-brand"}`}
    >
      {children}
    </button>
  );
}

export function Page({ title, subtitle, children, actions }: { title?: string; subtitle?: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-28 pt-5 sm:pt-8 lg:pb-12">
      {title && (
        <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-display text-2xl font-extrabold tracking-tight sm:text-3xl">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </div>
  );
}

// Fresh, flat tile colours (soft background + strong icon colour), cycled so neighbours differ.
const TILE_COLOURS = [
  "bg-brand-soft text-brand",
  "bg-accent-soft text-accent",
  "bg-orange-soft text-orange",
  "bg-sun-soft text-[#a16207] dark:text-sun",
  "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  "bg-pink-100 text-pink-700 dark:bg-pink-950 dark:text-pink-300",
];

/** Colourful tile for an icon; `index` picks the colour so neighbouring tiles differ. */
export function IconTile({ index = 0, size = "md", children }: { index?: number; size?: "sm" | "md" | "lg"; children: ReactNode }) {
  const dim = size === "sm" ? "size-9 rounded-lg" : size === "lg" ? "size-14 rounded-2xl" : "size-11 rounded-xl";
  return (
    <span className={`icon-float grid shrink-0 place-items-center ${dim} ${TILE_COLOURS[index % TILE_COLOURS.length]}`} style={{ animationDelay: `${-index * 0.7}s` }}>
      {children}
    </span>
  );
}
