"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Analysis } from "@/lib/types";
import { AnalysisView } from "@/components/AnalysisView";
import { LabelCapture, type OcrResult } from "@/components/LabelCapture";
import { OcrReview } from "@/components/OcrReview";
import { Button, Card, ErrorBox, Page, SectionTitle } from "@/components/ui";

export default function AnalyzePage() {
  const { me } = useAuth();
  const [ing, setIng] = useState("");
  const [nut, setNut] = useState("");
  const [ingRes, setIngRes] = useState<OcrResult | null>(null);
  const [nutRes, setNutRes] = useState<OcrResult | null>(null);
  const [bev, setBev] = useState(false);
  const [result, setResult] = useState<(Analysis & { note: string; nutrition_label: { warnings: string[] } | null }) | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const analyze = async () => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api("/analysis/text", { body: { ingredients_text: ing || null, nutrition_text: nut || null, is_beverage: bev } }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Scan a label" subtitle="Photograph the ingredient list and Nutrition Facts panel, or paste the text. Correct any OCR mistakes before analyzing.">
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <SectionTitle>1 · Ingredients</SectionTitle>
          <LabelCapture kind="ingredients" allowCloud={!!me} onResult={(r) => { setIngRes(r); setIng(r.text); }} />
          <OcrReview label="Ingredients text" value={ing} onChange={setIng} result={ingRes} />
        </Card>
        <Card>
          <SectionTitle>2 · Nutrition Facts</SectionTitle>
          <LabelCapture kind="nutrition" allowCloud={!!me} onResult={(r) => { setNutRes(r); setNut(r.text); }} />
          <OcrReview label="Nutrition panel text" value={nut} onChange={setNut} result={nutRes} />
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={bev} onChange={(e) => setBev(e.target.checked)} /> This is a beverage
          </label>
        </Card>
      </div>
      <div className="mt-4 flex gap-2">
        <Button onClick={analyze} loading={busy} disabled={!ing.trim() && !nut.trim()}>Analyze</Button>
      </div>
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
      {result && (
        <div className="mt-6 space-y-3">
          <p className="rounded-xl bg-surface-2 p-3 text-sm">{result.note}</p>
          {result.nutrition_label?.warnings?.map((w) => <p key={w} className="rounded-xl bg-warn-soft p-2 text-sm text-warn">{w}</p>)}
          <AnalysisView analysis={result} />
        </div>
      )}
    </Page>
  );
}
