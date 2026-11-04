"use client";

import Link from "next/link";
import { useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Button, Card, EmptyState, ErrorBox, inputCls, Page, Skeleton } from "@/components/ui";

type Item = { id: string; text: string; quantity: string | null; checked: boolean; product_id: string | null };
type List = { id: string; name: string; shared_with_family: boolean; items: Item[] };

function ListCard({ list, onChange }: { list: List; onChange: (l: List | null) => void }) {
  const [text, setText] = useState("");
  const add = async () => {
    if (!text.trim()) return;
    onChange(await api<List>(`/shopping-lists/${list.id}/items`, { body: { text } }));
    setText("");
  };
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-lg font-bold">{list.name}</h2>
        <button aria-label={`Delete ${list.name}`} className="text-muted hover:text-bad" onClick={async () => { await api(`/shopping-lists/${list.id}`, { method: "DELETE" }); onChange(null); }}>
          <Trash2 className="size-4" />
        </button>
      </div>
      <ul className="space-y-1">
        {list.items.map((i) => (
          <li key={i.id} className="flex items-center gap-3 rounded-lg px-1 py-1.5">
            <input type="checkbox" className="size-5" checked={i.checked} aria-label={`Mark ${i.text} as bought`} onChange={async (e) => onChange(await api<List>(`/shopping-lists/${list.id}/items/${i.id}`, { method: "PATCH", body: { checked: e.target.checked } }))} />
            <span className={`flex-1 ${i.checked ? "text-muted line-through" : ""}`}>
              {i.product_id ? <Link href={`/product/${i.product_id}`} className="hover:text-brand">{i.text}</Link> : i.text}
              {i.quantity && <span className="text-muted"> × {i.quantity}</span>}
            </span>
            <button aria-label={`Remove ${i.text}`} className="text-muted hover:text-bad" onClick={async () => onChange(await api<List>(`/shopping-lists/${list.id}/items/${i.id}`, { method: "DELETE" }))}>
              <Trash2 className="size-4" />
            </button>
          </li>
        ))}
      </ul>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); add(); }}>
        <input className={inputCls} placeholder="Add an item" value={text} onChange={(e) => setText(e.target.value)} aria-label="New item" />
        <Button type="submit" variant="secondary">Add</Button>
      </form>
    </Card>
  );
}

export default function ListsPage() {
  const { me } = useRequireAuth();
  const lists = useApi<List[]>(me ? "/shopping-lists" : null);
  const [name, setName] = useState("");
  const [error, setError] = useState<unknown>(null);
  return (
    <Page title="Shopping lists">
      <form className="mb-4 flex gap-2" onSubmit={async (e) => {
        e.preventDefault();
        setError(null);
        try {
          const l = await api<List>("/shopping-lists", { body: { name: name || "Groceries" } });
          lists.setData([l, ...(lists.data || [])]);
          setName("");
        } catch (err) { setError(err); }
      }}>
        <input className={inputCls} placeholder="New list name" value={name} onChange={(e) => setName(e.target.value)} aria-label="New list name" />
        <Button type="submit">Create</Button>
      </form>
      {error || lists.error ? <ErrorBox error={error || lists.error} /> : null}
      {lists.loading && <Skeleton className="h-40" />}
      {lists.data?.length === 0 && <EmptyState title="No lists yet" body="Create a list, or use “Add to list” on any product." />}
      <div className="grid gap-4 md:grid-cols-2">
        {lists.data?.map((l) => (
          <ListCard key={l.id} list={l} onChange={(nl) => lists.setData(nl ? lists.data!.map((x) => (x.id === l.id ? nl : x)) : lists.data!.filter((x) => x.id !== l.id))} />
        ))}
      </div>
    </Page>
  );
}
