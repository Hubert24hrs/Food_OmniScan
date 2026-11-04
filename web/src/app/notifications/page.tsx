"use client";

import Link from "next/link";
import { BellRing, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { EmptyState, ErrorBox, Page, Skeleton } from "@/components/ui";

type N = { id: string; kind: string; title: string; body: string; read: boolean; created_at: string; data: { product_id?: string; url?: string } };

export default function NotificationsPage() {
  const { me } = useRequireAuth();
  const n = useApi<N[]>(me ? "/notifications" : null);
  return (
    <Page title="Alerts" subtitle="Recalls for products you've scanned, submission updates and announcements.">
      {n.error ? <ErrorBox error={n.error} /> : null}
      {n.loading && <Skeleton className="h-20" />}
      {n.data?.length === 0 && <EmptyState title="You're all caught up" icon={<BellRing className="size-6" />} />}
      <ul className="space-y-2">
        {n.data?.map((x) => (
          <li key={x.id} className={`card flex gap-3 p-4 ${x.read ? "opacity-70" : ""}`}>
            {x.kind === "recall" ? <ShieldAlert className="size-5 shrink-0 text-bad" /> : <BellRing className="size-5 shrink-0 text-brand" />}
            <div className="flex-1">
              <p className="font-semibold">{x.title}</p>
              <p className="text-sm text-muted">{x.body}</p>
              <p className="mt-1 text-xs text-muted">{dateTime(x.created_at)}</p>
              <div className="mt-1 flex gap-3 text-sm">
                {x.data?.product_id && <Link className="font-semibold text-brand" href={`/product/${x.data.product_id}`}>View product</Link>}
                {x.data?.url && <a className="font-semibold text-brand" href={x.data.url} target="_blank" rel="noreferrer">Official notice</a>}
                {!x.read && <button className="text-muted" onClick={async () => { await api(`/notifications/${x.id}/read`, { method: "POST" }); n.reload(); }}>Mark read</button>}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </Page>
  );
}
