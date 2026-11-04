"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import type { Profile } from "@/lib/types";
import { Badge, Button, Chip, ErrorBox, inputCls, SectionTitle } from "./ui";

type Options = {
  allergens: { code: string; name: string; us_major: boolean; eu_14: boolean }[];
  diets: { code: string; name: string }[];
  severities: string[];
};

export function ProfileEditor({ profile, onSaved }: { profile: Profile; onSaved?: () => void }) {
  const opts = useApi<Options>("/profiles/options");
  const [allergens, setAllergens] = useState(profile.allergens);
  const [diets, setDiets] = useState<string[]>(profile.diets);
  const [avoid, setAvoid] = useState<string[]>(profile.avoid);
  const [term, setTerm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);

  const toggleAllergen = (code: string) =>
    setAllergens((a) => (a.some((x) => x.code === code) ? a.filter((x) => x.code !== code) : [...a, { code, severity: "severe", avoid_traces: true }]));
  const setSeverity = (code: string, severity: string) => setAllergens((a) => a.map((x) => (x.code === code ? { ...x, severity } : x)));
  const setTraces = (code: string, avoid_traces: boolean) => setAllergens((a) => a.map((x) => (x.code === code ? { ...x, avoid_traces } : x)));

  const save = async () => {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await api(`/profiles/${profile.id}/allergens`, { method: "PUT", body: allergens });
      await api(`/profiles/${profile.id}/diets`, { method: "PUT", body: diets });
      await api(`/profiles/${profile.id}/avoid`, { method: "PUT", body: avoid });
      setSaved(true);
      onSaved?.();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  if (!opts.data) return opts.error ? <ErrorBox error={opts.error} onRetry={opts.reload} /> : null;
  const us = opts.data.allergens.filter((a) => a.us_major);
  const other = opts.data.allergens.filter((a) => !a.us_major);

  return (
    <div className="space-y-6">
      <section>
        <SectionTitle>Allergies & intolerances</SectionTitle>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">US major allergens (FALCPA + FASTER Act)</p>
        <div className="flex flex-wrap gap-2">
          {us.map((a) => <Chip key={a.code} active={allergens.some((x) => x.code === a.code)} onClick={() => toggleAllergen(a.code)}>{a.name}</Chip>)}
        </div>
        <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">Also regulated in the EU/UK</p>
        <div className="flex flex-wrap gap-2">
          {other.map((a) => <Chip key={a.code} active={allergens.some((x) => x.code === a.code)} onClick={() => toggleAllergen(a.code)}>{a.name}</Chip>)}
        </div>
        {allergens.length > 0 && (
          <div className="mt-4 space-y-2">
            {allergens.map((a) => (
              <div key={a.code} className="flex flex-wrap items-center gap-3 rounded-xl bg-surface-2 p-3 text-sm">
                <span className="min-w-28 font-semibold">{opts.data!.allergens.find((x) => x.code === a.code)?.name}</span>
                <select aria-label="Severity" className="rounded-lg border border-line bg-surface px-2 py-1" value={a.severity} onChange={(e) => setSeverity(a.code, e.target.value)}>
                  {opts.data!.severities.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
                </select>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={a.avoid_traces} onChange={(e) => setTraces(a.code, e.target.checked)} /> Avoid &quot;may contain&quot; too
                </label>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionTitle>Diet & nutrition preferences</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {opts.data.diets.map((d) => (
            <Chip key={d.code} active={diets.includes(d.code)} onClick={() => setDiets((s) => (s.includes(d.code) ? s.filter((x) => x !== d.code) : [...s, d.code]))}>
              {d.name}
            </Chip>
          ))}
        </div>
      </section>

      <section>
        <SectionTitle>Ingredients to avoid</SectionTitle>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const t = term.trim().toLowerCase();
            if (t && !avoid.includes(t)) setAvoid([...avoid, t]);
            setTerm("");
          }}
        >
          <input className={inputCls} placeholder="e.g. palm oil, Red 40, E171, MSG" value={term} onChange={(e) => setTerm(e.target.value)} aria-label="Ingredient to avoid" />
          <Button type="submit" variant="secondary">Add</Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {avoid.map((t) => (
            <Badge key={t} tone="brand" className="py-1">
              {t}
              <button aria-label={`Remove ${t}`} onClick={() => setAvoid(avoid.filter((x) => x !== t))}>
                <X className="size-3.5" />
              </button>
            </Badge>
          ))}
        </div>
      </section>

      {error ? <ErrorBox error={error} /> : null}
      <div className="flex items-center gap-3">
        <Button onClick={save} loading={busy}>Save preferences</Button>
        {saved && <span className="text-sm font-semibold text-good" role="status">Saved ✓</span>}
      </div>
      <p className="text-xs text-muted">Compatibility checks use available ingredient data. They can&apos;t guarantee a product is allergen-free and aren&apos;t a medical diagnosis.</p>
    </div>
  );
}
