// Works out what a scanned code is (mirrors mobile/lib/core/scan_codes.dart).

export type ScannedCode =
  | { kind: "product"; gtin: string }
  | { kind: "shared"; token: string }
  | { kind: "link"; url: string; host: string }
  | { kind: "text"; text: string };

const GTIN = /^\d{8}$|^\d{12,14}$/;
// GS1 Digital Link: https://brand.example/01/09506000134352/10/ABC  (AI 01 = GTIN)
const DIGITAL_LINK = /\/01\/(\d{8,14})(?:\/|$|\?)/;
// GS1 element string in a GS1 QR / Data Matrix: "(01)09506000134352…" or "0109506000134352…"
const ELEMENT = /^\x1d?\(?01\)?(\d{14})/;

export function classifyCode(raw: string): ScannedCode {
  const s = raw.trim();
  const compact = s.replace(/ /g, "");
  if (GTIN.test(compact)) return { kind: "product", gtin: compact };
  const el = ELEMENT.exec(compact);
  if (el) return { kind: "product", gtin: el[1] };
  let url: URL | null = null;
  try {
    url = new URL(s);
  } catch {
    url = null;
  }
  if (url && (url.protocol === "http:" || url.protocol === "https:") && url.host) {
    const path = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
    const dl = DIGITAL_LINK.exec(path);
    if (dl) return { kind: "product", gtin: dl[1] };
    const segs = url.pathname.split("/").filter(Boolean);
    if (segs.length === 2 && segs[0] === "r" && /^[A-Za-z0-9_-]{8,40}$/.test(segs[1])) return { kind: "shared", token: segs[1] };
    return { kind: "link", url: url.toString(), host: url.host };
  }
  return { kind: "text", text: s };
}
