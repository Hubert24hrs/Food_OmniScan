"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";
import { BookOpen, Home, NotebookPen, ScanLine, Search, Shield, UserRound } from "lucide-react";
import { Logo } from "./Logo";
import { useAuth } from "@/lib/auth";

const nav = [
  { href: "/", label: "Home", icon: Home },
  { href: "/discover", label: "Discover", icon: Search },
  { href: "/scan", label: "Scan", icon: ScanLine, primary: true },
  { href: "/diary", label: "Diary", icon: NotebookPen },
  { href: "/profile", label: "Profile", icon: UserRound },
];

function useIsActive() {
  const path = usePathname();
  return (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
}

function DesktopNav() {
  const isActive = useIsActive();
  const { me } = useAuth();
  return (
    <nav className="hidden items-center gap-1 lg:flex" aria-label="Main">
      {nav.map((n) => (
        <Link
          key={n.href}
          href={n.href}
          aria-current={isActive(n.href) ? "page" : undefined}
          className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold ${n.primary ? "bg-brand text-white dark:text-[#06201d]" : isActive(n.href) ? "bg-surface-2 text-ink" : "text-muted hover:text-ink"}`}
        >
          <n.icon className="size-4" aria-hidden /> {n.label}
        </Link>
      ))}
      <Link href="/ingredients" className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold ${isActive("/ingredients") ? "bg-surface-2" : "text-muted hover:text-ink"}`}>
        <BookOpen className="size-4" aria-hidden /> Ingredients
      </Link>
      {me && (me.role === "admin" || me.role === "moderator") && (
        <Link href="/admin" className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold text-muted hover:text-ink">
          <Shield className="size-4" aria-hidden /> Admin
        </Link>
      )}
    </nav>
  );
}

function MobileNav() {
  const isActive = useIsActive();
  return (
    <nav aria-label="Main" className="pb-safe fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 backdrop-blur lg:hidden">
      <ul className="mx-auto grid max-w-md grid-cols-5 items-end px-2 pt-2">
        {nav.map((n) => (
          <li key={n.href} className="flex justify-center">
            <Link
              href={n.href}
              aria-current={isActive(n.href) ? "page" : undefined}
              className={n.primary ? "-mt-7 flex flex-col items-center gap-1 text-xs font-semibold text-brand" : `flex min-w-14 flex-col items-center gap-1 py-1 text-xs font-semibold ${isActive(n.href) ? "text-brand" : "text-muted"}`}
            >
              {n.primary ? (
                <span className="grid size-14 place-items-center rounded-2xl bg-brand text-white shadow-lg ring-4 ring-bg dark:text-[#06201d]">
                  <n.icon className="size-7" aria-hidden />
                </span>
              ) : (
                <n.icon className="size-6" aria-hidden />
              )}
              {n.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function AccountControl() {
  const { me, profiles, activeProfile, setActiveProfile } = useAuth();
  if (!me)
    return (
      <Link href="/login" className="rounded-xl px-3 py-2 text-sm font-semibold text-brand">
        Sign in
      </Link>
    );
  if (profiles.length > 1)
    return (
      <select aria-label="Active eater profile" className="rounded-xl border border-line bg-surface px-2 py-1.5 text-sm font-semibold" value={activeProfile?.id} onChange={(e) => setActiveProfile(e.target.value)}>
        {profiles.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    );
  return (
    <Link href="/profile" className="hidden rounded-full bg-brand-soft px-3 py-1.5 text-sm font-semibold text-brand-strong sm:block dark:text-brand">
      {me.display_name || me.email.split("@")[0]}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line bg-surface/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-3 px-4">
          <Link href="/" aria-label="Food omniScan home">
            <Logo />
          </Link>
          <Suspense fallback={null}>
            <DesktopNav />
          </Suspense>
          <AccountControl />
        </div>
      </header>
      <main id="main">{children}</main>
      <Suspense fallback={null}>
        <MobileNav />
      </Suspense>
    </div>
  );
}
