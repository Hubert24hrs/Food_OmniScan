"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/lib/useRequireAuth";
import { Badge, Button, Card, ErrorBox, inputCls, Page } from "@/components/ui";

type Msg = { role: "user" | "assistant"; content: string; sources?: { key: string; title: string; url: string | null }[] };

function Assistant() {
  const { me, activeProfile } = useRequireAuth();
  const productId = useSearchParams().get("product");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const ask = async (question: string) => {
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    const history = msgs.map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: "user", content: question }]);
    setQ("");
    try {
      const r = await api<{ answer: string; sources: Msg["sources"]; disclaimer: string }>("/assistant/ask", {
        body: { question, product_ids: productId ? [productId] : [], history, profile_id: activeProfile?.id },
      });
      setMsgs((m) => [...m, { role: "assistant", content: r.answer, sources: r.sources }]);
    } catch (e) {
      setError(e);
      setMsgs((m) => m.slice(0, -1));
    } finally {
      setBusy(false);
    }
  };

  if (!me) return null;
  return (
    <Page title="Nutrition assistant" subtitle="Answers grounded in our product data and cited sources. General information, not medical advice.">
      {productId && <Badge tone="brand" className="mb-3">Asking about the product you were viewing</Badge>}
      <Card className="min-h-80 space-y-4">
        {msgs.length === 0 && (
          <div className="space-y-2 text-sm text-muted">
            <p className="flex items-center gap-2 font-semibold text-ink"><Sparkles className="size-4 text-brand" /> Try asking:</p>
            {(productId
              ? ["Why did this product get its score?", "Is this OK for someone avoiding added sugar?", "What does each additive do?"]
              : ["What's the difference between total and added sugars?", "Is Red 40 banned anywhere?", "Give me a high-protein breakfast idea"]
            ).map((s) => (
              <button key={s} onClick={() => ask(s)} className="block rounded-xl border border-line px-3 py-2 text-left hover:border-brand">{s}</button>
            ))}
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} className={m.role === "user" ? "ml-auto max-w-[85%] rounded-2xl bg-brand px-4 py-2 text-white dark:text-[#06201d]" : "max-w-[90%] rounded-2xl bg-surface-2 px-4 py-3"}>
            <p className="whitespace-pre-wrap text-sm">{m.content}</p>
            {m.sources && m.sources.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {m.sources.map((s) => <a key={s.key} href={`/sources#${s.key}`} className="rounded-full bg-surface px-2 py-0.5 text-xs text-muted underline">{s.key}</a>)}
              </div>
            )}
            {m.role === "assistant" && <p className="mt-2 text-[11px] text-muted">AI-generated · check the label · not medical advice</p>}
          </div>
        ))}
        {busy && <p className="text-sm text-muted" role="status">Thinking…</p>}
      </Card>
      {error ? <div className="mt-3"><ErrorBox error={error} /></div> : null}
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <input className={inputCls} placeholder="Ask about ingredients, nutrients, swaps…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Your question" maxLength={2000} />
        <Button type="submit" loading={busy} aria-label="Send"><Send className="size-4" /></Button>
      </form>
      <p className="mt-2 text-xs text-muted">Conversations aren&apos;t stored on our servers. Questions are processed by Google Gemini.</p>
    </Page>
  );
}

export default function AssistantPage() {
  return <Suspense><Assistant /></Suspense>;
}
