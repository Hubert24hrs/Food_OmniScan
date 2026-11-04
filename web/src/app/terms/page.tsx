import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/ui";
import { SUPPORT_EMAIL } from "@/lib/legal";

export const metadata: Metadata = { title: "Terms of Service · Food omniScan" };

const H = ({ children }: { children: React.ReactNode }) => <h2 className="mt-6 font-display text-lg font-bold">{children}</h2>;

export default function TermsPage() {
  return (
    <Page title="Terms of Service" subtitle="Last updated 4 November 2026">
      <div className="card max-w-3xl space-y-3 p-6 text-sm leading-relaxed">
        <p>By creating an account or using Food omniScan you agree to these terms. If you don&apos;t agree, please don&apos;t use the service.</p>

        <H>Information, not medical advice</H>
        <p>
          Food omniScan explains food labels, nutrition and ingredients using public data (Open Food Facts, USDA FoodData Central, regulators and published
          research) and AI. It is general information only. It is not a medical device and does not diagnose, treat or prevent any condition. Product data can be
          incomplete or out of date and AI answers can be wrong: <b>always read the package label</b>, especially for allergies, and talk to a doctor or
          dietitian about your health.
        </p>

        <H>Your account</H>
        <p>You must be 13 or older. Keep your password safe; you are responsible for activity on your account. You can delete your account at any time.</p>

        <H>Subscriptions</H>
        <ul className="list-disc space-y-1 pl-5">
          <li>Scanning, scores, allergen alerts, recalls and food-safety information are free. Plus, Premium and Family add the features described on the <Link href="/subscription" className="text-brand underline">plans page</Link>.</li>
          <li>Paid plans renew automatically each month or year until you cancel. Cancel any time in Google Play, the App Store, or your account on the website; you keep access until the end of the paid period.</li>
          <li>Purchases through Google Play or the App Store follow that store&apos;s refund rules. For web purchases, contact us within 14 days for a refund.</li>
          <li>Monthly AI allowances reset each calendar month and don&apos;t roll over. We may change prices or allowances with advance notice; changes apply from your next renewal.</li>
        </ul>

        <H>Acceptable use</H>
        <p>Don&apos;t misuse the service: no scraping, reverse engineering, overloading it, uploading unlawful content, or submitting false product information.</p>

        <H>Content you submit</H>
        <p>
          When you submit product photos, prices or reviews, you give us permission to use them to improve product information for everyone. Approved product
          data may be shared under the Open Database License, like Open Food Facts.
        </p>

        <H>Liability</H>
        <p>
          The service is provided &quot;as is&quot;. To the extent the law allows, we are not liable for indirect losses or for decisions made from information in
          the app. Nothing in these terms limits rights you have under consumer law.
        </p>

        <H>Contact</H>
        <p>
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-brand underline">{SUPPORT_EMAIL}</a> · <Link href="/privacy" className="text-brand underline">Privacy Policy</Link>
        </p>
      </div>
    </Page>
  );
}
