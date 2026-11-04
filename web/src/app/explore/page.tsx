"use client";

import Link from "next/link";
import { BookOpen, CalendarDays, ChefHat, FlaskConical, Globe2, Home, Package, Trophy, Wallet } from "lucide-react";
import { Badge, Page } from "@/components/ui";

const tiles = [
  { href: "/recipes", title: "Recipes", body: "Nigerian, US and European recipes, checked against your allergies. AI recipes on paid plans.", icon: ChefHat },
  { href: "/meal-plans", title: "Meal planner", body: "Plan the week and turn it into a shopping list.", icon: CalendarDays, plan: "Plus" },
  { href: "/pantry", title: "Pantry", body: "Track what's at home and get reminders before food expires.", icon: Package, plan: "Plus" },
  { href: "/budget", title: "Grocery budget", body: "Spending, shopping history and where prices are lowest.", icon: Wallet, plan: "Plus" },
  { href: "/household", title: "Household", body: "Share the pantry, lists and budget with family.", icon: Home, plan: "Family" },
  { href: "/rankings", title: "Category rankings", body: "Best-scoring products in each category, with the criteria shown.", icon: Trophy },
  { href: "/local-foods", title: "Nigerian foods", body: "Dishes and ingredients with Yoruba, Igbo, Hausa and Pidgin names.", icon: Globe2 },
  { href: "/safety", title: "Food safety research", body: "Heavy metals, microplastics, pesticides, glyphosate and aflatoxins: what the evidence says.", icon: FlaskConical },
  { href: "/learn", title: "Learn", body: "Short, sourced guides to labels, sugars, processing and more.", icon: BookOpen },
  { href: "/ingredients", title: "Ingredient encyclopedia", body: "Every ingredient and additive: what it does, and what the evidence says.", icon: FlaskConical },
];

export default function ExplorePage() {
  return (
    <Page title="Explore" subtitle="Everything beyond the scanner: cook, plan, shop and learn.">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((t) => (
          <Link key={t.href} href={t.href} className="card flex gap-3 p-4 transition hover:border-brand">
            <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand"><t.icon className="size-5" aria-hidden /></span>
            <span className="min-w-0">
              <span className="flex items-center gap-2 font-display font-bold">{t.title}{t.plan && <Badge tone="brand">{t.plan}</Badge>}</span>
              <span className="mt-0.5 block text-sm text-muted">{t.body}</span>
            </span>
          </Link>
        ))}
      </div>
    </Page>
  );
}
