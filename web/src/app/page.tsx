"use client";

import Link from "next/link";
import { ArrowRight, Bell, BookOpen, ChefHat, Compass, GitCompare, ListChecks, MessageCircle, ScanLine, Search, ShieldCheck, Sparkles, Users } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/useApi";
import { Badge, Card, EmptyState, LinkButton, Page, SectionTitle, Skeleton } from "@/components/ui";
import { ProductCard } from "@/components/ProductCard";
import { relDays } from "@/lib/format";
import type { ProductSummary } from "@/lib/types";
import { LogoMark } from "@/components/Logo";

type Hist = { id: string; product: ProductSummary; last_scanned_at: string; scan_count: number };

export default function Home() {
  const { me, loading, activeProfile } = useAuth();
  if (loading) return <Page><Skeleton className="h-40 w-full" /></Page>;
  return me ? <Dashboard name={me.display_name || "there"} profileName={activeProfile?.name} /> : <Landing />;
}

function Dashboard({ name, profileName }: { name: string; profileName?: string }) {
  const hist = useApi<Hist[]>("/history?limit=6");
  const notes = useApi<{ id: string; read: boolean }[]>("/notifications?unread_only=true");
  const { activeProfile } = useAuth();
  const restrictions = (activeProfile?.allergens.length || 0) + (activeProfile?.diets.length || 0) + (activeProfile?.avoid.length || 0);
  return (
    <Page>
      <section className="card relative overflow-hidden bg-gradient-to-br from-brand to-brand-strong p-6 text-white dark:text-[#06201d]">
        <p className="text-sm font-semibold opacity-90">Hi {name} 👋</p>
        <h1 className="mt-1 font-display text-2xl font-extrabold sm:text-3xl">What are you eating today?</h1>
        <p className="mt-1 max-w-md text-sm opacity-90">Scan a barcode or photograph a label. Checking for {profileName ? <b>{profileName}</b> : "you"}.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/scan" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-white px-4 text-sm font-bold text-brand-strong">
            <ScanLine className="size-5" aria-hidden /> Scan a product
          </Link>
          <Link href="/discover" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-white/15 px-4 text-sm font-semibold ring-1 ring-white/40">
            <Search className="size-4" aria-hidden /> Search
          </Link>
        </div>
        <ScanLine className="absolute -right-6 -top-6 size-40 opacity-10" aria-hidden />
      </section>

      {restrictions === 0 && (
        <Card className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold">Personalize your results</p>
            <p className="text-sm text-muted">Add allergies and diet preferences to get a fit / avoid verdict on every scan.</p>
          </div>
          <LinkButton href="/onboarding" variant="secondary">Set up profile</LinkButton>
        </Card>
      )}

      <div className="mt-6 grid gap-6 md:grid-cols-[1.4fr_1fr]">
        <section>
          <SectionTitle action={<Link href="/history" className="text-sm font-semibold text-brand">See all</Link>}>Recent scans</SectionTitle>
          {hist.loading ? (
            <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-20" />)}</div>
          ) : hist.data && hist.data.length ? (
            <div className="space-y-2">
              {hist.data.map((h) => <ProductCard key={h.id} p={h.product} sub={relDays(h.last_scanned_at)} />)}
            </div>
          ) : (
            <EmptyState title="No scans yet" body="Your scan history shows up here, and it's available offline in the mobile app." action={<LinkButton href="/scan">Scan your first product</LinkButton>} icon={<ScanLine className="size-6" />} />
          )}
        </section>
        <section>
          <SectionTitle>Explore</SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            {[
              { href: "/compare", icon: GitCompare, label: "Compare" },
              { href: "/ingredients", icon: BookOpen, label: "Ingredients" },
              { href: "/lists", icon: ListChecks, label: "Shopping lists" },
              { href: "/assistant", icon: MessageCircle, label: "Ask AI" },
              { href: "/profile", icon: Users, label: "Family" },
              { href: "/notifications", icon: Bell, label: "Alerts", badge: notes.data?.length },
              { href: "/recipes", icon: ChefHat, label: "Recipes" },
              { href: "/explore", icon: Compass, label: "More" },
            ].map((x) => (
              <Link key={x.href} href={x.href} className="card flex min-h-20 flex-col justify-between p-3 hover:border-brand/50">
                <x.icon className="size-5 text-brand" aria-hidden />
                <span className="flex items-center justify-between text-sm font-semibold">
                  {x.label} {x.badge ? <Badge tone="red">{x.badge}</Badge> : null}
                </span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </Page>
  );
}

function Landing() {
  return (
    <Page>
      <section className="grid items-center gap-8 py-6 md:grid-cols-2 md:py-14">
        <div>
          <Badge tone="brand">
            <Sparkles className="size-3.5" aria-hidden /> Built on FDA nutrition standards
          </Badge>
          <h1 className="mt-4 font-display text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
            Know what&apos;s inside.
            <br />
            <span className="text-brand">Understand what you eat.</span>
          </h1>
          <p className="mt-4 max-w-lg text-lg text-muted">
            Scan any packaged food for a transparent health score, plain-English ingredient explanations, allergen alerts for your whole family, and healthier swaps.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <LinkButton href="/register" className="px-6">
              Get started free <ArrowRight className="size-4" aria-hidden />
            </LinkButton>
            <LinkButton href="/scan" variant="secondary">
              <ScanLine className="size-4" aria-hidden /> Try a scan
            </LinkButton>
          </div>
          <p className="mt-3 text-xs text-muted">No account needed to scan. Data from Open Food Facts and USDA FoodData Central.</p>
        </div>
        <div className="card mx-auto w-full max-w-sm p-5">
          <div className="flex items-center gap-3">
            <LogoMark size={40} />
            <div>
              <p className="text-sm text-muted">Example breakdown</p>
              <p className="font-display font-bold">Every point explained</p>
            </div>
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {[
              ["−60", "Added sugars: 38 g per 12 fl oz = 76% DV", "text-bad"],
              ["−17", "Energy: 151 kcal per 12 fl oz", "text-warn"],
              ["−10", "Caffeine: not for children", "text-warn"],
              ["cap", "Poor nutrition limits the overall score", "text-grey"],
            ].map(([p, t, c]) => (
              <li key={t} className="flex gap-3 rounded-xl bg-surface-2 p-2.5">
                <span className={`w-10 shrink-0 font-bold tabular-nums ${c}`}>{p}</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>
      <section className="grid gap-3 sm:grid-cols-3">
        {[
          { icon: ShieldCheck, t: "Allergen-first", b: "US Big 9 and EU 14 allergens with contains / may contain / unknown. A good score never hides an allergen alert." },
          { icon: BookOpen, t: "Transparent science", b: "FDA Daily Values, regulatory findings and peer-reviewed sources, with clear evidence levels. No invented results." },
          { icon: Users, t: "For the whole family", b: "Profiles for every eater, with vegan, halal screening, keto, low-sodium and custom avoid lists." },
        ].map((f) => (
          <Card key={f.t}>
            <f.icon className="size-6 text-brand" aria-hidden />
            <p className="mt-2 font-display font-bold">{f.t}</p>
            <p className="mt-1 text-sm text-muted">{f.b}</p>
          </Card>
        ))}
      </section>
      <p className="mt-8 text-center text-xs text-muted">Food omniScan gives general nutrition information, not medical advice. Always read the package label.</p>
    </Page>
  );
}
