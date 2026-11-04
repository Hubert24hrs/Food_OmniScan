"use client";

import Link from "next/link";
import { useState } from "react";
import { useApi } from "@/lib/useApi";
import { Badge, Chip, ErrorBox, Page, Skeleton } from "@/components/ui";

type Article = { slug: string; title: string; summary: string; topic: string; region: string | null };
const TOPICS = [["", "All"], ["nutrition", "Nutrition"], ["ingredients", "Ingredients"], ["processing", "Processing"], ["safety", "Food safety"], ["african", "African foods"]];

export default function LearnPage() {
  const [topic, setTopic] = useState("");
  const a = useApi<Article[]>(`/articles${topic ? `?topic=${topic}` : ""}`, [topic]);
  return (
    <Page title="Learn" subtitle="Short guides with their sources, written to explain rather than alarm.">
      <div className="mb-4 flex flex-wrap gap-2">{TOPICS.map(([k, l]) => <Chip key={k} active={topic === k} onClick={() => setTopic(k)}>{l}</Chip>)}</div>
      {a.error ? <ErrorBox error={a.error} onRetry={a.reload} /> : !a.data ? <Skeleton className="h-40" /> : (
        <div className="grid gap-3 sm:grid-cols-2">
          {a.data.map((x) => (
            <Link key={x.slug} href={`/learn/${x.slug}`} className="card p-4 hover:border-brand">
              <Badge tone="brand" className="capitalize">{x.topic}</Badge>
              <p className="mt-2 font-display font-bold">{x.title}</p>
              <p className="mt-1 text-sm text-muted">{x.summary}</p>
            </Link>
          ))}
        </div>
      )}
    </Page>
  );
}
