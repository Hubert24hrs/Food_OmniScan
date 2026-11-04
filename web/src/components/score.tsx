"use client";

import { scoreColorVar } from "@/lib/format";
import type { Color } from "@/lib/types";

export function ScoreRing({ score, color, label, size = 132 }: { score: number | null; color: Color; label: string; size?: number }) {
  const r = 52;
  const c = 2 * Math.PI * r;
  const pct = score === null ? 0 : Math.max(0, Math.min(100, score)) / 100;
  const stroke = scoreColorVar[color] || "var(--grey)";
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }} role="img" aria-label={score === null ? `Score: ${label}` : `Score ${score} out of 100, ${label}`}>
      <svg viewBox="0 0 120 120" width={size} height={size} className="-rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="12" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={stroke} strokeWidth="12" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} style={{ transition: "stroke-dashoffset 900ms cubic-bezier(.34,1.56,.64,1)" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-4xl font-extrabold tabular-nums" style={{ color: stroke }}>
          {score ?? "?"}
        </span>
        <span className="text-xs font-semibold text-muted">{score === null ? "no score" : "/ 100"}</span>
      </div>
    </div>
  );
}

export function MiniScore({ score, color }: { score: number | null; color: Color }) {
  const stroke = scoreColorVar[color] || "var(--grey)";
  return (
    <span className="grid size-11 shrink-0 place-items-center rounded-full border-[3px] font-display text-sm font-extrabold tabular-nums" style={{ borderColor: stroke, color: stroke }} aria-label={score === null ? "No score" : `Score ${score}`}>
      {score ?? "?"}
    </span>
  );
}

const verdictStyle = {
  green: { cls: "bg-good-soft text-good", text: "Fits" },
  yellow: { cls: "bg-warn-soft text-warn", text: "Check" },
  red: { cls: "bg-bad-soft text-bad", text: "Avoid" },
} as const;

export function VerdictPill({ verdict, name }: { verdict: "green" | "yellow" | "red"; name?: string }) {
  const v = verdictStyle[verdict];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-bold ${v.cls}`}>
      <span className="size-2 rounded-full bg-current" aria-hidden />
      {name ? `${name}: ` : ""}
      {v.text}
    </span>
  );
}

export function ComponentBar({ label, score, weight, assessed }: { label: string; score: number | null; weight: number; assessed: boolean }) {
  const color = !assessed || score === null ? "var(--grey)" : score >= 50 ? "var(--good)" : score >= 35 ? "var(--warn)" : "var(--bad)";
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-semibold">
          {label} <span className="font-normal text-muted">· {weight}%</span>
        </span>
        <span className="tabular-nums font-semibold" style={{ color }}>
          {assessed && score !== null ? score : "Not assessed"}
        </span>
      </div>
      <div className="h-2 rounded-full bg-surface-2" aria-hidden>
        <div className="h-2 rounded-full transition-all" style={{ width: `${assessed && score !== null ? score : 0}%`, background: color }} />
      </div>
    </div>
  );
}
