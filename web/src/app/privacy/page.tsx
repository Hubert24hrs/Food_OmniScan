import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/ui";
import { SUPPORT_EMAIL } from "@/lib/legal";

export const metadata: Metadata = { title: "Privacy Policy · Food omniScan" };

const H = ({ children }: { children: React.ReactNode }) => <h2 className="mt-6 font-display text-lg font-bold">{children}</h2>;

export default function PrivacyPage() {
  return (
    <Page title="Privacy Policy" subtitle="Last updated 4 November 2026">
      <div className="card max-w-3xl space-y-3 p-6 text-sm leading-relaxed">
        <p>
          Food omniScan (&quot;we&quot;) helps you understand packaged food: you scan a barcode or photograph a label and we explain the ingredients, nutrition,
          allergens and recalls. This policy explains what we collect, why, and the choices you have. It applies to the Android and iOS apps and the website.
        </p>

        <H>What we collect</H>
        <ul className="list-disc space-y-1 pl-5">
          <li><b>Account details</b>: email address, display name, country and a securely hashed password.</li>
          <li><b>Eater profiles you create</b>: names, allergies, diet preferences, ingredients to avoid and goals. You choose whether to store these; they are used only to personalise results.</li>
          <li><b>What you do in the app</b>: products you scan or save, shopping lists, pantry, budget, food diary, water and weight entries, recipes and meal plans.</li>
          <li><b>Photos you choose to send</b>: label, product or meal photos you ask the AI to read. Barcode scanning and on-device text reading happen on your phone and are not uploaded.</li>
          <li><b>Questions you ask the assistant</b>, so it can answer them.</li>
          <li><b>Subscription status</b>: your plan and renewal date. Payments are handled by Google Play, the App Store or Stripe; we never see or store card numbers.</li>
          <li><b>Basic technical data</b>: IP address and request logs kept for security and abuse prevention.</li>
        </ul>
        <p>We do not use advertising identifiers, sell personal data, or show third-party ads.</p>

        <H>How we use it</H>
        <ul className="list-disc space-y-1 pl-5">
          <li>To provide the service: scores, allergen and diet checks, alerts, diary and planning features.</li>
          <li>To answer AI requests. Questions and photos are sent to Google&apos;s Gemini API to generate an answer and are not used by us to train models.</li>
          <li>To manage your subscription and enforce plan allowances.</li>
          <li>To send the notifications you switch on (recalls, expiry reminders, weekly reports).</li>
          <li>To keep the service secure and to fix problems.</li>
        </ul>

        <H>Who we share it with</H>
        <p>
          Only with service providers that run parts of the service for us: our cloud hosting and database provider, Google (Gemini AI), and the payment
          providers you use (Google Play, Apple, Stripe, Paystack, RevenueCat for app-store receipts). Product lookups send only the barcode to Open Food Facts and
          USDA FoodData Central. We share data with authorities only when the law requires it.
        </p>

        <H>Sensitive information</H>
        <p>
          Allergies and diet preferences can reveal health information. We store them only with your consent, use them only to check foods for you, and you can
          remove them at any time. Food omniScan provides general nutrition information and is not a medical device or medical advice.
        </p>

        <H>Your choices and rights</H>
        <ul className="list-disc space-y-1 pl-5">
          <li><b>Export</b> all your data from Profile → Privacy &amp; data.</li>
          <li><b>Delete your account</b> in the app (Profile → Privacy &amp; data → Delete account) or as described on our <Link href="/account-deletion" className="text-brand underline">account deletion page</Link>.</li>
          <li><b>Notifications</b> can be switched off in the app settings.</li>
          <li>Depending on where you live (for example the EU, UK, California or Nigeria), you may also have rights to access, correct or restrict use of your data. Contact us to use them.</li>
        </ul>

        <H>Retention and security</H>
        <p>
          We keep your data while your account is open. When you delete your account, your profile, diary, lists and other personal data are deleted
          immediately, and any backup copies are overwritten within 30 days. Product photos you submitted that moderators approved stay as anonymous product data. Data is encrypted
          in transit (HTTPS) and passwords are hashed.
        </p>

        <H>Children</H>
        <p>Accounts are for people aged 13 and over. A parent can create eater profiles for children within their own account.</p>

        <H>Contact</H>
        <p>
          Questions or requests: <a href={`mailto:${SUPPORT_EMAIL}`} className="text-brand underline">{SUPPORT_EMAIL}</a>. We will tell you here and in the app
          before making significant changes to this policy.
        </p>
      </div>
    </Page>
  );
}
