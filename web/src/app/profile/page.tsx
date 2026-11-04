"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Bell, CreditCard, Download, Heart, History, ListChecks, LogOut, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { ProfileEditor } from "@/components/ProfileEditor";
import { Badge, Button, Card, ErrorBox, inputCls, Page, SectionTitle } from "@/components/ui";

type Sub = { id: string; kind: string; barcode: string; status: string; name: string; review_notes: string | null; created_at: string };

export default function ProfilePage() {
  const { me, profiles, activeProfile, refresh, logout, setActiveProfile } = useRequireAuth();
  const router = useRouter();
  const [editing, setEditing] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [confirm, setConfirm] = useState("");
  const subs = useApi<Sub[]>(me ? "/submissions/mine" : null);
  if (!me) return null;

  const editingProfile = profiles.find((p) => p.id === (editing || activeProfile?.id));

  const exportData = async () => {
    const data = await api("/me/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "food-omniscan-data.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Page title="Profile" subtitle={me.email} actions={<Badge tone="brand">{me.tier} plan</Badge>}>
      <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
        {[["/history", History, "History"], ["/saved", Heart, "Saved"], ["/lists", ListChecks, "Lists"], ["/notifications", Bell, "Alerts"], ["/subscription", CreditCard, "Plan"]].map(([href, Icon, l]) => {
          const I = Icon as typeof History;
          return <Link key={href as string} href={href as string} className="card flex items-center gap-2 p-3 text-sm font-semibold hover:border-brand/50"><I className="size-4 text-brand" />{l as string}</Link>;
        })}
      </div>

      <Card className="mb-4">
        <SectionTitle>Eater profiles</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {profiles.map((p) => (
            <button key={p.id} onClick={() => setEditing(p.id)} aria-pressed={editingProfile?.id === p.id} className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold ${editingProfile?.id === p.id ? "border-brand bg-brand-soft" : "border-line"}`}>
              <span className="size-3 rounded-full" style={{ background: p.avatar_color || "#0F766E" }} aria-hidden />
              {p.name} {p.is_active && <span className="text-xs text-brand">· active</span>}
            </button>
          ))}
        </div>
        <form className="mt-3 flex gap-2" onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try { await api("/profiles", { body: { name: newName || "Family member", avatar_color: "#B45309" } }); setNewName(""); await refresh(); } catch (err) { setError(err); }
        }}>
          <input className={inputCls} placeholder="Add a family member (e.g. Ada)" value={newName} onChange={(e) => setNewName(e.target.value)} aria-label="New profile name" />
          <Button type="submit" variant="secondary"><Plus className="size-4" /> Add</Button>
        </form>
        {error ? <div className="mt-3"><ErrorBox error={error} /></div> : null}
        {editingProfile && (
          <div className="mt-5 border-t border-line pt-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <p className="font-display text-lg font-bold">{editingProfile.name}&apos;s preferences</p>
              <div className="flex gap-2">
                {!editingProfile.is_active && <Button variant="secondary" onClick={() => setActiveProfile(editingProfile.id)}>Make active</Button>}
                {!editingProfile.is_primary && <Button variant="ghost" onClick={async () => { await api(`/profiles/${editingProfile.id}`, { method: "DELETE" }); setEditing(null); refresh(); }}>Remove</Button>}
              </div>
            </div>
            {me.consent_health_data ? <ProfileEditor key={editingProfile.id} profile={editingProfile} onSaved={refresh} /> : <p className="text-sm text-muted">Allow storage of health data in Privacy below to set allergies and diets.</p>}
          </div>
        )}
      </Card>

      <Card className="mb-4" id="notifications">
        <SectionTitle>Notifications</SectionTitle>
        <div className="grid gap-2 sm:grid-cols-2">
          {([["allergen_alerts", "Allergen alerts when I scan", true], ["recalls", "Recalls for products I've scanned", true], ["ingredient_alerts", "Watchlist ingredient alerts (Plus)", true], ["expiry", "Pantry expiry reminders (Plus)", true], ["weekly_report", "Weekly nutrition summary (Plus)", true], ["tips", "A weekly food tip", false]] as const).map(([k, label, def]) => (
            <label key={k} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={me.notification_prefs?.[k] ?? def} onChange={async (e) => { await api("/me", { method: "PATCH", body: { notification_prefs: { [k]: e.target.checked } } }); refresh(); }} />
              {label}
            </label>
          ))}
        </div>
      </Card>

      <Card className="mb-4" id="submissions">
        <SectionTitle>My product submissions</SectionTitle>
        {subs.data?.length ? (
          <ul className="divide-y divide-line text-sm">
            {subs.data.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-2">
                <span>{s.name || s.barcode} <span className="text-muted">· {s.kind.replace("_", " ")}</span>{s.review_notes && <span className="block text-xs text-muted">{s.review_notes}</span>}</span>
                <Badge tone={s.status === "approved" ? "green" : s.status === "rejected" ? "red" : "amber"}>{s.status}</Badge>
              </li>
            ))}
          </ul>
        ) : <p className="text-sm text-muted">No submissions yet. Add products that aren&apos;t found when you scan them.</p>}
      </Card>

      <Card>
        <SectionTitle>Privacy & data</SectionTitle>
        <label className="flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-1 size-4" checked={me.consent_health_data} onChange={async (e) => {
            if (!e.target.checked && !window.confirm("Withdrawing consent deletes all stored allergy, diet and avoid-list data for every profile. Continue?")) return;
            await api("/me", { method: "PATCH", body: { consent_health_data: e.target.checked } });
            refresh();
          }} />
          <span>Store allergy & diet information (sensitive health data) to personalize results</span>
        </label>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" onClick={exportData}><Download className="size-4" /> Export my data</Button>
          <Button variant="secondary" onClick={() => { logout(); router.push("/"); }}><LogOut className="size-4" /> Sign out</Button>
        </div>
        <div className="mt-6 rounded-xl border border-bad/30 p-4">
          <p className="font-semibold text-bad">Delete account</p>
          <p className="mt-1 text-sm text-muted">Permanently deletes your account, profiles, history, lists and diary. This can&apos;t be undone. Type DELETE to confirm.</p>
          <div className="mt-2 flex gap-2">
            <input className={inputCls} value={confirm} onChange={(e) => setConfirm(e.target.value)} aria-label="Type DELETE to confirm" />
            <Button variant="danger" disabled={confirm !== "DELETE"} onClick={async () => { await api("/me", { method: "DELETE", body: { confirm } }); logout(); router.push("/"); }}>Delete</Button>
          </div>
        </div>
      </Card>
    </Page>
  );
}
