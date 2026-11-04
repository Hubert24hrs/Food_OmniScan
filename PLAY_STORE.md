# Publishing Food omniScan on Google Play

This guide is written for an **individual** Google Play developer account. The app is listed as a **Food & Drink** app
(a food-label, grocery and recipe tool), **not** as a health or medical app.

## What is already done in the code

| Item | Where |
|---|---|
| Application ID `app.foodomniscan.food_omniscan` (permanent after the first upload) | `mobile/android/app/build.gradle.kts` |
| Target SDK 36, min SDK 24 | Flutter defaults / `build.gradle.kts` |
| Release signing with an upload key | `mobile/android/key.properties` + `mobile/android/upload-keystore.jks` (both gitignored) |
| Google Play Billing subscriptions (through RevenueCat), Restore purchases, Manage subscription link | `mobile/lib/core/billing.dart`, `mobile/lib/screens/paywall_screen.dart` |
| HTTPS only in release builds (plain HTTP is allowed in debug builds only) | `mobile/android/app/src/debug/AndroidManifest.xml` |
| Permissions: Camera (scanning), Internet, Billing. No location, contacts or storage permissions; photos use the system photo picker | merged manifest |
| In-app account deletion, plus a public web page for deletion requests | Profile → Privacy & data; `/account-deletion` |
| Privacy Policy and Terms pages | `/privacy`, `/terms` on the web app |
| Hi-res icon 512×512 and feature graphic 1024×500 | `mobile/store/` (regenerate with `python mobile/tool/store_graphics.py`) |

**Back up the upload key now.** Copy `mobile/android/upload-keystore.jks` and `mobile/android/key.properties` to a password
manager or another safe place outside this computer. With Play App Signing, a lost upload key can be reset by Google support,
but it takes days.

## 1. Put the backend and website online (HTTPS)

The store app must talk to a public HTTPS API. Follow `DEPLOYMENT.md`, then set at least:

```
ENVIRONMENT=production
JWT_SECRET=<long random string>
DATABASE_URL=postgresql+psycopg://...
GEMINI_API_KEY=<your Gemini key>
PUBLIC_APP_URL=https://<your web domain>
CORS_ORIGINS=https://<your web domain>
REVENUECAT_WEBHOOK_AUTH=<long random string, also entered in RevenueCat>
```

Deploy the web app with `NEXT_PUBLIC_API_URL=https://<api domain>/api/v1` and
`NEXT_PUBLIC_SUPPORT_EMAIL=<the support address you will put in the Play listing>`.
Check that `https://<web domain>/privacy`, `/terms` and `/account-deletion` open.

## 2. Create the subscriptions

**Play Console → your app → Monetize → Products → Subscriptions.** Create three subscriptions, each with two
auto-renewing base plans:

| Subscription ID | Base plan IDs | Suggested price (USD) |
|---|---|---|
| `plus` | `monthly`, `annual` | 3.99 / 39.99 |
| `premium` | `monthly`, `annual` | 7.99 / 79.99 |
| `family` | `monthly`, `annual` | 11.99 / 119.99 |

The IDs matter: the server reads the plan from the word `plus` / `premium` / `family`, and a yearly plan from the word
`annual`. Let Play convert prices to local currencies (for example Naira); you can adjust each country afterwards.
An optional free trial on `premium` (for example 7 days) usually lifts conversions.

**RevenueCat (free up to a revenue threshold):**
1. Create a project and add a **Google Play** app with package `app.foodomniscan.food_omniscan`.
2. Upload the Play service-account JSON key RevenueCat asks for (it explains the steps), so it can verify purchases.
3. Import the six products. Create entitlements `plus`, `premium` and `family` and attach the matching products.
4. Create an offering called `default` containing all six packages, and make it current.
5. **Integrations → Webhooks:** URL `https://<api domain>/api/v1/billing/webhooks/revenuecat`, Authorization header value =
   your `REVENUECAT_WEBHOOK_AUTH`.
6. Copy the **public Google Play SDK key** (starts with `goog_`). It is safe to put in the app.

## 3. Build the App Bundle

Increase `version:` in `mobile/pubspec.yaml` for every upload (for example `1.0.1+2`; the number after `+` must always go up), then:

```bash
cd mobile
flutter build appbundle --release --dart-define=API_URL=https://<api domain>/api/v1 --dart-define=WEB_URL=https://<web domain> --dart-define=REVENUECAT_GOOGLE_KEY=goog_xxxxxxxx
```

Upload `mobile/build/app/outputs/bundle/release/app-release.aab`. Accept **Play App Signing** when asked.
Without `REVENUECAT_GOOGLE_KEY`, the store build shows the plans but says subscriptions aren't available yet; it never sends
people to a web checkout, which Play doesn't allow.

## 4. Testing track (required for new individual accounts)

New personal developer accounts must run a **closed test with at least 12 testers who stay opted in for 14 days in a row**
before **Production** can be requested. Steps:
1. **Testing → Closed testing → Create track**, upload the bundle, add testers by email list or a Google Group.
2. Share the opt-in link; testers install from Play.
3. Add the same testers as **License testers** (Settings → License testing) so they can buy subscriptions without being charged.
4. After 14 days, apply for production access from the Dashboard.

## 5. Store listing

- **App name (30):** `Food omniScan: Food Scanner`
- **Short description (80):** `Scan food barcodes & labels: ingredients, allergens, recalls and smarter swaps.`
- **Category:** Food & Drink. **Tags:** Food & drink, Shopping, Cooking. Do not pick Health & Fitness or Medical.
- **Contact email:** your support address. **Privacy policy URL:** `https://<web domain>/privacy`.
- **Graphics:** `mobile/store/icon-512.png`, `mobile/store/feature-graphic.png`, and 4 to 8 phone screenshots
  (Home, a scanned product, Explore, Recipes / meal plan, the plans screen).

**Full description (suggested):**

> Know what's inside your food. Point your camera at any barcode or QR code on a package and Food omniScan explains it in
> plain language: ingredients and additives, allergens, Nutrition Facts, recalls, and better options on the same shelf.
>
> • Scan any barcode or QR code, or photograph the ingredients and Nutrition Facts label
> • Allergen checks for everyone in the family: peanuts, tree nuts, milk, gluten, sesame and more
> • Ingredient encyclopedia: what every additive and E-number does, with sources
> • Official food recalls from FDA, UK FSA and NAFDAC
> • Recipes from Nigeria, the US and Europe, shopping lists and a food diary
> • Nigerian foods with Yoruba, Igbo, Hausa and Pidgin names
> • Ask the AI assistant about any product or ingredient
>
> Premium plans add AI meal plans, more AI questions and photo reads, vitamin and mineral tracking, pantry with expiry
> reminders, grocery budget and price comparison, and household sharing.
>
> Food omniScan gives general food information. It is not medical advice: always read the package label.

Keep the listing about food, groceries and cooking. Avoid words like "diagnose", "treat", "medical", "disease" or
"clinical" anywhere in the listing and screenshots.

## 6. App content forms (Policy → App content)

| Form | Answer |
|---|---|
| Privacy policy | `https://<web domain>/privacy` |
| Ads | No, the app contains no ads |
| App access | Most features work without signing in. Give reviewers a demo account (email + password) on a Premium plan so they can see the paid features. |
| Content rating (IARC) | Reference / utility type app. No violence, sexual content, gambling or drugs. Users can share content: yes (product prices, reviews, product photos, all moderated). Expected rating: Everyone / PEGI 3. |
| Target audience | 13 and over. Not designed for children. |
| News app | No |
| Government app | No |
| Financial features | None |
| Health apps declaration | Leave the app out of the health categories, as decided: it is listed as a Food & Drink app. |
| Data safety | See below |

Reviewers may look at the food diary, water log, weight log and nutrient targets. If Google asks about them, describe them as
food and meal logging inside a food-information app; they make no medical claims and don't connect to Health Connect or
any sensor.

**Data safety answers:**
- Data is encrypted in transit: **Yes**. Users can request deletion: **Yes** (in-app and `https://<web domain>/account-deletion`).
- **Personal info:** Email address and Name: collected, used for account management and app functionality, not shared.
- **Health and fitness → Health info:** allergies and diet preferences the user enters. Collected, optional, used for app
  functionality (personalised allergen checks), not shared. (This is a privacy disclosure, separate from the health apps declaration.)
- **Photos:** photos the user chooses to send for AI label reading. Collected, optional, for app functionality, processed by
  Google Gemini as a service provider (not "shared" under Play's definition).
- **App activity:** in-app search history and other user-generated content (lists, diary, recipes). Collected, for app functionality.
- **Financial info → Purchase history:** subscription status. Collected, for app functionality. Payment details are handled by Google Play.
- Not collected: location, contacts, messages, device identifiers for ads, audio, calendar, files.

## 7. Before you press "Send for review"

- [ ] The release bundle was built with the real `API_URL`, `WEB_URL` and `REVENUECAT_GOOGLE_KEY`
- [ ] Sign up, scan, the paywall and a test subscription work on a real phone from the closed-test install
- [ ] The privacy, terms and account deletion pages load on the public web domain
- [ ] A reviewer demo account exists and is on Premium
- [ ] Upload key backed up off this computer
