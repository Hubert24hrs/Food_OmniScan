"use client";

import type { OcrResult } from "./LabelCapture";
import { Badge } from "./ui";

export function OcrReview({ label, value, onChange, result }: { label: string; value: string; onChange: (v: string) => void; result: OcrResult | null }) {
  return (
    <div className="mt-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold">{label}: check and correct</span>
        {result && <Badge tone={result.confidence > 0.8 ? "green" : result.confidence > 0.55 ? "amber" : "red"}>{Math.round(result.confidence * 100)}% OCR confidence · {result.engine}</Badge>}
      </div>
      <textarea className="min-h-32 w-full rounded-xl border border-line bg-surface p-3 text-sm" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} />
    </div>
  );
}
