"use client";

import { useEffect, useRef, useState } from "react";
import { Flashlight, FlashlightOff, VideoOff } from "lucide-react";
import type { IScannerControls } from "@zxing/browser";

/** Live camera scanner for product barcodes (EAN-13/8, UPC-A/E) and QR / Data Matrix codes, using ZXing on-device. */
export function BarcodeScanner({ onDetected, paused }: { onDetected: (code: string) => void; paused?: boolean }) {
  const video = useRef<HTMLVideoElement>(null);
  const controls = useRef<IScannerControls | null>(null);
  const last = useRef<{ code: string; at: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [torch, setTorch] = useState(false);
  const [torchAvailable, setTorchAvailable] = useState(false);

  useEffect(() => {
    if (paused) return;
    let cancelled = false;
    (async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser can't access the camera. Enter the barcode below.");
        const [{ BrowserMultiFormatReader }, { BarcodeFormat, DecodeHintType }] = await Promise.all([import("@zxing/browser"), import("@zxing/library")]);
        const hints = new Map();
        hints.set(DecodeHintType.POSSIBLE_FORMATS, [BarcodeFormat.EAN_13, BarcodeFormat.EAN_8, BarcodeFormat.UPC_A, BarcodeFormat.UPC_E, BarcodeFormat.QR_CODE, BarcodeFormat.DATA_MATRIX]);
        hints.set(DecodeHintType.TRY_HARDER, true);
        const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 120 });
        if (cancelled || !video.current) return;
        controls.current = await reader.decodeFromConstraints(
          { video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } } },
          video.current,
          (result) => {
            if (!result) return;
            const code = result.getText();
            const now = Date.now();
            // Require the same code on two consecutive reads to avoid misreads; debounce repeats.
            if (last.current && last.current.code === code && now - last.current.at < 1500) {
              last.current = { code, at: now + 4000 };
              navigator.vibrate?.(60);
              onDetected(code);
            } else if (!last.current || last.current.code !== code || now > last.current.at) {
              last.current = { code, at: now };
            }
          },
        );
        setTorchAvailable(Boolean(controls.current.switchTorch));
      } catch (e) {
        const err = e as DOMException;
        setError(
          err.name === "NotAllowedError"
            ? "Camera permission was denied. Allow camera access in your browser settings, or enter the barcode below."
            : err.name === "NotFoundError"
              ? "No camera found on this device. Enter the barcode below."
              : err.message || "Couldn't start the camera.",
        );
      }
    })();
    return () => {
      cancelled = true;
      controls.current?.stop();
      controls.current = null;
    };
  }, [paused, onDetected]);

  const toggleTorch = async () => {
    try {
      await controls.current?.switchTorch?.(!torch);
      setTorch(!torch);
    } catch {
      setTorchAvailable(false);
    }
  };

  if (error) {
    return (
      <div className="flex aspect-[4/3] flex-col items-center justify-center gap-3 rounded-3xl bg-surface-2 p-6 text-center text-sm text-muted" role="alert">
        <VideoOff className="size-8" aria-hidden />
        {error}
      </div>
    );
  }
  return (
    <div className="relative overflow-hidden rounded-3xl bg-black">
      <video ref={video} className="aspect-[4/3] w-full object-cover" muted playsInline aria-label="Camera preview for barcode scanning" />
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="relative h-44 w-4/5 max-w-sm rounded-2xl border-4 border-brand shadow-[0_0_0_9999px_rgba(0,0,0,0.35)]">
          <div className="scanline absolute inset-x-4 top-1/2 h-0.5 bg-sun" />
        </div>
      </div>
      <p className="absolute inset-x-0 bottom-3 text-center text-sm font-semibold text-white drop-shadow">Point at a barcode or QR code</p>
      {torchAvailable && (
        <button onClick={toggleTorch} className="absolute right-3 top-3 rounded-full bg-black/60 p-3 text-white" aria-label={torch ? "Turn flashlight off" : "Turn flashlight on"} aria-pressed={torch}>
          {torch ? <FlashlightOff className="size-5" /> : <Flashlight className="size-5" />}
        </button>
      )}
    </div>
  );
}
