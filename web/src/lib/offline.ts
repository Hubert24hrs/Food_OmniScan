"use client";

import { api, getToken } from "./api";

// Offline scan queue: barcodes scanned without a connection are uploaded to /scans/sync later.
const KEY = "omniscan.queue";
type Queued = { client_id: string; barcode: string; scanned_at: string };

function read(): Queued[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

function write(q: Queued[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(q.slice(-200)));
  } catch {
    /* storage unavailable */
  }
}

export function queueScan(barcode: string) {
  const id = typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  write([...read(), { client_id: id, barcode, scanned_at: new Date().toISOString() }]);
}

export function queuedCount() {
  return read().length;
}

export async function flushQueue(): Promise<number> {
  const q = read();
  if (!q.length || !getToken() || !navigator.onLine) return 0;
  const r = await api<{ results: { client_id: string; status: string }[] }>("/scans/sync", { body: q });
  const retry = new Set(r.results.filter((x) => x.status === "retry_later").map((x) => x.client_id));
  write(q.filter((x) => retry.has(x.client_id)));
  return q.length - retry.size;
}

// Lightweight cache of recently viewed products for offline viewing.
const PKEY = "omniscan.products";
export function cacheProduct(id: string, payload: unknown) {
  try {
    const m = JSON.parse(localStorage.getItem(PKEY) || "{}");
    m[id] = { at: Date.now(), payload };
    const entries = Object.entries(m).sort((a, b) => (b[1] as { at: number }).at - (a[1] as { at: number }).at).slice(0, 30);
    localStorage.setItem(PKEY, JSON.stringify(Object.fromEntries(entries)));
  } catch {
    /* ignore */
  }
}
export function cachedProduct<T>(id: string): T | null {
  try {
    return (JSON.parse(localStorage.getItem(PKEY) || "{}")[id]?.payload as T) || null;
  } catch {
    return null;
  }
}
