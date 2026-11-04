// Typed fetch wrapper for the Food omniScan API. All secrets live on the server.

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");
export const API_ORIGIN = API_URL.replace(/\/api\/v1$/, "");
const TOKEN_KEY = "omniscan.token";

export class ApiError extends Error {
  status: number;
  code?: string;
  detail: unknown;
  constructor(status: number, message: string, code?: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export function getToken(): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode): session stays in memory only */
  }
}

type Opts = { method?: string; body?: unknown; form?: FormData; query?: Record<string, string | number | boolean | string[] | undefined | null>; signal?: AbortSignal };

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const url = new URL(API_URL + path);
  for (const [k, v] of Object.entries(opts.query || {})) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, x));
    else url.searchParams.set(k, String(v));
  }
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (opts.form) body = opts.form;
  else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }
  let res: Response;
  try {
    res = await fetch(url, { method: opts.method || (body ? "POST" : "GET"), headers, body, signal: opts.signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "Can't reach Food omniScan. Check your connection and try again.", "network_error");
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? safeJson(text) : null;
  if (!res.ok) {
    const d = (data as { detail?: unknown })?.detail;
    let message = `Request failed (${res.status})`;
    let code: string | undefined;
    if (typeof d === "string") message = d;
    else if (d && typeof d === "object") {
      const o = d as { message?: string; code?: string; errors?: { msg: string; loc: string[] }[] };
      code = o.code;
      message = o.message || (o.errors ? o.errors.map((e) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join("; ") : message);
    }
    if (res.status === 401 && token) setToken(null);
    throw new ApiError(res.status, message, code, d);
  }
  return data as T;
}

function safeJson(t: string): unknown {
  try {
    return JSON.parse(t);
  } catch {
    return t;
  }
}

export function assetUrl(u?: string | null): string | undefined {
  if (!u) return undefined;
  return u.startsWith("/api/") ? API_ORIGIN + u : u;
}
