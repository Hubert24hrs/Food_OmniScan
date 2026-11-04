import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';

/// Upgrade prompt for features that need a paid plan. Plans are bought on the web or in the store build.
class UpgradeNotice extends StatelessWidget {
  const UpgradeNotice({super.key, required this.message, this.tier});
  final String message;
  final String? tier;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      color: cs.primaryContainer,
      child: ListTile(
        leading: Icon(Icons.lock_outline, color: cs.onPrimaryContainer),
        title: Text(tier != null ? 'Included with ${tier![0].toUpperCase()}${tier!.substring(1)}' : 'Plan limit reached',
            style: TextStyle(fontWeight: FontWeight.w700, color: cs.onPrimaryContainer)),
        subtitle: Text(message, style: TextStyle(color: cs.onPrimaryContainer)),
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
    final tier = e.requiredTier;
    messenger.showSnackBar(SnackBar(
        content: Text(e.isPlan && tier != null ? '${e.message} (${tier[0].toUpperCase()}${tier.substring(1)} plan)' : e.message)));
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
