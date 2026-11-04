import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:purchases_flutter/purchases_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import 'api.dart';

/// RevenueCat public SDK key for Google Play (starts with `goog_`; it is safe to ship). Set it for store builds:
///   flutter build appbundle --dart-define=REVENUECAT_GOOGLE_KEY=goog_xxx
/// Play Console product IDs must contain the tier, and "annual" for yearly plans
/// (plus_monthly, plus_annual, premium_monthly, premium_annual, family_monthly, family_annual):
/// the backend's RevenueCat webhook maps them to plans. Purchases are only ever unlocked server-side.
const revenueCatGoogleKey = String.fromEnvironment('REVENUECAT_GOOGLE_KEY');

/// Where users manage or cancel a Play subscription.
final manageSubscriptionsUrl = Uri.parse('https://play.google.com/store/account/subscriptions');

enum BuyResult { purchased, cancelled, openedWeb, unavailable, failed }

/// In-app subscriptions: Google Play Billing (through RevenueCat) in store builds. Test builds without a key
/// fall back to the web checkout; release builds without a key say subscriptions aren't available yet,
/// because Play doesn't allow sending people to outside payment pages.
class StoreBilling {
  static bool get enabled => revenueCatGoogleKey.isNotEmpty && !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  /// Debug / test builds can upgrade on the web app instead.
  static bool get webFallback => !enabled && !kReleaseMode;

  static bool _configured = false;

  /// Tie purchases to the signed-in Food omniScan account (RevenueCat's app user ID = our user ID).
  static Future<void> identify(String? userId) async {
    if (!enabled) return;
    try {
      if (!_configured) {
        await Purchases.configure(PurchasesConfiguration(revenueCatGoogleKey)..appUserID = userId);
        _configured = true;
      } else if (userId != null) {
        await Purchases.logIn(userId);
      } else if (!await Purchases.isAnonymous) {
        await Purchases.logOut();
      }
    } on PlatformException catch (e) {
      debugPrint('Billing setup failed: ${e.message}');
    }
  }

  /// Store packages keyed "tier_month" / "tier_year", with localised prices.
  static Future<Map<String, Package>> packages() async {
    if (!enabled || !_configured) return {};
    try {
      final current = (await Purchases.getOfferings()).current;
      final out = <String, Package>{};
      for (final p in current?.availablePackages ?? <Package>[]) {
        final id = p.storeProduct.identifier.toLowerCase();
        final tier = ['family', 'premium', 'plus'].firstWhere(id.contains, orElse: () => '');
        if (tier.isEmpty) continue;
        final yearly = p.packageType == PackageType.annual || id.contains('annual') || id.contains('year');
        out['${tier}_${yearly ? 'year' : 'month'}'] = p;
      }
      return out;
    } on PlatformException {
      return {};
    }
  }

  static Future<BuyResult> buy(String tier, String interval, {Package? package, required ApiClient api}) async {
    if (enabled) {
      if (package == null) return BuyResult.unavailable;
      try {
        await Purchases.purchase(PurchaseParams.package(package));
        return BuyResult.purchased;
      } on PlatformException catch (e) {
        return PurchasesErrorHelper.getErrorCode(e) == PurchasesErrorCode.purchaseCancelledError ? BuyResult.cancelled : BuyResult.failed;
      }
    }
    if (!webFallback) return BuyResult.unavailable;
    // Test builds: Stripe checkout on the web, or the web subscription page if Stripe isn't set up.
    Uri url;
    try {
      final r = await api.post('/billing/checkout', {'tier': tier, 'interval': interval}) as Map;
      url = Uri.parse(r['url'] as String);
    } on ApiException {
      url = Uri.parse('$webUrl/subscription?tier=$tier&interval=$interval');
    }
    return await launchUrl(url, mode: LaunchMode.externalApplication) ? BuyResult.openedWeb : BuyResult.failed;
  }

  static Future<bool> restore() async {
    if (!enabled || !_configured) return false;
    try {
      final info = await Purchases.restorePurchases();
      return info.entitlements.active.isNotEmpty;
    } on PlatformException {
      return false;
    }
  }
}
