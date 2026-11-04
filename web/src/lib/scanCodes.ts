// Works out what a scanned code is (mirrors mobile/lib/core/scan_codes.dart): product barcodes, GS1 QR codes,
// share links, other links, Wi-Fi, phone, email, SMS, map locations, contact cards and plain text.

export type ActionKind = "phone" | "email" | "sms" | "geo";

export type ScannedCode =
  | { kind: "product"; gtin: string }
  | { kind: "shared"; token: string }
  | { kind: "link"; url: string; host: string }
  | { kind: "wifi"; ssid: string; password: string | null; security: string | null }
  | { kind: "action"; action: ActionKind; href: string; label: string }
  | { kind: "contact"; name: string | null; text: string }
  | { kind: "text"; text: string };

const GTIN = /^\d{8}$|^\d{12,14}$/;
// GS1 Digital Link: https://brand.example/01/09506000134352/10/ABC  (AI 01 = GTIN)
const DIGITAL_LINK = /\/01\/(\d{8,14})(?:\/|$|\?)/;
// GS1 element string (GS1 QR / Data Matrix / GS1-128): "(01)09506000134352…" or "0109506000134352…"
const ELEMENT = /^(?:\]\w\d)?\x1d?\(?01\)?(\d{14})/;
const LATLNG = /^-?\d+(\.\d+)?,-?\d+(\.\d+)?/;

/** Splits "KEY:value;KEY:value;;" (Wi-Fi / MECARD), honouring backslash escapes. */
function fields(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  const parts: string[] = [];
  let buf = "";
  for (let i = 0; i < body.length; i++) {
    const c = body[i];
    if (c === "\\" && i + 1 < body.length) buf += body[++i];
    else if (c === ";") {
      parts.push(buf);
      buf = "";
    } else buf += c;
  }
  if (buf) parts.push(buf);
  for (const p of parts) {
    const j = p.indexOf(":");
    if (j > 0) {
      const k = p.slice(0, j).toUpperCase();
      if (!(k in out)) out[k] = p.slice(j + 1);
    }
  }
  return out;
}

export function classifyCode(raw: string): ScannedCode {
  const s = raw.trim();
  const compact = s.replace(/ /g, "");
  if (GTIN.test(compact)) return { kind: "product", gtin: compact };
  const el = ELEMENT.exec(compact);
  if (el) return { kind: "product", gtin: el[1] };

  const upper = s.toUpperCase();
  if (upper.startsWith("WIFI:")) {
    const f = fields(s.slice(5));
    if (f.S) return { kind: "wifi", ssid: f.S, password: f.P || null, security: f.T || null };
  }
  if (upper.startsWith("BEGIN:VCARD")) {
    const m = /^FN(?:;[^:]*)?:(.+)$/im.exec(s);
    return { kind: "contact", name: m ? m[1].trim() : null, text: s };
  }
  if (upper.startsWith("MECARD:")) {
    const n = fields(s.slice(7)).N;
    return { kind: "contact", name: n ? n.split(",").reverse().join(" ").trim() : null, text: s };
  }
  if (upper.startsWith("MATMSG:")) {
    const f = fields(s.slice(7));
    if (f.TO) {
      const q = new URLSearchParams();
      if (f.SUB) q.set("subject", f.SUB);
      if (f.BODY) q.set("body", f.BODY);
      return { kind: "action", action: "email", href: `mailto:${f.TO}${q.toString() ? `?${q}` : ""}`, label: f.TO };
    }
  }
  if (upper.startsWith("SMSTO:")) {
    const [num, ...msg] = s.slice(6).split(":");
    return { kind: "action", action: "sms", href: `sms:${num}${msg.length ? `?body=${encodeURIComponent(msg.join(":"))}` : ""}`, label: num };
  }

  let url: URL | null = null;
  try {
    url = new URL(s);
  } catch {
    url = null;
  }
  if (url) {
    const scheme = url.protocol.toLowerCase();
    if ((scheme === "http:" || scheme === "https:") && url.host) {
      const path = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
      const dl = DIGITAL_LINK.exec(path);
      if (dl) return { kind: "product", gtin: dl[1] };
      const segs = url.pathname.split("/").filter(Boolean);
      if (segs.length === 2 && segs[0] === "r" && /^[A-Za-z0-9_-]{8,40}$/.test(segs[1])) return { kind: "shared", token: segs[1] };
      return { kind: "link", url: url.toString(), host: url.host };
    }
    if (scheme === "tel:" && url.pathname) return { kind: "action", action: "phone", href: s, label: url.pathname };
    if (scheme === "mailto:" && url.pathname) return { kind: "action", action: "email", href: s, label: decodeURIComponent(url.pathname) };
    if ((scheme === "sms:" || scheme === "smsto:") && url.pathname) {
      const num = url.pathname.split(":")[0];
      return { kind: "action", action: "sms", href: `sms:${num}${url.search}`, label: num };
    }
    if (scheme === "geo:" && LATLNG.test(url.pathname)) {
      const ll = LATLNG.exec(url.pathname)![0];
      return { kind: "action", action: "geo", href: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(ll)}`, label: ll };
    }
  }
  return { kind: "text", text: s };
}
