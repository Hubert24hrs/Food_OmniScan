"use client";

import { AdminAnalytics, AdminArticles, AdminReviews } from "@/components/AdminContent";
import { useState } from "react";
import { api, assetUrl } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, EmptyState, ErrorBox, Field, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type Stats = Record<string, unknown> & { users: number; products: number; pending_submissions: number; scans_30d: number; scan_success_rate_30d: number | null; ai_cost_30d_usd: number; active_methodology: string; ingredients_pending_verification: number; products_by_source: Record<string, number>; subscriptions_by_tier: Record<string, number> };
type Sub = { id: string; kind: string; barcode: string; payload: Record<string, unknown> & { name?: string; brand?: string; ingredients_text?: string; nutrition?: Record<string, number> }; images: string[]; ocr_confidence: number | null; created_at: string };
type Method = { version: string; name: string; is_active: boolean; notes: string; published_at: string; config: Record<string, unknown> };
type Log = { id: string; action: string; entity: string; entity_id: string; note: string | null; created_at: string; actor_id: string };
type U = { id: string; email: string; role: string; is_active: boolean; country: string; created_at: string };

const TABS = ["Overview", "Analytics", "Submissions", "Reviews", "Scoring", "Recalls", "Articles", "Users", "Audit log"] as const;

export default function AdminPage() {
  const { me } = useRequireAuth();
  const [tab, setTab] = useState<(typeof TABS)[number]>("Overview");
  if (!me) return null;
  if (me.role !== "admin" && me.role !== "moderator") return <Page><EmptyState title="Admins only" body="You don't have access to the admin console." /></Page>;
  const visible = me.role === "admin" ? TABS : (["Overview", "Submissions", "Reviews"] as const);
  return (
    <Page title="Admin console" subtitle={`Signed in as ${me.role}. Every action is audit-logged.`}>
      <div className="mb-4 flex flex-wrap gap-2" role="tablist">
        {visible.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`min-h-10 rounded-xl px-4 text-sm font-semibold ${tab === t ? "btn-brand" : "border border-line"}`}>{t}</button>
        ))}
      </div>
      {tab === "Overview" && <Overview />}
      {tab === "Analytics" && <AdminAnalytics />}
      {tab === "Articles" && <AdminArticles />}
      {tab === "Submissions" && <Submissions />}
      {tab === "Reviews" && <AdminReviews />}
      {tab === "Scoring" && <Scoring />}
      {tab === "Recalls" && <Recalls />}
      {tab === "Users" && <Users />}
      {tab === "Audit log" && <Audit />}
    </Page>
  );
}

function Overview() {
  const s = useApi<Stats>("/admin/stats");
  const failed = useApi<{ barcode: string; status: string; count: number }[]>("/admin/scans/failed?limit=15");
  if (s.error) return <ErrorBox error={s.error} />;
  if (!s.data) return <Skeleton className="h-40" />;
  const d = s.data;
  const tiles: [string, string | number][] = [
    ["Users", d.users], ["Products", d.products], ["Pending submissions", d.pending_submissions], ["Scans (30d)", d.scans_30d],
    ["Scan success", d.scan_success_rate_30d === null ? "—" : `${Math.round(d.scan_success_rate_30d * 100)}%`], ["AI cost (30d)", `$${d.ai_cost_30d_usd.toFixed(2)}`],
    ["Ingredients to verify", d.ingredients_pending_verification], ["Active methodology", d.active_methodology],
  ];
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map(([l, v]) => <Card key={l}><p className="text-xs text-muted">{l}</p><p className="mt-1 font-display text-2xl font-extrabold tabular-nums">{v}</p></Card>)}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card><SectionTitle>Products by source</SectionTitle>{Object.entries(d.products_by_source).map(([k, v]) => <p key={k} className="flex justify-between text-sm"><span>{k}</span><b>{v}</b></p>)}</Card>
        <Card><SectionTitle>Most-failed barcodes</SectionTitle>
          {failed.data?.length ? failed.data.map((f) => <p key={f.barcode + f.status} className="flex justify-between text-sm"><span className="font-mono">{f.barcode}</span><span>{f.status} × {f.count}</span></p>) : <p className="text-sm text-muted">None yet.</p>}
        </Card>
      </div>
    </div>
  );
}

function Submissions() {
  const subs = useApi<Sub[]>("/admin/submissions");
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [err, setErr] = useState<unknown>(null);
  const review = async (id: string, action: string) => {
    setErr(null);
    try {
      await api(`/admin/submissions/${id}/review`, { body: { action, notes: notes[id] || null } });
      subs.reload();
    } catch (e) { setErr(e); }
  };
  if (subs.loading) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-3">
      {err ? <ErrorBox error={err} /> : null}
      {!subs.data?.length && <EmptyState title="Queue is empty" body="New product submissions and correction reports show up here." />}
      {subs.data?.map((s) => (
        <Card key={s.id}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-display font-bold">{s.payload.name || `Report on ${s.barcode}`} <span className="text-sm font-normal text-muted">{s.payload.brand}</span></p>
            <div className="flex gap-1"><Badge tone="grey">{s.kind}</Badge><Badge tone="grey">{s.barcode}</Badge>{s.ocr_confidence !== null && <Badge tone={s.ocr_confidence > 0.8 ? "green" : "amber"}>OCR {Math.round(s.ocr_confidence * 100)}%</Badge>}</div>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {s.images.map((i) => <img key={i} src={assetUrl(i)} alt="Submitted label" className="h-32 rounded-xl border border-line" />)}
          </div>
          <pre className="mt-3 max-h-48 overflow-auto rounded-xl bg-surface-2 p-3 text-xs">{JSON.stringify(s.payload, null, 2)}</pre>
          <div className="mt-3 flex flex-wrap gap-2">
            <input className={`${inputCls} flex-1`} placeholder="Review notes (sent to contributor)" value={notes[s.id] || ""} onChange={(e) => setNotes({ ...notes, [s.id]: e.target.value })} aria-label="Review notes" />
            <Button onClick={() => review(s.id, "approve")}>Approve</Button>
            <Button variant="secondary" onClick={() => review(s.id, "needs_info")}>Needs info</Button>
            <Button variant="danger" onClick={() => review(s.id, "reject")}>Reject</Button>
          </div>
          <p className="mt-2 text-xs text-muted">Submitted {dateTime(s.created_at)}. Check values against the photos before approving.</p>
        </Card>
      ))}
    </div>
  );
}

function Scoring() {
  const ms = useApi<Method[]>("/admin/methodologies");
  const [draft, setDraft] = useState("");
  const [version, setVersion] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState<unknown>(null);
  const active = ms.data?.find((m) => m.is_active);
  return (
    <div className="space-y-4">
      {err ? <ErrorBox error={err} /> : null}
      <Card>
        <SectionTitle>Versions</SectionTitle>
        <ul className="divide-y divide-line text-sm">
          {ms.data?.map((m) => (
            <li key={m.version} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span><b>{m.version}</b> · {m.name} <span className="block text-xs text-muted">{m.notes}</span></span>
              {m.is_active ? <Badge tone="green">Active</Badge> : <Button variant="secondary" onClick={async () => { await api(`/admin/methodologies/${m.version}/activate`, { method: "POST" }); ms.reload(); }}>Activate</Button>}
            </li>
          ))}
        </ul>
      </Card>
      <Card className="space-y-3">
        <SectionTitle>Publish a new version</SectionTitle>
        <p className="text-sm text-muted">Versions are immutable. Start from the active config, edit the JSON, and publish under a new version (e.g. 2026.12-us.2). The server validates it and dry-runs the engine.</p>
        <Button variant="secondary" onClick={() => setDraft(JSON.stringify(active?.config, null, 2))}>Load active config</Button>
        <textarea className="min-h-72 w-full rounded-xl border border-line bg-surface p-3 font-mono text-xs" value={draft} onChange={(e) => setDraft(e.target.value)} aria-label="Methodology JSON" />
        <div className="grid gap-2 sm:grid-cols-2">
          <Field label="Version"><input className={inputCls} value={version} onChange={(e) => setVersion(e.target.value)} placeholder="2026.12-us.2" /></Field>
          <Field label="Release notes"><input className={inputCls} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
        </div>
        <Button onClick={async () => {
          setErr(null);
          try {
            const cfg = JSON.parse(draft);
            await api("/admin/methodologies", { body: { version, name: cfg.name || "Food omniScan Score", config: cfg, notes: note, activate: false } });
            ms.reload();
          } catch (e) { setErr(e); }
        }} disabled={!draft || !version || !note}>Publish (inactive)</Button>
      </Card>
    </div>
  );
}

function Recalls() {
  const [f, setF] = useState({ title: "", reason: "", hazard: "undeclared_allergen", jurisdiction: "US", authority: "FDA", barcode: "", url: "", recall_date: "" });
  const [res, setRes] = useState<string | null>(null);
  const [err, setErr] = useState<unknown>(null);
  return (
    <Card className="space-y-3">
      <SectionTitle>Publish a verified recall</SectionTitle>
      <p className="text-sm text-muted">Only enter recalls from an official notice (FDA, USDA FSIS, FSA, EU RASFF, NAFDAC). Users who scanned the product are notified.</p>
      <div className="grid gap-2 sm:grid-cols-2">
        {(Object.keys(f) as (keyof typeof f)[]).map((k) => (
          <Field key={k} label={k.replace("_", " ")}><input className={inputCls} type={k === "recall_date" ? "date" : "text"} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></Field>
        ))}
      </div>
      {err ? <ErrorBox error={err} /> : null}
      {res && <p className="text-sm text-good">{res}</p>}
      <Button disabled={!f.title || !f.reason} onClick={async () => {
        setErr(null);
        try {
          const r = await api<{ notified_users: number }>("/admin/recalls", { body: { ...f, barcode: f.barcode || null, url: f.url || null, recall_date: f.recall_date || null } });
          setRes(`Recall published; ${r.notified_users} user(s) notified.`);
        } catch (e) { setErr(e); }
      }}>Publish recall</Button>
    </Card>
  );
}

function Users() {
  const [q, setQ] = useState("");
  const users = useApi<U[]>(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`, [q]);
  const [err, setErr] = useState<unknown>(null);
  const setRole = async (u: U, role: string) => {
    const reason = window.prompt(`Reason for changing ${u.email} to ${role}?`);
    if (!reason) return;
    setErr(null);
    try { await api(`/admin/users/${u.id}`, { method: "PATCH", body: { role, reason } }); users.reload(); } catch (e) { setErr(e); }
  };
  return (
    <Card>
      <input className={inputCls} placeholder="Search by email" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search users" />
      {err ? <div className="mt-2"><ErrorBox error={err} /></div> : null}
      <ul className="mt-3 divide-y divide-line text-sm">
        {users.data?.map((u) => (
          <li key={u.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span>{u.email} <span className="text-muted">· {u.country} · {new Date(u.created_at).toLocaleDateString("en-US")}</span></span>
            <select className="rounded-lg border border-line bg-surface px-2 py-1" value={u.role} onChange={(e) => setRole(u, e.target.value)} aria-label={`Role for ${u.email}`}>
              {["user", "contributor", "moderator", "admin"].map((r) => <option key={r}>{r}</option>)}
            </select>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function Audit() {
  const logs = useApi<Log[]>("/admin/audit-logs?limit=200");
  return (
    <Card>
      {logs.error ? <ErrorBox error={logs.error} /> : null}
      <ul className="divide-y divide-line text-sm">
        {logs.data?.map((l) => (
          <li key={l.id} className="py-2">
            <b>{l.action}</b> · {l.entity} {l.entity_id && <span className="font-mono text-xs">{l.entity_id.slice(0, 12)}</span>}
            <span className="block text-xs text-muted">{dateTime(l.created_at)} · actor {l.actor_id.slice(0, 8)}{l.note ? ` · ${l.note}` : ""}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
