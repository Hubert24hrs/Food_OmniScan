"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Clock, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { Badge, Button, Card, Chip, EmptyState, ErrorBox, inputCls, Page, SectionTitle, Skeleton } from "@/components/ui";

type RecipeSummary = { id: string; title: string; description: string | null; cuisine: string | null; region: string | null; servings: number; time_minutes: number | null; tags: string[]; diet_tags: string[]; ai_generated: boolean; mine: boolean };
const REGIONS = [["", "All"], ["NG", "Nigerian"], ["US", "American"], ["EU", "European"]];
const DIETS = ["vegan", "vegetarian", "gluten_free", "dairy_free", "high_protein"];

export default function RecipesPage() {
  const { me, activeProfile } = useAuth();
  const router = useRouter();
  const [q, setQ] = useState("");
  const [region, setRegion] = useState("");
  const [diet, setDiet] = useState("");
  const [mine, setMine] = useState(false);
  const query = new URLSearchParams({ ...(q ? { q } : {}), ...(region ? { region } : {}), ...(diet ? { diet } : {}), ...(mine ? { mine: "true" } : {}) }).toString();
  const list = useApi<RecipeSummary[]>(`/recipes?${query}`, [query]);
  const [ask, setAsk] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ id: string }>("/recipes/generate", { body: { request: ask, profile_id: activeProfile?.id, region: region || undefined } });
      router.push(`/recipes/${r.id}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Recipes" subtitle="Checked against your profile's allergies and diets. Nutrition is only shown as a labelled estimate.">
      <Card className="mb-4">
        <SectionTitle><span className="flex items-center gap-2"><Sparkles className="size-5 text-brand" /> Create a recipe with AI</span></SectionTitle>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input className={inputCls} placeholder="e.g. a quick dinner with beans, plantain and spinach" value={ask} onChange={(e) => setAsk(e.target.value)} maxLength={1000} aria-label="What would you like to cook?" />
          <Button onClick={generate} loading={busy} disabled={!me || ask.trim().length < 3}>{me ? "Create" : "Sign in to create"}</Button>
        </div>
        <p className="mt-2 text-xs text-muted">Follows {activeProfile ? `${activeProfile.name}'s` : "your"} allergies, avoided ingredients and diets. Included with Plus and above.</p>
        {error ? <div className="mt-3"><ErrorBox error={error} /></div> : null}
      </Card>

      <div className="mb-3 flex flex-col gap-2 sm:flex-row">
        <input className={inputCls} placeholder="Search recipes" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search recipes" />
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        {REGIONS.map(([k, l]) => <Chip key={k} active={region === k} onClick={() => setRegion(k)}>{l}</Chip>)}
        {DIETS.map((d) => <Chip key={d} active={diet === d} onClick={() => setDiet(diet === d ? "" : d)}>{d.replace("_", " ")}</Chip>)}
        {me && <Chip active={mine} onClick={() => setMine(!mine)}>My recipes</Chip>}
      </div>

      {list.error ? <ErrorBox error={list.error} onRetry={list.reload} /> : null}
      {!list.data ? <Skeleton className="h-40" /> : list.data.length === 0 ? <EmptyState title="No recipes found" body="Try another filter, or create one with AI." /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {list.data.map((r) => (
            <Link key={r.id} href={`/recipes/${r.id}`} className="card p-4 transition hover:border-brand">
              <p className="font-display font-bold">{r.title}</p>
              {r.description && <p className="mt-1 line-clamp-2 text-sm text-muted">{r.description}</p>}
              <div className="mt-2 flex flex-wrap gap-1.5">
                {r.cuisine && <Badge tone="brand">{r.cuisine}</Badge>}
                {r.time_minutes && <Badge><Clock className="size-3" /> {r.time_minutes} min</Badge>}
                {r.ai_generated && <Badge tone="amber">AI</Badge>}
                {r.diet_tags.slice(0, 2).map((d) => <Badge key={d} tone="green">{d.replace("_", " ")}</Badge>)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </Page>
  );
}
