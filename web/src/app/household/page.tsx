"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, ErrorBox, inputCls, LinkButton, Page, SectionTitle, Skeleton, UpgradeCard } from "@/components/ui";

type Member = { id: string; email: string; name: string | null; role: string; status: string };
type Resp = { household: { id: string; name: string; owner_user_id: string; members: Member[] } | null; invites: { id: string; household: string }[]; can_create: boolean };

export default function HouseholdPage() {
  const { me } = useRequireAuth();
  const h = useApi<Resp>(me ? "/household" : null);
  const [name, setName] = useState("Our home");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<unknown>(null);
  const run = async (fn: () => Promise<unknown>) => { setError(null); try { await fn(); h.reload(); } catch (e) { setError(e); } };
  const hh = h.data?.household;
  const owner = hh && me && hh.owner_user_id === me.id;

  return (
    <Page title="Household" subtitle="Share a pantry, shopping lists and a grocery budget with the people you live with.">
      {h.error ? <ErrorBox error={h.error} onRetry={h.reload} /> : !h.data ? <Skeleton className="h-32" /> : (
        <div className="space-y-4">
          {h.data.invites.map((i) => (
            <Card key={i.id} className="flex flex-wrap items-center justify-between gap-2">
              <p>You&apos;re invited to <b>{i.household}</b>.</p>
              <Button onClick={() => run(() => api(`/household/invites/${i.id}/accept`, { method: "POST" }))}>Join</Button>
            </Card>
          ))}
          {hh ? (
            <Card>
              <SectionTitle>{hh.name}</SectionTitle>
              <ul className="divide-y divide-line text-sm">
                {hh.members.map((m) => (
                  <li key={m.id} className="flex items-center gap-2 py-2">
                    <span className="flex-1">{m.name || m.email}<span className="block text-xs text-muted">{m.email}</span></span>
                    <Badge tone={m.status === "active" ? "green" : "amber"}>{m.role === "owner" ? "Owner" : m.status}</Badge>
                    {(owner || m.email === me?.email) && (
                      <Button variant="ghost" className="text-bad" onClick={() => run(() => api(`/household/members/${m.id}`, { method: "DELETE" }))}>
                        {m.email === me?.email ? (m.role === "owner" ? "Close household" : "Leave") : "Remove"}
                      </Button>
                    )}
                  </li>
                ))}
              </ul>
              {owner && (
                <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); run(async () => { await api("/household/invite", { body: { email } }); setEmail(""); }); }}>
                  <input type="email" required className={inputCls} placeholder="Email address to invite" value={email} onChange={(e) => setEmail(e.target.value)} aria-label="Email to invite" />
                  <Button type="submit">Invite</Button>
                </form>
              )}
              <p className="mt-3 text-xs text-muted">Members see shared shopping lists, pantry items and the household budget. Food diaries and health profiles stay private.</p>
            </Card>
          ) : h.data.can_create ? (
            <Card>
              <SectionTitle>Create a household</SectionTitle>
              <div className="flex gap-2">
                <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} aria-label="Household name" />
                <Button onClick={() => run(() => api("/household", { body: { name } }))}>Create</Button>
              </div>
            </Card>
          ) : (
            <UpgradeCard title="Household sharing is part of the Family plan" error={{ message: "Ask someone on the Family plan to invite you, or upgrade to create your own household." }} />
          )}
          <LinkButton variant="secondary" href="/lists">Open shopping lists</LinkButton>
        </div>
      )}
      {error ? <div className="mt-4"><ErrorBox error={error} /></div> : null}
    </Page>
  );
}
