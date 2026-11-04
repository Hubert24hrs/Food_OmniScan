import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../core/theme.dart';
import '../screens/paywall_screen.dart';

/// Upgrade prompt for features that need a paid plan, with a button straight to the plans.
class UpgradeNotice extends StatelessWidget {
  const UpgradeNotice({super.key, required this.message, this.tier});
  final String message;
  final String? tier;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: Brand.tomatoSoft,
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.workspace_premium, color: Brand.tomato),
            const SizedBox(width: 8),
            Expanded(
              child: Text(tier != null ? 'Included with ${tierName(tier!)}' : 'Plan limit reached',
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Color(0xFF7F1D1D), fontSize: 15)),
            ),
          ]),
          const SizedBox(height: 4),
          Text(message, style: const TextStyle(color: Color(0xFF7F1D1D))),
          const SizedBox(height: 10),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: Brand.tomato, foregroundColor: Colors.white),
            onPressed: () => showPaywall(context, reason: message, tier: tier),
            icon: const Icon(Icons.lock_open),
            label: Text(tier != null ? 'Unlock with ${tierName(tier!)}' : 'See plans'),
          ),
        ]),
      ),
    );
  }
}

Widget errorView(Object e, {VoidCallback? retry}) {
  if (e is ApiException && e.isPlan) return UpgradeNotice(message: e.message, tier: e.requiredTier);
  return Padding(
    padding: const EdgeInsets.all(24),
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      Text(e is ApiException ? e.message : 'Something went wrong.', textAlign: TextAlign.center),
      if (retry != null) TextButton(onPressed: retry, child: const Text('Try again')),
    ]),
  );
}

/// Loads `path` and renders it; shows a spinner, an error, or an upgrade prompt.
class ApiView extends StatefulWidget {
  const ApiView({super.key, required this.path, required this.builder, this.query, this.signedIn = false});
  final String path;
  final Map<String, String>? query;
  final bool signedIn;
  final Widget Function(BuildContext context, dynamic data, Future<void> Function() reload) builder;

  @override
  State<ApiView> createState() => _ApiViewState();
}

class _ApiViewState extends State<ApiView> {
  late Future<dynamic> _future;

  @override
  void initState() {
    super.initState();
    _future = _fetch();
  }

  @override
  void didUpdateWidget(ApiView old) {
    super.didUpdateWidget(old);
    if (old.path != widget.path || old.query.toString() != widget.query.toString()) _future = _fetch();
  }

  Future<dynamic> _fetch() => context.read<AppState>().api.get(widget.path, query: widget.query);

  Future<void> _reload() async {
    final f = _fetch();
    setState(() => _future = f);
    await f;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.signedIn && !context.watch<AppState>().signedIn) {
      return const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('Sign in on the Profile tab first.')));
    }
    return FutureBuilder(
      future: _future,
      builder: (context, snap) {
        if (snap.hasError) return Center(child: errorView(snap.error!, retry: _reload));
        if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()));
        return widget.builder(context, snap.data, _reload);
      },
    );
  }
}

/// Runs an API action and reports success or failure in a snackbar.
Future<T?> runAction<T>(BuildContext context, Future<T> Function() action, {String? ok}) async {
  final messenger = ScaffoldMessenger.of(context);
  try {
    final r = await action();
    if (ok != null) messenger.showSnackBar(SnackBar(content: Text(ok)));
    return r;
  } on ApiException catch (e) {
    // Out of allowance or a paid feature: take them to the plans rather than a passing snackbar.
    if (context.mounted && handlePlanError(context, e)) return null;
    messenger.showSnackBar(SnackBar(content: Text(e.message)));
    return null;
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) =>
      Padding(padding: const EdgeInsets.fromLTRB(4, 16, 4, 8), child: Text(text, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)));
}
