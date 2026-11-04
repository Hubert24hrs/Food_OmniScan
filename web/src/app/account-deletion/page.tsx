import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/ui";
import { SUPPORT_EMAIL } from "@/lib/legal";

export const metadata: Metadata = { title: "Delete your account · Food omniScan" };

export default function AccountDeletionPage() {
  return (
    <Page title="Delete your Food omniScan account" subtitle="You can delete your account and data at any time.">
      <div className="card max-w-3xl space-y-4 p-6 text-sm leading-relaxed">
        <section>
          <h2 className="font-display text-lg font-bold">In the app</h2>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            <li>Open Food omniScan and go to <b>Profile</b>.</li>
            <li>Tap <b>Privacy &amp; data</b>.</li>
            <li>Tap <b>Delete account</b>, type DELETE and confirm.</li>
          </ol>
          <p className="mt-2">
            On the website: sign in, open <Link href="/profile" className="text-brand underline">Profile</Link> and choose <b>Delete account</b>.
          </p>
        </section>
        <section>
          <h2 className="font-display text-lg font-bold">Without the app</h2>
          <p className="mt-2">
            Email <a href={`mailto:${SUPPORT_EMAIL}?subject=Delete%20my%20account`} className="text-brand underline">{SUPPORT_EMAIL}</a> from the address on your
            account with the subject &quot;Delete my account&quot;. We delete it within 30 days and confirm by email.
          </p>
        </section>
        <section>
          <h2 className="font-display text-lg font-bold">What is deleted</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Your account, email and password.</li>
            <li>Eater profiles, allergies, diet preferences and avoid lists.</li>
            <li>Scan history, saved products, food diary, water and weight logs, shopping lists, pantry, budget, recipes and meal plans.</li>
            <li>Assistant conversations and photos you sent for AI reading.</li>
          </ul>
          <p className="mt-2">
            Kept: product photos and corrections that moderators already approved stay as anonymous product data (not linked to you), and payment records that
            tax law requires us to keep. Any backup copies are overwritten within 30 days.
          </p>
          <p className="mt-2">Deleting your account does not cancel a Google Play or App Store subscription: cancel it in the store first.</p>
        </section>
      </div>
    </Page>
  );
}
