"use client";

import Link from "next/link";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-strong dark:text-[#06201d]",
  secondary: "bg-surface border border-line text-ink hover:bg-surface-2",
  ghost: "text-ink hover:bg-surface-2",
  danger: "bg-bad text-white hover:opacity-90",
};
const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-4 min-h-11 text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed";

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
      <div className="rounded-full bg-surface-2 p-3 text-muted">{icon || <Inbox className="size-6" aria-hidden />}</div>
      <p className="font-display text-base font-bold">{title}</p>
      {body && <p className="max-w-sm text-sm text-muted">{body}</p>}
      {action}
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
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
  "w-full rounded-xl border border-line bg-surface px-3 min-h-11 text-sm text-ink placeholder:text-muted";

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`min-h-10 rounded-full border px-3.5 text-sm font-medium transition ${active ? "border-brand bg-brand-soft text-brand-strong dark:text-brand" : "border-line bg-surface text-ink hover:bg-surface-2"}`}
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
