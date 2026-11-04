"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ImagePlus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { LabelCapture, type OcrResult } from "@/components/LabelCapture";
import { Button, Card, ErrorBox, Field, inputCls, LinkButton, Page, SectionTitle } from "@/components/ui";
import { OcrReview } from "@/components/OcrReview";

const NUT_FIELDS: [string, string, string][] = [
  ["energy_kcal", "Calories", "kcal"], ["fat", "Total fat", "g"], ["saturated_fat", "Saturated fat", "g"], ["trans_fat", "Trans fat", "g"],
  ["carbohydrates", "Total carbohydrate", "g"], ["sugars", "Total sugars", "g"], ["added_sugars", "Added sugars", "g"], ["fiber", "Dietary fiber", "g"],
  ["protein", "Protein", "g"], ["sodium_mg", "Sodium", "mg"],
];

function SubmitForm() {
  const { me } = useAuth();
  const router = useRouter();
  const barcode = useSearchParams().get("barcode") || "";
  const [f, setF] = useState({ barcode, name: "", brand: "", category: "", quantity: "", serving_size: "", is_beverage: false });
  const [ing, setIng] = useState("");
  const [ingRes, setIngRes] = useState<OcrResult | null>(null);
  const [nutText, setNutText] = useState("");
  const [nutRes, setNutRes] = useState<OcrResult | null>(null);
  const [nut, setNut] = useState<Record<string, string>>({});
  const [images, setImages] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<string | null>(null);

  if (!me) return <Page><Card className="mx-auto max-w-md text-center"><p className="font-semibold">Sign in to add products</p><LinkButton className="mt-3" href={`/login?next=/submit?barcode=${barcode}`}>Sign in</LinkButton></Card></Page>;

  const parseNut = async (text: string) => {
    setNutText(text);
    try {
      const r = await api<{ per_100: Record<string, number | null> | null }>("/analysis/nutrition-label", { body: { text, is_beverage: f.is_beverage } });
      if (r.per_100) {
        const out: Record<string, string> = {};
        for (const [k, , ] of NUT_FIELDS) {
          const v = k === "sodium_mg" ? (r.per_100.sodium != null ? r.per_100.sodium * 1000 : null) : r.per_100[k];
          if (v !== null && v !== undefined) out[k] = String(Math.round(v * 10) / 10);
        }
        setNut(out);
      }
    } catch {
      /* user can type values manually */
    }
  };

  const upload = async (file: File) => {
    const form = new FormData();
    form.append("image", file);
    const r = await api<{ image_id: string }>("/uploads", { form });
    setImages((s) => [...s, r.image_id]);
  };

  const submit = async () => {
    setBusy(true);
    setError(null);
    try {
      const n: Record<string, number> = {};
      for (const [k, v] of Object.entries(nut)) {
        if (v === "") continue;
        if (k === "sodium_mg") n.sodium = Number(v) / 1000;
        else n[k] = Number(v);
      }
      const ocrConf = [ingRes?.confidence, nutRes?.confidence].filter((x): x is number => typeof x === "number");
      const r = await api<{ id: string; message: string }>("/submissions", {
        body: {
          ...f, ingredients_text: ing || null, nutrition: Object.keys(n).length ? n : null, nutrition_basis: f.is_beverage ? "100ml" : "100g",
          image_ids: images, ocr_confidence: ocrConf.length ? Math.min(...ocrConf) : null, user_corrected_ocr: true, countries: [me.country || "US"],
        },
      });
      setDone(r.message);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  if (done) return <Page><Card className="mx-auto max-w-md text-center"><p className="font-display text-xl font-extrabold">Thank you!</p><p className="mt-2 text-sm text-muted">{done}</p><div className="mt-4 flex justify-center gap-2"><LinkButton href="/scan">Scan another</LinkButton><Button variant="secondary" onClick={() => router.push("/profile#submissions")}>My submissions</Button></div></Card></Page>;

  return (
    <Page title="Add a product" subtitle="Everything here comes from the package you're holding. Please don't guess values.">
      <div className="grid gap-4 md:grid-cols-2">
        <Card className="space-y-3">
          <SectionTitle>Product details</SectionTitle>
          <Field label="Barcode"><input className={inputCls} inputMode="numeric" value={f.barcode} onChange={(e) => setF({ ...f, barcode: e.target.value })} required /></Field>
          <Field label="Product name"><input className={inputCls} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required /></Field>
          <Field label="Brand"><input className={inputCls} value={f.brand} onChange={(e) => setF({ ...f, brand: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Category"><input className={inputCls} placeholder="e.g. Breakfast cereal" value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })} /></Field>
            <Field label="Net quantity"><input className={inputCls} placeholder="e.g. 12 oz (340 g)" value={f.quantity} onChange={(e) => setF({ ...f, quantity: e.target.value })} /></Field>
          </div>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={f.is_beverage} onChange={(e) => setF({ ...f, is_beverage: e.target.checked })} /> Beverage</label>
          <div>
            <p className="mb-1 text-sm font-semibold">Photos (front, ingredients, nutrition)</p>
            <label className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-line p-3 text-sm text-muted hover:border-brand">
              <ImagePlus className="size-5" /> Add photo ({images.length}/6)
              <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0]).catch(setError)} />
            </label>
            <p className="mt-1 text-xs text-muted">Photos are re-encoded to strip location metadata.</p>
          </div>
        </Card>
        <Card>
          <SectionTitle>Ingredients</SectionTitle>
          <LabelCapture kind="ingredients" onResult={(r) => { setIngRes(r); setIng(r.text); }} />
          <OcrReview label="Ingredients" value={ing} onChange={setIng} result={ingRes} />
        </Card>
        <Card className="md:col-span-2">
          <SectionTitle>Nutrition Facts</SectionTitle>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <LabelCapture kind="nutrition" onResult={(r) => { setNutRes(r); parseNut(r.text); }} />
              {nutText && <OcrReview label="Panel text" value={nutText} onChange={parseNut} result={nutRes} />}
            </div>
            <div>
              <p className="mb-2 text-sm text-muted">Values per 100 {f.is_beverage ? "ml" : "g"} (converted from the per-serving label automatically when serving size is known).</p>
              <div className="grid grid-cols-2 gap-2">
                {NUT_FIELDS.map(([k, l, u]) => (
                  <Field key={k} label={`${l} (${u})`}>
                    <input className={inputCls} inputMode="decimal" value={nut[k] || ""} onChange={(e) => setNut({ ...nut, [k]: e.target.value })} />
                  </Field>
                ))}
              </div>
            </div>
          </div>
        </Card>
      </div>
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
      <div className="mt-4 flex items-center gap-3">
        <Button onClick={submit} loading={busy} disabled={!f.barcode || !f.name}>Submit for review</Button>
        <Link href="/scan" className="text-sm text-muted">Cancel</Link>
      </div>
    </Page>
  );
}

export default function SubmitPage() {
  return <Suspense><SubmitForm /></Suspense>;
}
