// US-first formatting (en-US, USD, US customary alongside metric).

export const nf = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "—"
    : new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(v);

export const money = (v: number, currency = "USD", locale = "en-US") =>
  new Intl.NumberFormat(locale, { style: "currency", currency, currencyDisplay: "narrowSymbol" }).format(v);

export const gToOz = (g: number) => g / 28.3495;
export const mlToFlOz = (ml: number) => ml / 29.5735;

export const dateTime = (iso: string) =>
  new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));

export const relDays = (iso: string) => {
  const d = (Date.now() - new Date(iso).getTime()) / 86400000;
  if (d < 1) return "Today";
  if (d < 2) return "Yesterday";
  return `${Math.floor(d)} days ago`;
};

export const prettyTag = (t?: string | null) => (t ? t.replace(/^[a-z]{2}:/, "").replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "");

export const scoreColorVar: Record<string, string> = {
  green: "var(--good)",
  amber: "var(--warn)",
  red: "var(--bad)",
  grey: "var(--grey)",
};
