"use client";

import { useParams } from "next/navigation";
import { useApi } from "@/lib/useApi";
import { SourceList, type Source } from "@/components/SourceList";
import { Card, ErrorBox, Page, SectionTitle, Skeleton } from "@/components/ui";

type Article = { slug: string; title: string; summary: string; body: string; topic: string; sources: Source[] };

export default function ArticlePage() {
  const { slug } = useParams<{ slug: string }>();
  const a = useApi<Article>(`/articles/${slug}`);
  if (a.error) return <Page><ErrorBox error={a.error} /></Page>;
  if (!a.data) return <Page><Skeleton className="h-60" /></Page>;
  return (
    <Page title={a.data.title} subtitle={a.data.summary}>
      <article className="card max-w-3xl space-y-3 p-5 leading-relaxed">
        {a.data.body.split("\n\n").map((para) => <p key={para.slice(0, 40)} className="whitespace-pre-line">{para}</p>)}
      </article>
      {a.data.sources.length > 0 && (
        <Card className="mt-4 max-w-3xl">
          <SectionTitle>Sources</SectionTitle>
          <SourceList sources={a.data.sources} />
        </Card>
      )}
    </Page>
  );
}
