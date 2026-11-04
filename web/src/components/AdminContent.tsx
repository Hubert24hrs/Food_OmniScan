"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Badge, Button, Card, ErrorBox, Field, inputCls, SectionTitle, Skeleton } from "./ui";

type Analytics = {
  days: number;
  scans_by_day: { day: string; scans: number }[];
  active_scanners: number;
  signups_by_day: { day: string; users: number }[];
  top_products: { id: string; name: string | null; brand: string | null; scans: number }[];
  top_missing_barcodes: { barcode: string; scans: number }[];
  feature_usage: { feature: string; uses: number; est_cost_usd: number }[];
  diary_entries: number;
  pantry_items: number;
  recipes_user_or_ai: number;
};
type Article = { slug: string; title: string; summary: string; body: string; topic: string; region: string | null; source_keys: string[]; status: string };

export function AdminAnalytics() {
  const [days, setDays] = useState(30);
  const a = useApi<Analytics>(`/admin/analytics?days=${days}`, [days]);
  const [jobs, setJobs] = useState<string | null>(null);
  if (a.error) return <ErrorBox error={a.error} onRetry={a.reload} />;
  if (!a.data) return <Skeleton className="h-60" />;
  const x = a.data;
  const max = Math.max(1, ...x.scans_by_day.map((d) => d.scans));
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {[7, 30, 90].map((d) => <Button key={d} variant={d === days ? "primary" : "secondary"} onClick={() => setDays(d)}>{d} days</Button>)}
        <Button variant="secondary" onClick={async () => setJobs(JSON.stringify(await api("/admin/jobs/daily", { method: "POST" })))}>Run daily jobs</Button>
        {jobs && <span className="text-xs text-muted">Done: {jobs}</span>}
      </div>
      <div className="grid gap-3 sm:grid-cols-4">
        {[["Active scanners", x.active_scanners], ["New users", x.signups_by_day.reduce((n, d) => n + d.users, 0)], ["Diary entries", x.diary_entries], ["Pantry items", x.pantry_items]].map(([l, v]) => (
          <Card key={l as string}><p className="text-xs text-muted">{l}</p><p className="font-display text-2xl font-extrabold tabular-nums">{v}</p></Card>
        ))}
      </div>
      <Card>
        <SectionTitle>Scans per day</SectionTitle>
        <div className="flex h-28 items-end gap-1" role="img" aria-label="Scans per day">
          {x.scans_by_day.map((d) => <div key={d.day} className="flex-1 rounded-t bg-brand" style={{ height: `${(d.scans / max) * 100}%` }} title={`${d.day}: ${d.scans}`} />)}
        </div>
      </Card>
      <div className="grid gap-4 md:grid-cols-3">
        <Card><SectionTitle>Popular products</SectionTitle><ol className="space-y-1 text-sm">{x.top_products.map((p) => <li key={p.id} className="flex justify-between gap-2"><span className="truncate">{p.name || "Unnamed"}</span><span className="tabular-nums text-muted">{p.scans}</span></li>)}</ol></Card>
        <Card><SectionTitle>Most-scanned missing barcodes</SectionTitle><ol className="space-y-1 text-sm">{x.top_missing_barcodes.map((p) => <li key={p.barcode} className="flex justify-between"><span className="font-mono">{p.barcode}</span><span className="tabular-nums text-muted">{p.scans}</span></li>)}</ol></Card>
        <Card><SectionTitle>Feature usage</SectionTitle><ul className="space-y-1 text-sm">{x.feature_usage.map((f) => <li key={f.feature} className="flex justify-between gap-2"><span>{f.feature.replace(/_/g, " ")}</span><span className="tabular-nums text-muted">{f.uses} · ${f.est_cost_usd.toFixed(2)}</span></li>)}</ul></Card>
      </div>
    </div>
  );
}

const blank: Article = { slug: "", title: "", summary: "", body: "", topic: "nutrition", region: null, source_keys: [], status: "draft" };

type Reported = { id: string; product_id: string; rating: number; title: string | null; body: string | null; status: string; reports: number; reasons: string[] };

/** Reviews people reported. Three reports hide a review until a moderator publishes or hides it. */
export function AdminReviews() {
  const q = useApi<Reported[]>("/admin/reviews/reported");
  const [error, setError] = useState<unknown>(null);
  const act = async (id: string, action: "publish" | "hide") => {
    setError(null);
    try {
      await api(`/admin/reviews/${id}/moderate`, { body: { action } });
      q.reload();
    } catch (e) {
      setError(e);
    }
  };
  if (q.loading) return <Skeleton className="h-32" />;
  if (q.error) return <ErrorBox error={q.error} onRetry={q.reload} />;
  return (
    <div className="space-y-3">
      {error ? <ErrorBox error={error} /> : null}
      {!q.data?.length && <p className="text-sm text-muted">No reported reviews.</p>}
      {q.data?.map((r) => (
        <Card key={r.id} className="text-sm">
          <p className="font-semibold">
            {r.reports} report(s) · {r.reasons.join(", ")} <Badge tone={r.status === "hidden" ? "red" : "grey"}>{r.status}</Badge>
          </p>
          <p className="mt-1">{"★".repeat(r.rating)} {r.title}</p>
          {r.body && <p className="mt-1 text-muted">{r.body}</p>}
          <div className="mt-2 flex gap-2">
            <Button variant="secondary" onClick={() => act(r.id, "publish")}>Keep published</Button>
            <Button variant="danger" onClick={() => act(r.id, "hide")}>Hide</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}

export function AdminArticles() {
  const list = useApi<Article[]>("/admin/articles");
  const [edit, setEdit] = useState<Article | null>(null);
  const [error, setError] = useState<unknown>(null);
  const save = async () => {
    if (!edit) return;
    setError(null);
    try {
      await api(`/admin/articles/${edit.slug}`, { method: "PUT", body: edit });
      setEdit(null);
      list.reload();
    } catch (e) { setError(e); }
  };
  return (
    <div className="grid gap-4 md:grid-cols-[1fr_1.3fr]">
      <Card>
        <SectionTitle action={<Button variant="secondary" onClick={() => setEdit({ ...blank })}>New</Button>}>Articles</SectionTitle>
        {!list.data ? <Skeleton className="h-32" /> : (
          <ul className="divide-y divide-line text-sm">
            {list.data.map((a) => (
              <li key={a.slug}><button className="flex w-full items-center gap-2 py-2 text-left" onClick={() => setEdit(a)}>
                <span className="flex-1">{a.title}</span><Badge tone={a.status === "published" ? "green" : "amber"}>{a.status}</Badge>
              </button></li>
            ))}
          </ul>
        )}
      </Card>
      {edit && (
        <Card className="space-y-2">
          <Field label="Slug" hint="lowercase-with-dashes; can't be changed after publishing"><input className={inputCls} value={edit.slug} onChange={(e) => setEdit({ ...edit, slug: e.target.value })} /></Field>
          <Field label="Title"><input className={inputCls} value={edit.title} onChange={(e) => setEdit({ ...edit, title: e.target.value })} /></Field>
          <Field label="Summary"><input className={inputCls} value={edit.summary} onChange={(e) => setEdit({ ...edit, summary: e.target.value })} /></Field>
          <Field label="Body" hint="Blank lines separate paragraphs."><textarea className={`${inputCls} min-h-48 py-2`} value={edit.body} onChange={(e) => setEdit({ ...edit, body: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-2">
            <Field label="Topic"><select className={inputCls} value={edit.topic} onChange={(e) => setEdit({ ...edit, topic: e.target.value })}>{["nutrition", "processing", "ingredients", "safety", "african", "announcement"].map((t) => <option key={t}>{t}</option>)}</select></Field>
            <Field label="Status"><select className={inputCls} value={edit.status} onChange={(e) => setEdit({ ...edit, status: e.target.value })}><option>draft</option><option>published</option></select></Field>
          </div>
          <Field label="Source keys" hint="Comma-separated keys from the sources library"><input className={inputCls} value={edit.source_keys.join(", ")} onChange={(e) => setEdit({ ...edit, source_keys: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} /></Field>
          {error ? <ErrorBox error={error} /> : null}
          <div className="flex gap-2"><Button onClick={save}>Save</Button><Button variant="ghost" onClick={() => setEdit(null)}>Cancel</Button></div>
        </Card>
      )}
    </div>
  );
}
