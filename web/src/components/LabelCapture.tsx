"use client";

import { useRef, useState } from "react";
import { Camera, Loader2, Sparkles } from "lucide-react";
import { Badge, Button } from "./ui";
import { api } from "@/lib/api";

export interface OcrResult {
  text: string;
  confidence: number; // 0..1
  quality: Quality;
  engine: "on-device" | "cloud-ai";
}
interface Quality {
  ok: boolean;
  issues: string[];
  width: number;
  brightness: number;
  sharpness: number;
}

/** Image-quality check before OCR: resolution, exposure and blur (variance of a Laplacian). */
async function checkQuality(file: File): Promise<Quality> {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, 640 / bmp.width);
  const w = Math.round(bmp.width * scale);
  const h = Math.round(bmp.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(bmp, 0, 0, w, h);
  const { data } = ctx.getImageData(0, 0, w, h);
  const gray = new Float32Array(w * h);
  let sum = 0;
  for (let i = 0; i < w * h; i++) {
    const g = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2];
    gray[i] = g;
    sum += g;
  }
  const brightness = sum / (w * h);
  let lapSum = 0;
  let lapSq = 0;
  let n = 0;
  for (let y = 1; y < h - 1; y += 2) {
    for (let x = 1; x < w - 1; x += 2) {
      const i = y * w + x;
      const l = 4 * gray[i] - gray[i - 1] - gray[i + 1] - gray[i - w] - gray[i + w];
      lapSum += l;
      lapSq += l * l;
      n++;
    }
  }
  const mean = lapSum / n;
  const sharpness = lapSq / n - mean * mean;
  const issues: string[] = [];
  if (bmp.width < 700) issues.push("Low resolution: move closer or use a higher-quality photo.");
  if (brightness < 60) issues.push("Too dark: turn on more light or use the flashlight.");
  if (brightness > 225) issues.push("Overexposed: avoid glare and direct light on the label.");
  if (sharpness < 80) issues.push("Looks blurry: hold steady and tap to focus.");
  return { ok: issues.length === 0, issues, width: bmp.width, brightness: Math.round(brightness), sharpness: Math.round(sharpness) };
}

export function LabelCapture({ kind, onResult, allowCloud }: { kind: "ingredients" | "nutrition"; onResult: (r: OcrResult) => void; allowCloud?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [quality, setQuality] = useState<Quality | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pick = async (f: File) => {
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
    try {
      setQuality(await checkQuality(f));
    } catch {
      setQuality(null);
    }
  };

  const runOcr = async () => {
    if (!file) return;
    setBusy("Reading the label on your device…");
    setError(null);
    try {
      const { createWorker } = await import("tesseract.js");
      const worker = await createWorker("eng");
      const { data } = await worker.recognize(file);
      await worker.terminate();
      onResult({ text: data.text.trim(), confidence: (data.confidence || 0) / 100, quality: quality!, engine: "on-device" });
    } catch (e) {
      setError(`On-device OCR failed: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  const runCloud = async () => {
    if (!file) return;
    setBusy("Asking cloud AI to read the label…");
    setError(null);
    try {
      const form = new FormData();
      form.append("task", kind);
      form.append("image", file);
      const r = await api<{ extracted: { ingredients_text?: string; panel_text?: string; legibility?: string; may_contain_statement?: string } }>("/analysis/image", { form });
      const t = kind === "ingredients" ? [r.extracted.ingredients_text, r.extracted.may_contain_statement].filter(Boolean).join(". ") : r.extracted.panel_text || "";
      onResult({ text: t, confidence: r.extracted.legibility === "good" ? 0.9 : r.extracted.legibility === "partial" ? 0.6 : 0.3, quality: quality!, engine: "cloud-ai" });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-3">
      <input ref={input} type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => e.target.files?.[0] && pick(e.target.files[0])} aria-label={`Photo of the ${kind} label`} />
      {preview ? (
        // eslint-disable-next-line @next/next/no-img-element -- local object URL preview
        <img src={preview} alt={`Your ${kind} label photo`} className="max-h-72 w-full rounded-2xl border border-line object-contain" />
      ) : (
        <button onClick={() => input.current?.click()} className="flex w-full flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-line px-6 py-10 text-muted hover:border-brand hover:text-brand">
          <Camera className="size-8" aria-hidden />
          <span className="font-semibold">Photograph the {kind === "ingredients" ? "ingredient list" : "Nutrition Facts panel"}</span>
          <span className="text-xs">Fill the frame, avoid glare. Processed on your device.</span>
        </button>
      )}
      {quality && (
        <div className="flex flex-wrap gap-2">
          {quality.ok ? <Badge tone="green">Image quality looks good</Badge> : quality.issues.map((i) => <Badge key={i} tone="amber">{i}</Badge>)}
        </div>
      )}
      {error && <p className="text-sm text-bad" role="alert">{error}</p>}
      {file && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={runOcr} loading={busy?.includes("device")} disabled={!!busy}>
            Read label
          </Button>
          {allowCloud && (
            <Button variant="secondary" onClick={runCloud} loading={busy?.includes("cloud")} disabled={!!busy}>
              <Sparkles className="size-4" aria-hidden /> Cloud AI (uses a credit)
            </Button>
          )}
          <Button variant="ghost" onClick={() => input.current?.click()} disabled={!!busy}>
            Retake
          </Button>
        </div>
      )}
      {busy && (
        <p className="flex items-center gap-2 text-sm text-muted" role="status">
          <Loader2 className="size-4 animate-spin" /> {busy}
        </p>
      )}
    </div>
  );
}
