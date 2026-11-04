"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { Button, Card, ErrorBox, Field, inputCls, Page } from "@/components/ui";

const COUNTRIES: [string, string][] = [
  ["US", "United States"], ["GB", "United Kingdom"], ["CA", "Canada"], ["IE", "Ireland"], ["DE", "Germany"], ["FR", "France"],
  ["ES", "Spain"], ["IT", "Italy"], ["NL", "Netherlands"], ["SE", "Sweden"], ["NG", "Nigeria"], ["GH", "Ghana"], ["KE", "Kenya"],
  ["ZA", "South Africa"], ["AU", "Australia"],
];

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [f, setF] = useState({ email: "", password: "", display_name: "", country: "US", accept_terms: false, consent_health_data: true });
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f, v: string | boolean) => setF((s) => ({ ...s, [k]: v }));

  return (
    <Page>
      <Card className="mx-auto mt-6 max-w-md">
        <h1 className="font-display text-2xl font-extrabold">Create your account</h1>
        <p className="mt-1 text-sm text-muted">Free forever for scanning, scores and allergen alerts.</p>
        <form
          className="mt-5 space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError(null);
            try {
              await register(f);
              router.push("/onboarding");
            } catch (err) {
              setError(err);
            } finally {
              setBusy(false);
            }
          }}
        >
          <Field label="Name (optional)">
            <input className={inputCls} autoComplete="given-name" value={f.display_name} onChange={(e) => set("display_name", e.target.value)} />
          </Field>
          <Field label="Email">
            <input className={inputCls} type="email" autoComplete="email" required value={f.email} onChange={(e) => set("email", e.target.value)} />
          </Field>
          <Field label="Password" hint="At least 8 characters, with an uppercase letter and a number.">
            <input className={inputCls} type="password" autoComplete="new-password" required minLength={8} maxLength={72} value={f.password} onChange={(e) => set("password", e.target.value)} />
          </Field>
          <Field label="Country" hint="Sets label standards and currency. US uses FDA Daily Values.">
            <select className={inputCls} value={f.country} onChange={(e) => set("country", e.target.value)}>
              {COUNTRIES.map(([c, n]) => (
                <option key={c} value={c}>
                  {n}
                </option>
              ))}
            </select>
          </Field>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 size-4" checked={f.consent_health_data} onChange={(e) => set("consent_health_data", e.target.checked)} />
            <span>
              Store my allergy and diet information so results can be personalized. <span className="text-muted">This is sensitive health data. You can withdraw consent and delete it at any time.</span>
            </span>
          </label>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-1 size-4" required checked={f.accept_terms} onChange={(e) => set("accept_terms", e.target.checked)} />
            <span>I agree to the Terms of Service and Privacy Policy, and I understand Food omniScan isn&apos;t medical advice.</span>
          </label>
          {error ? <ErrorBox error={error} /> : null}
          <Button type="submit" loading={busy} className="w-full">
            Create account
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-brand">
            Sign in
          </Link>
        </p>
      </Card>
    </Page>
  );
}
