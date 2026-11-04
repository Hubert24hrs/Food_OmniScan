"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Barcode, Camera, CloudOff, Keyboard } from "lucide-react";
import { BarcodeScanner } from "@/components/BarcodeScanner";
import { Badge, Button, Card, inputCls, LinkButton, Page } from "@/components/ui";
import { flushQueue, queueScan, queuedCount } from "@/lib/offline";

type Mode = "camera" | "manual";

export default function ScanPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("camera");
  const [code, setCode] = useState("");
  const [offline, setOffline] = useState(false);
  const [queued, setQueued] = useState(0);
  const [toast, setToast] = useState<string | null>(null);

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

  return (
    <Page title="Scan" subtitle="Barcodes are read on your device. EAN-13, EAN-8, UPC-A and UPC-E are supported.">
      {offline && (
        <p className="mb-3 flex items-center gap-2 rounded-xl bg-warn-soft p-3 text-sm text-warn" role="status">
          <CloudOff className="size-4" /> You&apos;re offline. Scans are queued and synced later{queued ? ` (${queued} waiting)` : ""}.
        </p>
      )}
      {toast && <p className="mb-3 rounded-xl bg-good-soft p-3 text-sm text-good" role="status">{toast}</p>}

      <div className="mb-4 inline-flex rounded-2xl border border-line bg-surface p-1" role="tablist">
        {([["camera", Barcode, "Camera"], ["manual", Keyboard, "Enter code"]] as const).map(([m, Icon, label]) => (
          <button key={m} role="tab" aria-selected={mode === m} onClick={() => setMode(m)} className={`flex min-h-10 items-center gap-2 rounded-xl px-4 text-sm font-semibold ${mode === m ? "bg-brand text-white dark:text-[#06201d]" : "text-muted"}`}>
            <Icon className="size-4" aria-hidden /> {label}
          </button>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-[1.3fr_1fr]">
        <div>
          {mode === "camera" ? <BarcodeScanner onDetected={go} /> : (
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
          <p className="font-display font-bold">No barcode, or product not found?</p>
          <p className="text-sm text-muted">Photograph the ingredient list and Nutrition Facts panel. We&apos;ll read them on your device and analyze them right away.</p>
          <LinkButton href="/analyze" variant="secondary" className="w-full">
            <Camera className="size-4" aria-hidden /> Scan a label
          </LinkButton>
          <div className="flex flex-wrap gap-1.5 pt-1">
            <Badge tone="grey">Flashlight support</Badge>
            <Badge tone="grey">Works offline</Badge>
            <Badge tone="grey">No photo upload needed</Badge>
          </div>
        </Card>
      </div>
    </Page>
  );
}
