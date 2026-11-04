"""Builds the public Food omniScan pages for GitHub Pages (privacy policy, terms, account deletion).

    python site/build.py

Writes site/index.html, site/privacy/index.html, site/terms/index.html and site/account-deletion/index.html.
The text mirrors the web app's /privacy, /terms and /account-deletion pages; keep them in sync.
Google Play links to these pages, and the mobile app opens <WEB_URL>/privacy and <WEB_URL>/terms.
"""

import pathlib
import shutil

SITE = pathlib.Path(__file__).resolve().parent
SUPPORT = "iheanachohubert@gmail.com"
UPDATED = "4 November 2026"

PAGES: dict[str, tuple[str, str, str]] = {}

PAGES[""] = (
    "Food omniScan",
    "Know what's inside your food.",
    """
<div class="card">
  <p>Food omniScan reads any barcode or QR code on a food package and explains it in plain language: ingredients and
  additives, allergens for everyone in your family, Nutrition Facts, official recalls and better options on the same shelf.</p>
  <p>Scanning, scores, allergen alerts and recalls are free. Premium plans add AI meal plans, more AI questions and photo
  reads, vitamin tracking, pantry, grocery budget and household sharing.</p>
</div>
<h2>Legal</h2>
<ul>
  <li><a href="privacy/">Privacy Policy</a></li>
  <li><a href="terms/">Terms of Service</a></li>
  <li><a href="account-deletion/">Delete your account</a></li>
</ul>
<p class="note">Food omniScan gives general food information, not medical advice. Always read the package label.</p>
""",
)

PAGES["privacy"] = (
    "Privacy Policy",
    f"Last updated {UPDATED}",
    f"""
<p>Food omniScan ("we") helps you understand packaged food: you scan a barcode or photograph a label and we explain the
ingredients, nutrition, allergens and recalls. This policy explains what we collect, why, and the choices you have. It applies
to the Android and iOS apps and the website.</p>

<h2>What we collect</h2>
<ul>
  <li><b>Account details</b>: email address, display name, country and a securely hashed password.</li>
  <li><b>Eater profiles you create</b>: names, allergies, diet preferences, ingredients to avoid and goals. You choose whether to
  store these; they are used only to personalise results.</li>
  <li><b>What you do in the app</b>: products you scan or save, shopping lists, pantry, budget, food diary, water and weight
  entries, recipes, meal plans and product reviews.</li>
  <li><b>Photos you choose to send</b>: label, product or meal photos you ask the AI to read. Barcode scanning and on-device text
  reading happen on your phone and are not uploaded.</li>
  <li><b>Questions you ask the assistant</b>, so it can answer them.</li>
  <li><b>Subscription status</b>: your plan and renewal date. Payments are handled by Google Play, the App Store or Stripe; we never
  see or store card numbers.</li>
  <li><b>Basic technical data</b>: IP address and request logs kept for security and abuse prevention.</li>
</ul>
<p>We do not use advertising identifiers, sell personal data, or show third-party ads.</p>

<h2>How we use it</h2>
<ul>
  <li>To provide the service: scores, allergen and diet checks, alerts, diary and planning features.</li>
  <li>To answer AI requests. Questions and photos are sent to Google's Gemini API to generate an answer and are not used by us to
  train models.</li>
  <li>To manage your subscription and enforce plan allowances.</li>
  <li>To send the notifications you switch on (recalls, expiry reminders, weekly reports).</li>
  <li>To keep the service secure, moderate reported reviews and fix problems.</li>
</ul>

<h2>Who we share it with</h2>
<p>Only with service providers that run parts of the service for us: our cloud hosting and database provider, Google (Gemini AI),
and the payment providers you use (Google Play, Apple, Stripe, Paystack, RevenueCat for app-store receipts). Product lookups send
only the barcode to Open Food Facts and USDA FoodData Central. Product reviews you post are shown to other users without your name.
We share data with authorities only when the law requires it.</p>

<h2>Sensitive information</h2>
<p>Allergies and diet preferences can reveal health information. We store them only with your consent, use them only to check
foods for you, and you can remove them at any time. Food omniScan provides general nutrition information and is not a medical
device or medical advice.</p>

<h2>Your choices and rights</h2>
<ul>
  <li><b>Export</b> all your data from Profile, Privacy &amp; data.</li>
  <li><b>Delete your account</b> in the app (Profile, Privacy &amp; data, Delete account) or as described on our
  <a href="../account-deletion/">account deletion page</a>.</li>
  <li><b>Notifications</b> can be switched off in the app settings.</li>
  <li><b>Report or block</b>: you can report any review and block its author from the review's menu.</li>
  <li>Depending on where you live (for example the EU, UK, California or Nigeria), you may also have rights to access, correct
  or restrict use of your data. Contact us to use them.</li>
</ul>

<h2>Retention and security</h2>
<p>We keep your data while your account is open. When you delete your account, your profile, diary, lists and other personal data
are deleted immediately, and any backup copies are overwritten within 30 days. Product photos you submitted that moderators
approved stay as anonymous product data. Data is encrypted in transit (HTTPS) and passwords are hashed.</p>

<h2>Children</h2>
<p>Accounts are for people aged 13 and over. A parent can create eater profiles for children within their own account.</p>

<h2>Contact</h2>
<p>Questions or requests: <a href="mailto:{SUPPORT}">{SUPPORT}</a>. We will tell you here and in the app before making
significant changes to this policy.</p>
""",
)

PAGES["terms"] = (
    "Terms of Service",
    f"Last updated {UPDATED}",
    f"""
<p>By creating an account or using Food omniScan you agree to these terms. If you don't agree, please don't use the service.</p>

<h2>Information, not medical advice</h2>
<p>Food omniScan explains food labels, nutrition and ingredients using public data (Open Food Facts, USDA FoodData Central,
regulators and published research) and AI. It is general information only. It is not a medical device and does not diagnose,
treat or prevent any condition. Product data can be incomplete or out of date and AI answers can be wrong: <b>always read the
package label</b>, especially for allergies, and talk to a doctor or dietitian about your health.</p>

<h2>Your account</h2>
<p>You must be 13 or older. Keep your password safe; you are responsible for activity on your account. You can delete your
account at any time.</p>

<h2>Subscriptions</h2>
<ul>
  <li>Scanning, scores, allergen alerts, recalls and food-safety information are free. Plus, Premium and Family add the features
  shown on the plans screen in the app.</li>
  <li>Paid plans renew automatically each month or year until you cancel. Cancel any time in Google Play, the App Store, or your
  account on the website; you keep access until the end of the paid period.</li>
  <li>Purchases through Google Play or the App Store follow that store's refund rules. For web purchases, contact us within 14 days
  for a refund.</li>
  <li>Monthly AI allowances reset each calendar month and don't roll over. We may change prices or allowances with advance notice;
  changes apply from your next renewal.</li>
</ul>

<h2>Acceptable use and reviews</h2>
<p>Don't misuse the service: no scraping, reverse engineering, overloading it, uploading unlawful content, or submitting false
product information. Reviews must be honest and about the product: no spam, advertising, abuse, hate or personal information.
Anyone can report a review; reported reviews are checked by moderators and may be removed, and accounts that break these rules
may be suspended.</p>

<h2>Content you submit</h2>
<p>When you submit product photos, prices or reviews, you give us permission to use them to improve product information for
everyone. Approved product data may be shared under the Open Database License, like Open Food Facts.</p>

<h2>Liability</h2>
<p>The service is provided "as is". To the extent the law allows, we are not liable for indirect losses or for decisions made
from information in the app. Nothing in these terms limits rights you have under consumer law.</p>

<h2>Contact</h2>
<p><a href="mailto:{SUPPORT}">{SUPPORT}</a> · <a href="../privacy/">Privacy Policy</a></p>
""",
)

PAGES["account-deletion"] = (
    "Delete your Food omniScan account",
    "You can delete your account and data at any time.",
    f"""
<h2>In the app</h2>
<ol>
  <li>Open Food omniScan and go to <b>Profile</b>.</li>
  <li>Tap <b>Privacy &amp; data</b>.</li>
  <li>Tap <b>Delete my account</b>, type DELETE and confirm.</li>
</ol>

<h2>Without the app</h2>
<p>Email <a href="mailto:{SUPPORT}?subject=Delete%20my%20Food%20omniScan%20account">{SUPPORT}</a> from the address on your
account with the subject "Delete my Food omniScan account". We delete it within 30 days and confirm by email.</p>

<h2 id="some-data">Delete some data and keep your account</h2>
<ul>
  <li><b>Allergies, diets and avoid lists</b>: Profile, Privacy &amp; data, switch off "Store allergy &amp; diet information". They are deleted at once.</li>
  <li><b>Pantry items and shopping lists</b>: delete them from the Pantry and Shopping lists screens.</li>
  <li><b>Anything else</b> (eater profiles, diary, water and weight entries, scan history, saved products, purchases, recipes,
  meal plans, reviews): email <a href="mailto:{SUPPORT}?subject=Delete%20some%20of%20my%20data">{SUPPORT}</a> from the address
  on your account and say what to delete; we do it within 30 days and confirm by email.</li>
</ul>

<h2>What is deleted when you delete your account</h2>
<ul>
  <li>Your account, email and password.</li>
  <li>Eater profiles, allergies, diet preferences and avoid lists.</li>
  <li>Scan history, saved products, food diary, water and weight logs, shopping lists, pantry, budget, recipes, meal plans and reviews.</li>
  <li>Assistant conversations and photos you sent for AI reading.</li>
</ul>
<p>Kept: product photos and corrections that moderators already approved stay as anonymous product data (not linked to you), and
payment records that tax law requires us to keep. Any backup copies are overwritten within 30 days.</p>
<p class="note">Deleting your account does not cancel a Google Play or App Store subscription: cancel it in the store first.</p>
""",
)


def page(slug: str, title: str, sub: str, body: str) -> str:
    root = "./" if not slug else "../"
    full_title = title if not slug else f"{title} · Food omniScan"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full_title}</title>
<meta name="description" content="{sub}">
<link rel="icon" href="{root}icon.png">
<link rel="stylesheet" href="{root}style.css">
</head>
<body>
<header><div class="wrap bar"><img src="{root}icon.png" alt=""><a href="{root}">Food <b>omniScan</b></a></div><div class="stripe"></div></header>
<main class="wrap">
<h1>{title}</h1>
<p class="sub">{sub}</p>
{body.strip()}
</main>
<footer><div class="wrap"><a href="{root}privacy/">Privacy</a><a href="{root}terms/">Terms</a><a href="{root}account-deletion/">Delete account</a>
<span>Contact: <a href="mailto:{SUPPORT}">{SUPPORT}</a></span></div></footer>
</body>
</html>
"""


def main() -> None:
    icon = SITE.parent / "mobile" / "store" / "icon-512.png"
    if icon.exists():
        shutil.copyfile(icon, SITE / "icon.png")
    for slug, (title, sub, body) in PAGES.items():
        out = SITE / slug / "index.html" if slug else SITE / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(slug, title, sub, body), encoding="utf-8", newline="\n")
        print("wrote", out.relative_to(SITE.parent))


if __name__ == "__main__":
    main()
