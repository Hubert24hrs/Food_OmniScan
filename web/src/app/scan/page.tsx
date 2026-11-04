"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { Barcode, Camera, CloudOff, Contact, Copy, ExternalLink, ImageUp, Keyboard, Mail, MapPin, MessageSquare, Phone, QrCode, Wifi } from "lucide-react";
import { BarcodeScanner, decodeImageFile } from "@/components/BarcodeScanner";
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
  const [other, setOther] = useState<Exclude<ScannedCode, { kind: "product" | "shared" }> | null>(null);

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
      if (![8, 12, 13, 14].includes(c.length)) {
        setToast("Barcodes have 8, 12, 13 or 14 digits.");
        return;
      }
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

  // Typed digits are a barcode; anything else typed or pasted (a link, a GS1 string) is classified like a scan.
  const submit = (text: string) => (/^[\d\s-]+$/.test(text.trim()) ? go(text) : text.trim() && onScan(text));

  const fromPhoto = async (file: File | undefined) => {
    if (!file) return;
    const v = await decodeImageFile(file);
    if (v) onScan(v);
    else setToast("No barcode or QR code found in that photo.");
  };

  return (
    <Page title="Scan" subtitle="Read on your device: any barcode or QR code. Product barcodes and GS1 product QR codes open the product; links, Wi-Fi, phone, email and other codes show what they contain.">
      {offline && (
        <p className="mb-3 flex items-center gap-2 rounded-xl bg-warn-soft p-3 text-sm text-warn" role="status">
          <CloudOff className="size-4" /> You&apos;re offline. Scans are queued and synced later{queued ? ` (${queued} waiting)` : ""}.
        </p>
      )}
      {toast && <p className="mb-3 rounded-xl bg-good-soft p-3 text-sm text-good" role="status">{toast}</p>}
      {other && <OtherCode code={other} onCopied={() => setToast("Copied.")} onDismiss={() => setOther(null)} />}

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
              <form onSubmit={(e) => { e.preventDefault(); submit(code); }} className="space-y-3">
                <label className="block text-sm font-semibold" htmlFor="code">Barcode number</label>
                <input id="code" className={`${inputCls} text-lg tracking-widest`} inputMode="numeric" placeholder="e.g. 049000000443" value={code} onChange={(e) => setCode(e.target.value)} autoFocus />
                <Button type="submit" className="w-full">Look up</Button>
              </form>
            </Card>
          )}
          {mode === "camera" && (
            <form onSubmit={(e) => { e.preventDefault(); submit(code); }} className="mt-3 flex gap-2">
              <input className={inputCls} inputMode="numeric" placeholder="Or type the barcode" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Barcode number" />
              <Button type="submit" variant="secondary">Go</Button>
            </form>
          )}
          <label className="mt-3 flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-line px-4 text-sm font-semibold text-muted hover:border-brand hover:text-brand">
            <ImageUp className="size-4" aria-hidden /> Scan a code from a photo or screenshot
            <input type="file" accept="image/*" className="sr-only" onChange={(e) => { fromPhoto(e.target.files?.[0]); e.target.value = ""; }} />
          </label>
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

const ACTIONS = {
  phone: { icon: Phone, title: "Phone number", verb: "Call" },
  email: { icon: Mail, title: "Email address", verb: "Write email" },
  sms: { icon: MessageSquare, title: "Text message", verb: "Send text" },
  geo: { icon: MapPin, title: "Location", verb: "Open map" },
} as const;

/** What a non-product code contains, with the matching action and Copy. */
function OtherCode({ code, onCopied, onDismiss }: { code: Exclude<ScannedCode, { kind: "product" | "shared" }>; onCopied: () => void; onDismiss: () => void }) {
  const btn = "btn-brand inline-flex min-h-11 items-center gap-2 rounded-xl px-4 text-sm font-semibold";
  let Icon = QrCode;
  let title = "Scanned code";
  let body: React.ReactNode;
  let action: React.ReactNode = null;
  let copy: string;
  switch (code.kind) {
    case "link":
      title = "This code is a link";
      body = (
        <>
          <p className="mt-1 text-sm text-muted">It goes to <b className="text-ink">{code.host}</b>. Only open links you trust.</p>
          <p className="mt-1 break-all text-sm">{code.url}</p>
        </>
      );
      action = <a href={code.url} target="_blank" rel="noopener noreferrer" className={btn}><ExternalLink className="size-4" aria-hidden /> Open link</a>;
      copy = code.url;
      break;
    case "wifi":
      Icon = Wifi;
      title = "Wi-Fi network";
      body = <p className="mt-1 text-sm">Network: <b>{code.ssid}</b>{code.security ? ` · ${code.security}` : ""}</p>;
      copy = code.password ?? code.ssid;
      break;
    case "action": {
      const a = ACTIONS[code.action];
      Icon = a.icon;
      title = a.title;
      body = <p className="mt-1 break-all text-sm font-semibold">{code.label}</p>;
      action = <a href={code.href} target={code.action === "geo" ? "_blank" : undefined} rel="noopener noreferrer" className={btn}><a.icon className="size-4" aria-hidden /> {a.verb}</a>;
      copy = code.label;
      break;
    }
    case "contact":
      Icon = Contact;
      title = "Contact card";
      body = <p className="mt-1 text-sm font-semibold">{code.name || "Contact details"}</p>;
      copy = code.text;
      break;
    default:
      body = (
        <>
          <p className="mt-1 text-sm text-muted">This isn&apos;t a product barcode. It contains:</p>
          <p className="mt-1 whitespace-pre-wrap break-all text-sm">{code.text.slice(0, 1000)}</p>
        </>
      );
      copy = code.text;
  }
  return (
    <Card className="mb-4" role="status">
      <p className="flex items-center gap-2 font-display font-bold"><Icon className="size-5 text-brand" aria-hidden /> {title}</p>
      {body}
      <div className="mt-3 flex flex-wrap gap-2">
        {action}
        <Button variant="secondary" onClick={() => navigator.clipboard?.writeText(copy).then(onCopied)}>
          <Copy className="size-4" aria-hidden /> {code.kind === "wifi" && code.password ? "Copy password" : "Copy"}
        </Button>
        <Button variant="ghost" onClick={onDismiss}>Dismiss</Button>
      </div>
    </Card>
  );
}
