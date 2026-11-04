"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Barcode, Camera, CloudOff, Copy, ExternalLink, Keyboard, QrCode } from "lucide-react";
import { BarcodeScanner } from "@/components/BarcodeScanner";
import { Badge, Button, Card, inputCls, LinkButton, Page } from "@/components/ui";
import { flushQueue, queueScan, queuedCount } from "@/lib/offline";
import { classifyCode, type ScannedCode } from "@/lib/scanCodes";

type Mode = "camera" | "manual";

export default function ScanPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("camera");
  const [code, setCode] = useState("");
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [other, setOther] = useState<Extract<ScannedCode, { kind: "link" | "text" }> | null>(null);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    Promise.resolve().then(() => {
      update();
      setQueued(queuedCount());
    });
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    flushQueue().then((n) => n && setToast(`Synced ${n} offline scan${n > 1 ? "s" : ""}.`)).catch(() => {}).finally(() => setQueued(queuedCount()));
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  const go = useCallback(
    (raw: string) => {
      const c = raw.replace(/\D/g, "");
      if (!c) return;
      if (!navigator.onLine) {
        queueScan(c);
        setQueued(queuedCount());
        setToast(`Saved ${c}. It will be looked up when you're back online.`);
        return;
      }
      router.push(`/scan/${c}`);
    },
    [router],
  );

  // Camera results can be product barcodes or QR codes: route each kind to the right place.
  const onScan = useCallback(
    (raw: string) => {
      const c = classifyCode(raw);
      if (c.kind === "product") go(c.gtin);
      else if (c.kind === "shared") router.push(`/r/${c.token}`);
      else setOther(c);
    },
    [go, router],
  );

  return (
    <Page title="Scan" subtitle="Read on your device: product barcodes (EAN-13, EAN-8, UPC-A, UPC-E) and QR codes, including GS1 product QR codes.">
      {offline && (
        <p className="mb-3 flex items-center gap-2 rounded-xl bg-warn-soft p-3 text-sm text-warn" role="status">
          <CloudOff className="size-4" /> You&apos;re offline. Scans are queued and synced later{queued ? ` (${queued} waiting)` : ""}.
        </p>
      )}
      {toast && <p className="mb-3 rounded-xl bg-good-soft p-3 text-sm text-good" role="status">{toast}</p>}
      {other && (
        <Card className="mb-4" role="status">
          <p className="flex items-center gap-2 font-display font-bold"><QrCode className="size-5 text-brand" aria-hidden /> {other.kind === "link" ? "This QR code is a link" : "Scanned code"}</p>
          {other.kind === "link" ? (
            <>
              <p className="mt-1 text-sm text-muted">It goes to <b className="text-ink">{other.host}</b>. Only open links you trust.</p>
              <p className="mt-1 break-all text-sm">{other.url}</p>
            </>
          ) : (
            <>
              <p className="mt-1 text-sm text-muted">This isn&apos;t a product barcode. It contains:</p>
              <p className="mt-1 whitespace-pre-wrap break-all text-sm">{other.text.slice(0, 1000)}</p>
            </>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {other.kind === "link" && (
              <a href={other.url} target="_blank" rel="noopener noreferrer" className="btn-brand inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold">
                <ExternalLink className="size-4" aria-hidden /> Open link
              </a>
            )}
            <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(other.kind === "link" ? other.url : other.text).then(() => setToast("Copied."))}>
              <Copy className="size-4" aria-hidden /> Copy
            </Button>
            <Button variant="ghost" onClick={() => setOther(null)}>Dismiss</Button>
          </div>
        </Card>
      )}

      <div className="mb-4 inline-flex bg-surface rounded-2xl border border-line p-1" role="tablist">
        {([["camera", Barcode, "Camera"], ["manual", Keyboard, "Enter code"]] as const).map(([m, Icon, label]) => (
          <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`flex min-h-10 items-center gap-2 rounded-xl px-4 text-sm font-semibold transition-all ${mode === m ? "btn-brand" : "text-muted hover:text-brand"}`}>
            <Icon className="size-4" aria-hidden /> {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <div>
          {mode === "camera" ? <BarcodeScanner onDetected={onScan} /> : (
            <Card>
              <form onSubmit={(e) => { e.preventDefault(); go(code); }} className="space-y-3">
                <label className="block text-sm font-semibold" htmlFor="code">Barcode number</label>
                <input id="code" className={`${inputCls} text-lg tracking-widest`} inputMode="numeric" pattern="[0-9 ]{8,14}" placeholder="e.g. 049000000443" value={code} onChange={(e) => setCode(e.target.value)} autoFocus />
                <Button type="submit" className="w-full">Look up</Button>
              </form>
            </Card>
          )}
          {mode === "camera" && (
            <form onSubmit={(e) => { e.preventDefault(); go(code); }} className="mt-3 flex gap-2">
              <input className={inputCls} inputMode="numeric" placeholder="Or type the barcode" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Barcode number" />
              <Button type="submit" variant="secondary">Go</Button>
            </form>
          )}
        </div>
        <Card className="space-y-3">
          <Image src="/brand/scan.svg" alt="" width={1024} height={1024} unoptimized className="icon-float mx-auto size-40" />
          <p className="font-display font-bold">No barcode, or product not found?</p>
          <p className="text-sm text-muted">Photograph the ingredient list and Nutrition Facts panel. We&apos;ll read them on your device and analyze them right away.</p>
          <LinkButton href="/analyze" variant="secondary" className="w-full">
            <Camera className="size-4" aria-hidden /> Scan a label
          </LinkButton>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <Badge tone="brand">Flashlight support</Badge>
            <Badge tone="tomato">Works offline</Badge>
            <Badge tone="sun">No photo upload needed</Badge>
          </div>
        </Card>
      </div>
    </Page>
  );
}
