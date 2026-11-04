"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertOctagon, ChevronDown, FlaskConical, Info, ShieldAlert, TriangleAlert } from "lucide-react";
import type { Analysis, Adjustment } from "@/lib/types";
import { Badge, Card, SectionTitle } from "./ui";
import { ComponentBar, ScoreRing, VerdictPill } from "./score";
import { NutritionInfoBox } from "./NutritionFacts";

const COMP_LABEL: Record<string, string> = {
  nutrition: "Nutrition",
  ingredients: "Ingredients & additives",
  processing: "Processing",
  dietary_suitability: "Dietary suitability",
  product_concerns: "Product-specific concerns",
};
const EVIDENCE: Record<Adjustment["evidence_type"], { label: string; tone: "brand" | "grey" | "amber" | "green" }> = {
  product_measurement: { label: "Label data", tone: "green" },
  regulatory: { label: "Regulatory", tone: "brand" },
  published_research: { label: "Research", tone: "grey" },
  estimate: { label: "Estimate", tone: "amber" },
  unverified: { label: "Unverified", tone: "amber" },
};
const CONCERN_TONE: Record<string, "green" | "grey" | "amber" | "red"> = { beneficial: "green", neutral: "grey", caution: "amber", concern: "red", unknown: "grey" };

export function CriticalAllergenBanner({ analysis }: { analysis: Analysis }) {
  const alerts = analysis.compatibility.flatMap((c) => c.critical_allergen_alerts.map((a) => ({ ...a, who: c.profile_name })));
  if (!alerts.length) return null;
  return (
    <div role="alert" className="flex gap-3 rounded-2xl border-2 border-bad bg-bad-soft p-4 text-bad">
      <AlertOctagon className="size-6 shrink-0" aria-hidden />
      <div>
        <p className="font-display text-lg font-extrabold">Allergen alert</p>
        <ul className="mt-1 space-y-0.5 text-sm font-semibold">
          {alerts.map((a, i) => (
            <li key={i}>
              {a.who}: {a.message}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs">Always check the physical package. Recipes and labels change.</p>
      </div>
    </div>
  );
}

export function AnalysisView({ analysis }: { analysis: Analysis }) {
  const s = analysis.score;
  const [open, setOpen] = useState<string | null>("nutrition");
  const hl = s.highlights;
  const flagGroups: [string, string][] = [
    ["artificial_colours", "Artificial colors"], ["artificial_sweeteners", "Artificial sweeteners"], ["sugar_alcohols", "Sugar alcohols"],
    ["added_sugars", "Added sugars"], ["seed_oils", "Seed oils"], ["palm_oil", "Palm oil"], ["partially_hydrogenated_oils", "Partially hydrogenated oils"],
    ["hydrogenated_oils", "Hydrogenated oils"], ["preservatives", "Preservatives"], ["emulsifiers", "Emulsifiers"], ["thickeners", "Thickeners"],
    ["flavourings", "Flavorings"], ["flavour_enhancers", "Flavor enhancers"], ["whole_grains", "Whole grains"],
  ];
  return (
    <div className="space-y-4">
      <CriticalAllergenBanner analysis={analysis} />

      {analysis.recalls && analysis.recalls.length > 0 && (
        <div role="alert" className="rounded-2xl border-2 border-bad bg-bad-soft p-4 text-bad">
          <p className="flex items-center gap-2 font-display text-lg font-extrabold">
            <ShieldAlert className="size-5" /> Active recall
          </p>
          {analysis.recalls.map((r) => (
            <p key={r.id} className="mt-1 text-sm">
              <b>{r.authority}</b> ({r.jurisdiction}): {r.title}. {r.reason}{" "}
              {r.url && <a className="underline" href={r.url} target="_blank" rel="noreferrer">Official notice</a>}
            </p>
          ))}
        </div>
      )}

      {analysis.compatibility.length > 0 && (
        <Card>
          <SectionTitle>For your profiles</SectionTitle>
          <div className="space-y-3">
            {analysis.compatibility.map((c) => (
              <div key={c.profile_id || c.profile_name}>
                <VerdictPill verdict={c.verdict} name={c.profile_name} />
                <ul className="mt-2 space-y-1 text-sm">
                  {c.reasons.filter((r) => r.severity !== "green").slice(0, 6).map((r, i) => (
                    <li key={i} className="flex gap-2">
                      <span className={`mt-1.5 size-2 shrink-0 rounded-full ${r.severity === "red" ? "bg-bad" : "bg-warn"}`} aria-hidden />
                      {r.message}
                    </li>
                  ))}
                  {c.reasons.every((r) => r.severity === "green") && <li className="text-muted">No conflicts found with this profile&apos;s preferences.</li>}
                </ul>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-muted">{analysis.compatibility[0].disclaimer}</p>
        </Card>
      )}

      <Card>
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
          <ScoreRing score={s.overall} color={s.color} label={s.label} />
          <div className="flex-1 space-y-2 text-center sm:text-left">
            <p className="font-display text-2xl font-extrabold">{s.label}</p>
            <div className="flex flex-wrap justify-center gap-2 sm:justify-start">
              <Badge tone={s.confidence === "high" ? "green" : s.confidence === "medium" ? "amber" : "grey"}>{s.confidence} confidence</Badge>
              <Badge tone="grey">Method {s.methodology_version}</Badge>
              {s.components.processing.nova_group && (
                <Badge tone={s.components.processing.nova_group === 4 ? "red" : s.components.processing.nova_group === 3 ? "amber" : "green"}>
                  NOVA {s.components.processing.nova_group}
                  {s.components.processing.nova_source === "estimated" ? " (est.)" : ""}
                </Badge>
              )}
            </div>
            {s.insufficient_data && (
              <p className="flex items-start gap-2 rounded-xl bg-grey-soft p-3 text-left text-sm">
                <Info className="mt-0.5 size-4 shrink-0" />
                Not enough data for an overall score ({s.missing_components.map((m) => COMP_LABEL[m]).join(", ")} missing). We don&apos;t guess. Scan the label to fill the gaps.
              </p>
            )}
            {s.caps_applied.map((c) => (
              <p key={c.code} className="text-sm text-muted">• {c.reason}</p>
            ))}
          </div>
          <div className="w-full sm:w-72">
            <NutritionInfoBox fop={s.front_of_pack} />
          </div>
        </div>

        <div className="mt-5 space-y-2">
          {Object.entries(s.components).map(([k, c]) => (
            <div key={k} className="rounded-xl border border-line">
              <button className="flex w-full items-center gap-3 p-3 text-left" aria-expanded={open === k} onClick={() => setOpen(open === k ? null : k)}>
                <div className="flex-1">
                  <ComponentBar label={COMP_LABEL[k]} score={c.score} weight={c.weight} assessed={c.assessed} />
                </div>
                <ChevronDown className={`size-4 transition ${open === k ? "rotate-180" : ""}`} aria-hidden />
              </button>
              {open === k && (
                <div className="space-y-2 border-t border-line p-3 text-sm">
                  {c.basis && <p className="text-xs text-muted">Assessed {c.basis}</p>}
                  {c.adjustments.length === 0 && c.assessed && <p className="text-muted">No deductions.</p>}
                  {c.adjustments.map((a) => (
                    <div key={a.code} className="flex gap-3">
                      <span className={`w-12 shrink-0 text-right font-bold tabular-nums ${a.points < 0 ? "text-bad" : "text-good"}`}>
                        {a.points > 0 ? "+" : ""}
                        {a.points}
                      </span>
                      <div className="flex-1">
                        <p>{a.reason}</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          <Badge tone={EVIDENCE[a.evidence_type].tone}>{EVIDENCE[a.evidence_type].label}</Badge>
                          {a.source_keys.map((k2) => (
                            <Link key={k2} href={`/sources#${k2}`} className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-muted underline-offset-2 hover:underline">
                              {k2}
                            </Link>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                  {c.notes.map((n) => (
                    <p key={n} className="flex gap-2 text-muted">
                      <Info className="mt-0.5 size-4 shrink-0" /> {n}
                    </p>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">{s.disclaimer}</p>
      </Card>

      <Card>
        <SectionTitle>What&apos;s inside</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {flagGroups.filter(([k]) => hl[k]?.length).map(([k, label]) => (
            <Badge key={k} tone={k === "whole_grains" ? "green" : k === "partially_hydrogenated_oils" ? "red" : k === "seed_oils" || k === "palm_oil" ? "grey" : "amber"} className="py-1">
              {label}: {hl[k].map((x) => x.name).join(", ")}
            </Badge>
          ))}
          <Badge tone={hl.organic ? "green" : "grey"} className="py-1">{hl.organic_note}</Badge>
        </div>
        {hl.seed_oils?.length > 0 && <p className="mt-2 text-xs text-muted">Seed oils are listed for transparency. The score doesn&apos;t penalize them, because current evidence doesn&apos;t support treating them as harmful in normal diets.</p>}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <SectionTitle>Allergens</SectionTitle>
          <ul className="space-y-1.5 text-sm">
            {analysis.allergens.filter((a) => a.regulated_in_region || a.status === "contains" || a.status === "may_contain").map((a) => (
              <li key={a.code} className="flex items-center justify-between gap-2">
                <span>{a.name}</span>
                <Badge tone={a.status === "contains" ? "red" : a.status === "may_contain" ? "amber" : a.status === "unknown" ? "grey" : "green"}>
                  {a.status === "contains" ? "Contains" : a.status === "may_contain" ? "May contain" : a.status === "unknown" ? "Unknown" : "Not detected"}
                </Badge>
              </li>
            ))}
          </ul>
          {analysis.ingredients_parse?.precautionary_statement && <p className="mt-3 rounded-xl bg-warn-soft p-2 text-xs text-warn">Label says: &ldquo;{analysis.ingredients_parse.precautionary_statement}&rdquo;</p>}
          <p className="mt-3 text-xs text-muted">&ldquo;Not detected&rdquo; means we didn&apos;t find it in the listed ingredients. It isn&apos;t a guarantee.</p>
        </Card>

        <Card>
          <SectionTitle>Lab testing & contaminants</SectionTitle>
          <p className="flex gap-2 text-sm">
            <FlaskConical className="mt-0.5 size-4 shrink-0 text-brand" aria-hidden />
            {analysis.contaminant_testing?.message || "No product-specific laboratory testing on file."}
          </p>
          {analysis.lab_reports?.map((r) => (
            <div key={r.id} className={`mt-2 rounded-xl p-2 text-sm ${r.exceeds_threshold ? "bg-bad-soft text-bad" : "bg-surface-2"}`}>
              <b>{r.analyte}</b>: {r.value} {r.unit}
              {r.threshold !== null && ` (threshold ${r.threshold} ${r.unit}, ${r.threshold_jurisdiction})`}. {r.lab_name}, {r.tested_on || "date n/a"}
            </div>
          ))}
        </Card>
      </div>

      {analysis.ingredients.length > 0 && (
        <Card>
          <SectionTitle>Ingredients</SectionTitle>
          <ol className="divide-y divide-line">
            {analysis.ingredients.filter((i) => !i.is_group || i.ingredient).map((i, idx) => (
              <li key={idx} className="flex items-center gap-3 py-2" style={{ paddingLeft: i.depth * 16 }}>
                {i.ingredient ? (
                  <Link href={`/ingredients/${i.ingredient.slug}`} className="flex flex-1 items-center justify-between gap-2 hover:text-brand">
                    <span>
                      <span className="font-semibold">{i.text.replace(/\s*\(.*$/, "") || i.ingredient.name}</span>
                      {i.percent !== null && <span className="text-muted"> {i.percent}%</span>}
                      <span className="block text-xs text-muted">
                        {i.ingredient.name}
                        {i.ingredient.e_number ? ` · ${i.ingredient.e_number}` : ""} · {i.ingredient.function}
                      </span>
                    </span>
                    {i.ingredient.concern_level !== "neutral" && <Badge tone={CONCERN_TONE[i.ingredient.concern_level]}>{i.ingredient.concern_level}</Badge>}
                  </Link>
                ) : (
                  <span className="flex flex-1 items-center justify-between gap-2">
                    <span>{i.text}</span>
                    <span className="flex items-center gap-1 text-xs text-muted">
                      <TriangleAlert className="size-3.5" /> not in database yet
                    </span>
                  </span>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}
