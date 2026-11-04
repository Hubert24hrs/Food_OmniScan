"use client";

import Image from "next/image";
import Link from "next/link";
import { BookOpen, CalendarDays, ChefHat, FlaskConical, Globe2, Home, Package, Trophy, Wallet } from "lucide-react";
import { Badge, IconTile, Page } from "@/components/ui";

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
      <div className="card rise mb-5 overflow-hidden p-2">
        <Image src="/brand/kitchen.svg" alt="" width={1280} height={832} unoptimized priority className="mx-auto h-44 w-auto rounded-xl object-contain sm:h-60" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((t, i) => (
          <Link key={t.href} href={t.href} className="card rise flex gap-3 p-4" style={{ animationDelay: `${i * 60}ms` }}>
            <IconTile index={i}><t.icon className="size-5" aria-hidden /></IconTile>
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
