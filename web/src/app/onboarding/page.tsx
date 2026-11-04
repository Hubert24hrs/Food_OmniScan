"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Button, Card, Page, Spinner } from "@/components/ui";
import { ProfileEditor } from "@/components/ProfileEditor";

export default function Onboarding() {
  const { me, activeProfile, loading, refresh } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !me) router.replace("/login?next=/onboarding");
  }, [loading, me, router]);
  if (loading || !me || !activeProfile) return <Spinner />;

  return (
    <Page title="Set up your food profile" subtitle="Tell us what to look out for. Every scan then gets a personal fits / check / avoid verdict.">
      {!me.consent_health_data ? (
        <Card>
          <p className="font-semibold">Allow Food omniScan to store allergy and diet information?</p>
          <p className="mt-1 text-sm text-muted">This is sensitive health data. It&apos;s used only to personalize results, never sold, and you can delete it any time.</p>
          <Button className="mt-4" onClick={async () => { await api("/me", { method: "PATCH", body: { consent_health_data: true } }); await refresh(); }}>
            Allow and continue
          </Button>
        </Card>
      ) : (
        <Card>
          <ProfileEditor key={activeProfile.id} profile={activeProfile} onSaved={async () => { await refresh(); router.push("/scan"); }} />
        </Card>
      )}
    </Page>
  );
}
