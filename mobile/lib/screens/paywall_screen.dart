import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:purchases_flutter/purchases_flutter.dart' show Package;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../core/billing.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import '../widgets/fresh.dart';
import 'account_screens.dart';

String tierName(String t) => t.isEmpty ? t : '${t[0].toUpperCase()}${t.substring(1)}';

/// Lower-cases a label's first letter for use mid-sentence, unless it starts with an acronym ("AI …").
String midSentence(String label) =>
    label.length < 2 || label.substring(0, 2) == label.substring(0, 2).toUpperCase() ? label : '${label[0].toLowerCase()}${label.substring(1)}';

bool _paywallOpen = false;

/// Opens the plans screen. `reason` explains why (e.g. "You've used all 5 AI questions"),
/// `tier` is the plan to preselect. Ignored if a paywall is already showing.
Future<void> showPaywall(BuildContext context, {String? reason, String? tier}) async {
  if (_paywallOpen) return;
  _paywallOpen = true;
  try {
    await Navigator.of(context, rootNavigator: true)
        .push(MaterialPageRoute(fullscreenDialog: true, builder: (_) => PaywallScreen(reason: reason, tier: tier)));
  } finally {
    _paywallOpen = false;
  }
}

/// If `e` means "this needs a paid plan" or "allowance used up", open the paywall and return true.
bool handlePlanError(BuildContext context, Object e) {
  if (e is! ApiException || !e.isPlan || !context.mounted) return false;
  showPaywall(context, reason: e.message, tier: e.requiredTier);
  return true;
}

/// Once a day (never on the first day) free users see the plans when they open the app.
Future<void> maybeDailyUpsell(BuildContext context) async {
  final app = context.read<AppState>();
  if (!app.isFree) return;
  final prefs = await SharedPreferences.getInstance();
  final now = DateTime.now().millisecondsSinceEpoch;
  final first = prefs.getInt('omniscan.first_open');
  if (first == null) {
    await prefs.setInt('omniscan.first_open', now);
    return;
  }
  const day = 24 * 60 * 60 * 1000;
  final last = prefs.getInt('omniscan.last_upsell') ?? 0;
  if (now - first < day || now - last < day) return;
  await prefs.setInt('omniscan.last_upsell', now);
  if (context.mounted) await showPaywall(context);
}

const _benefits = <(IconData, String, String)>[
  (Icons.calendar_month, 'AI meal plans', 'Weekly plans with Nigerian, US and European dishes'),
  (Icons.auto_awesome, 'Much more AI', 'Up to 500 questions and 300 photo reads a month'),
  (Icons.monitor_heart_outlined, 'Vitamins, minerals & reports', 'Weekly and monthly nutrition reports'),
  (Icons.kitchen, 'Pantry & expiry reminders', 'Never waste food again'),
  (Icons.sell_outlined, 'Budget & price comparison', 'See where it is cheaper'),
  (Icons.translate, 'Assistant in your language', 'Pidgin, Yoruba, Igbo, Hausa, French, Spanish'),
  (Icons.groups_outlined, 'Family sharing', 'Shared pantry, lists and budget (Family)'),
];

/// The plans / upgrade screen: benefits, monthly or yearly plans, checkout and this month's usage.
class PaywallScreen extends StatefulWidget {
  const PaywallScreen({super.key, this.reason, this.tier});
  final String? reason;
  final String? tier;

  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> with WidgetsBindingObserver {
  late final Future<(List<Map<String, dynamic>>, Map<String, Package>)> _data = _load();
  late String tier = widget.tier ?? 'premium';
  String interval = 'year';
  bool busy = false;
  bool _waitingForWeb = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final current = context.read<AppState>().tier;
    if (widget.tier == null && current == 'premium') tier = 'family';
    if (widget.tier == null && current == 'family') tier = 'family';
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Back from the browser checkout (test builds): pick up the new plan.
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && _waitingForWeb) {
      _waitingForWeb = false;
      _awaitUpgrade();
    }
  }

  Future<(List<Map<String, dynamic>>, Map<String, Package>)> _load() async {
    final api = context.read<AppState>().api;
    final plans = (await api.get('/billing/plans') as List).cast<Map<String, dynamic>>();
    return (plans, await StoreBilling.packages());
  }

  Future<void> _awaitUpgrade() async {
    final app = context.read<AppState>();
    final before = app.tier;
    // Store purchases reach the server through a webhook, usually within seconds.
    for (var i = 0; i < 8 && mounted; i++) {
      await app.refresh();
      if (app.tier != before) break;
      await Future<void>.delayed(const Duration(seconds: 2));
    }
    if (!mounted) return;
    final upgraded = app.tier != before;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(upgraded ? "You're on ${tierName(app.tier)}. Enjoy!" : 'Payment received. Your plan will update in a minute.')));
    if (upgraded) Navigator.of(context).pop();
  }

  Future<void> _buy(Map<String, Package> packages) async {
    final app = context.read<AppState>();
    if (!app.signedIn) {
      await Navigator.of(context).push(MaterialPageRoute(builder: (_) => const ProfileScreen()));
      return;
    }
    setState(() => busy = true);
    final r = await StoreBilling.buy(tier, interval, package: packages['${tier}_$interval'], api: app.api);
    if (!mounted) return;
    setState(() => busy = false);
    final messenger = ScaffoldMessenger.of(context);
    switch (r) {
      case BuyResult.purchased:
        await _awaitUpgrade();
      case BuyResult.openedWeb:
        _waitingForWeb = true;
        messenger.showSnackBar(const SnackBar(content: Text('Finish checkout in your browser, then come back here.')));
      case BuyResult.cancelled:
        break;
      case BuyResult.unavailable:
        messenger.showSnackBar(const SnackBar(content: Text("This plan isn't available in your store yet. Please try again later.")));
      case BuyResult.failed:
        messenger.showSnackBar(const SnackBar(content: Text("The payment didn't go through. You haven't been charged.")));
    }
  }

  Future<void> _restore() async {
    setState(() => busy = true);
    final ok = await StoreBilling.restore();
    if (!mounted) return;
    setState(() => busy = false);
    if (ok) {
      await _awaitUpgrade();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('No active subscription found for this Google account.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Plans'), actions: [
        if (StoreBilling.enabled) TextButton(onPressed: busy ? null : _restore, child: const Text('Restore')),
      ]),
      body: FutureBuilder(
        future: _data,
        builder: (context, snap) {
          if (snap.hasError) return Center(child: errorView(snap.error!));
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final (plans, packages) = snap.data!;
          final paid = {for (final p in plans.where((p) => p['tier'] != 'free')) p['tier'] as String: p};
          final sel = paid[tier] ?? paid.values.first;
          final pkg = packages['${tier}_$interval'];
          final price = pkg?.storeProduct.priceString ?? '\$${interval == 'year' ? sel['annual_usd'] : sel['monthly_usd']}';
          final current = app.tier;
          return Column(children: [
            Expanded(
              child: ListView(padding: const EdgeInsets.fromLTRB(16, 4, 16, 16), children: [
                _Hero(reason: widget.reason, current: current),
                const SizedBox(height: 16),
                for (final (i, (icon, title, sub)) in _benefits.indexed)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Row(children: [
                      IconTile(icon: icon, index: i, size: 38),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text(sub, style: TextStyle(fontSize: 12.5, color: cs.onSurfaceVariant)),
                        ]),
                      ),
                    ]),
                  ),
                const SizedBox(height: 16),
                Center(
                  child: SegmentedButton<String>(
                    segments: [
                      const ButtonSegment(value: 'month', label: Text('Monthly')),
                      ButtonSegment(value: 'year', label: Text('Yearly · save ${_saving(sel)}%')),
                    ],
                    selected: {interval},
                    onSelectionChanged: (s) => setState(() => interval = s.first),
                  ),
                ),
                const SizedBox(height: 12),
                for (final p in paid.values)
                  _PlanOption(
                    plan: p,
                    interval: interval,
                    package: packages['${p['tier']}_$interval'],
                    selected: p['tier'] == tier,
                    current: p['tier'] == current,
                    onTap: () => setState(() => tier = p['tier'] as String),
                  ),
                const SizedBox(height: 8),
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: const Text('Compare every plan', style: TextStyle(fontWeight: FontWeight.w700)),
                  children: [
                    for (final p in plans)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(tierName(p['tier'] as String), style: const TextStyle(fontWeight: FontWeight.w800)),
                        subtitle: Text([for (final f in p['features'] as List) '✓ $f'].join('\n')),
                      ),
                  ],
                ),
                if (app.signedIn && app.allowances.isNotEmpty) ...[
                  const SectionHeader('Your allowance this month'),
                  for (final a in app.allowances) AllowanceMeter(label: a.label, used: a.used, limit: a.limit),
                ],
                const SizedBox(height: 8),
                Text(
                  'Scanning, scores, allergen alerts, recalls and food-safety information stay free for everyone.',
                  style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
                ),
              ]),
            ),
            SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 8),
                decoration: BoxDecoration(color: cs.surface, border: Border(top: BorderSide(color: cs.outlineVariant))),
                child: Column(mainAxisSize: MainAxisSize.min, children: [
                  if (current == tier)
                    OutlinedButton.icon(
                      onPressed: () => launchUrl(manageSubscriptionsUrl, mode: LaunchMode.externalApplication),
                      icon: const Icon(Icons.settings_outlined),
                      label: Text("You're on ${tierName(tier)} · Manage subscription"),
                    )
                  else
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: Brand.tomato, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 16)),
                        onPressed: busy ? null : () => _buy(packages),
                        child: busy
                            ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white))
                            : Text(
                                app.signedIn
                                    ? 'Get ${tierName(tier)} · $price/${interval == 'year' ? 'year' : 'month'}'
                                    : 'Create a free account to continue',
                                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                      ),
                    ),
                  const SizedBox(height: 6),
                  Text(
                    StoreBilling.enabled
                        ? 'Billed through Google Play. Renews automatically; cancel any time in Google Play.'
                        : StoreBilling.webFallback
                            ? 'Test build: checkout opens in your browser.'
                            : 'Renews automatically; cancel any time.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11.5, color: cs.onSurfaceVariant),
                  ),
                  Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    TextButton(onPressed: () => launchUrl(Uri.parse('$webUrl/terms')), child: const Text('Terms', style: TextStyle(fontSize: 12))),
                    TextButton(onPressed: () => launchUrl(Uri.parse('$webUrl/privacy')), child: const Text('Privacy', style: TextStyle(fontSize: 12))),
                  ]),
                ]),
              ),
            ),
          ]);
        },
      ),
    );
  }

  static int _saving(Map<String, dynamic> p) {
    final m = (p['monthly_usd'] as num?)?.toDouble() ?? 0;
    final y = (p['annual_usd'] as num?)?.toDouble() ?? 0;
    if (m == 0 || y == 0) return 0;
    return ((1 - y / (m * 12)) * 100).round();
  }
}

class _Hero extends StatelessWidget {
  const _Hero({this.reason, required this.current});
  final String? reason;
  final String current;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(colors: [Brand.green, Brand.greenBright], begin: Alignment.topLeft, end: Alignment.bottomRight),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.asset('assets/brand/app_icon_256.png', width: 48, height: 48)),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
            child: Text('${tierName(current)} plan', style: const TextStyle(color: Brand.green, fontWeight: FontWeight.w800, fontSize: 12)),
          ),
        ]),
        const SizedBox(height: 14),
        const Text('Unlock the full Food omniScan',
            style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w800, height: 1.15)),
        const SizedBox(height: 6),
        const Text('Smarter meals, more AI, and the whole family covered.', style: TextStyle(color: Colors.white, fontSize: 14.5)),
        if (reason != null) ...[
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Brand.tomatoSoft, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              const Icon(Icons.lock_clock_outlined, color: Brand.tomato, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(reason!, style: const TextStyle(color: Color(0xFF7F1D1D), fontWeight: FontWeight.w600))),
            ]),
          ),
        ],
      ]),
    );
  }
}

class _PlanOption extends StatelessWidget {
  const _PlanOption(
      {required this.plan, required this.interval, required this.selected, required this.current, required this.onTap, this.package});
  final Map<String, dynamic> plan;
  final String interval;
  final Package? package;
  final bool selected;
  final bool current;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final t = plan['tier'] as String;
    final yearly = interval == 'year';
    final usd = (yearly ? plan['annual_usd'] : plan['monthly_usd']) as num?;
    final price = package?.storeProduct.priceString ?? '\$$usd';
    final perMonth = yearly
        ? (package?.storeProduct.pricePerMonthString ?? (usd != null ? '\$${(usd / 12).toStringAsFixed(2)}' : null))
        : null;
    final features = (plan['features'] as List).cast<String>().where((f) => !f.startsWith('Everything')).take(2);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Material(
        color: selected ? Brand.greenSoft.withValues(alpha: Theme.of(context).brightness == Brightness.dark ? 0.15 : 1) : cs.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(color: selected ? Brand.greenBright : cs.outlineVariant, width: selected ? 2.5 : 1),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off, color: selected ? Brand.greenBright : cs.outline),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Wrap(spacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
                    Text(tierName(t), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                    if (t == 'premium') const _Tag('MOST POPULAR', Brand.tomato),
                    if (current) const _Tag('YOUR PLAN', Brand.green),
                  ]),
                  const SizedBox(height: 4),
                  for (final f in features) Text(f, style: TextStyle(fontSize: 12.5, color: cs.onSurfaceVariant)),
                ]),
              ),
              const SizedBox(width: 8),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(price, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                Text(yearly ? 'a year' : 'a month', style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant)),
                if (perMonth != null) Text('$perMonth/mo', style: const TextStyle(fontSize: 12, color: Brand.green, fontWeight: FontWeight.w700)),
              ]),
            ]),
          ),
        ),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  const _Tag(this.text, this.color);
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(6)),
        child: Text(text, style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800, letterSpacing: 0.4)),
      );
}

/// "3 of 5 left" bar for one monthly allowance.
class AllowanceMeter extends StatelessWidget {
  const AllowanceMeter({super.key, required this.label, required this.used, required this.limit});
  final String label;
  final int used;
  final int limit;

  @override
  Widget build(BuildContext context) {
    final left = (limit - used).clamp(0, limit);
    final low = left <= (limit / 5).ceil();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13))),
          Text('$left of $limit left', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: low ? Brand.tomato : null)),
        ]),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: limit == 0 ? 1 : used / limit,
            minHeight: 7,
            color: low ? Brand.tomato : Brand.greenBright,
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
          ),
        ),
      ]),
    );
  }
}

/// Crown pill for app bars: always one tap from the plans for anyone not paying.
class UpgradeChip extends StatelessWidget {
  const UpgradeChip({super.key});

  @override
  Widget build(BuildContext context) {
    if (!context.watch<AppState>().isFree) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(
        avatar: const Icon(Icons.workspace_premium, color: Colors.white, size: 18),
        label: const Text('Go Premium', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
        backgroundColor: Brand.tomato,
        side: BorderSide.none,
        shape: const StadiumBorder(),
        onPressed: () => showPaywall(context),
      ),
    );
  }
}

/// Home-screen card for free users: what Premium adds, plus the allowance that is closest to running out.
class UpgradeBanner extends StatelessWidget {
  const UpgradeBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    if (!app.isFree) return const SizedBox.shrink();
    final a = app.allowances.firstOrNull;
    return Card(
      color: Brand.tomato,
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => showPaywall(context),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.workspace_premium, color: Colors.white, size: 28),
              const SizedBox(width: 10),
              const Expanded(
                child: Text('Get more with Premium', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
              ),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: Colors.white, foregroundColor: Brand.tomato),
                onPressed: () => showPaywall(context),
                child: const Text('See plans', style: TextStyle(fontWeight: FontWeight.w800)),
              ),
            ]),
            const SizedBox(height: 8),
            const Text('AI meal plans, vitamins & reports, pantry, budget and price comparison. Plans from \$3.99.',
                style: TextStyle(color: Colors.white)),
            if (a != null) ...[
              const SizedBox(height: 10),
              Text('${(a.limit - a.used).clamp(0, a.limit)} of ${a.limit} free ${midSentence(a.label)} left this month',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12.5)),
              const SizedBox(height: 4),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(value: a.used / a.limit, minHeight: 6, color: Colors.white, backgroundColor: Colors.white24),
              ),
            ],
          ]),
        ),
      ),
    );
  }
}

/// Slim prompt under paid-feature previews (product page, diary…).
class UpsellStrip extends StatelessWidget {
  const UpsellStrip({super.key, required this.text, this.tier = 'plus'});
  final String text;
  final String tier;

  @override
  Widget build(BuildContext context) {
    if (!context.watch<AppState>().isFree) return const SizedBox.shrink();
    return Card(
      color: Brand.sunSoft,
      child: ListTile(
        leading: const Icon(Icons.workspace_premium, color: Brand.sun),
        title: Text(text, style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF713F12), fontSize: 14)),
        trailing: const Icon(Icons.chevron_right, color: Brand.sun),
        onTap: () => showPaywall(context, tier: tier),
      ),
    );
  }
}
