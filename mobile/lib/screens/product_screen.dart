import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../widgets/analysis_view.dart';
import '../widgets/common.dart';
import 'product_extras.dart';
import 'assistant_screen.dart';

/// Loads a product by barcode (scan flow) or id, with an offline cached fallback.
class ProductScreen extends StatefulWidget {
  const ProductScreen({super.key, this.barcode, this.productId, this.initial});
  final String? barcode;
  final String? productId;
  final Map<String, dynamic>? initial;

  @override
  State<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends State<ProductScreen> {
  Map<String, dynamic>? data;
  ApiException? error;
  bool offlineCopy = false;

  @override
  void initState() {
    super.initState();
    data = widget.initial;
    if (data == null) _load();
  }

  Future<void> _load() async {
    final app = context.read<AppState>();
    try {
      final path = widget.barcode != null ? '/products/barcode/${widget.barcode}' : '/products/${widget.productId}';
      final r = await app.api.get(path) as Map<String, dynamic>;
      await app.store.cacheProduct((r['product'] as Map)['id'] as String, r);
      if (mounted) setState(() => data = r);
    } on ApiException catch (e) {
      if (e.isNetwork && widget.productId != null) {
        final cached = await app.store.cachedProduct(widget.productId!);
        if (cached != null && mounted) {
          setState(() {
            data = cached;
            offlineCopy = true;
          });
          return;
        }
      }
      if (e.isNetwork && widget.barcode != null) await app.queueScan(widget.barcode!);
      if (mounted) setState(() => error = e);
    }
  }

  Future<void> _share(String productId) async {
    final r = await runAction(context, () => context.read<AppState>().api.post('/products/$productId/share'));
    if (r is! Map || !mounted) return;
    final url = '$webUrl${r['path']}';
    await Clipboard.setData(ClipboardData(text: url));
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Report link copied: $url')));
  }

  Future<void> _log(String productId) async {
    final servings = TextEditingController(text: '1');
    var meal = 'snack';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Log this product'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: servings, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Servings')),
            DropdownButtonFormField<String>(
              initialValue: meal,
              items: [for (final m in ['breakfast', 'lunch', 'dinner', 'snack']) DropdownMenuItem(value: m, child: Text(m))],
              onChanged: (v) => set(() => meal = v ?? 'snack'),
            ),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Log')),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final app = context.read<AppState>();
    await runAction(
      context,
      () => app.api.post('/diary/entries', {
        'product_id': productId,
        'servings': double.tryParse(servings.text) ?? 1,
        'meal_type': meal,
        'profile_id': app.activeProfile?['id'],
      }),
      ok: 'Logged in your diary',
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    if (error != null) {
      final notFound = error!.code == 'product_not_found';
      return Scaffold(
        appBar: AppBar(),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(notFound ? Icons.search_off : Icons.wifi_off, size: 48),
            const SizedBox(height: 12),
            Text(notFound ? "We couldn't find this product" : error!.message,
                textAlign: TextAlign.center, style: t.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            Text(
              notFound
                  ? 'Photograph the ingredient list and Nutrition Facts to analyze it now. You can add it on the web app for review.'
                  : error!.isNetwork
                      ? "You're offline. We saved this scan and will look it up when you reconnect."
                      : 'Please try again.',
              textAlign: TextAlign.center,
            ),
          ]),
        ),
      );
    }
    if (data == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [CircularProgressIndicator(), SizedBox(height: 12), Text('Analyzing…')])),
      );
    }
    final p = data!['product'] as Map<String, dynamic>;
    final prov = p['provenance'] as Map<String, dynamic>;
    return Scaffold(
      appBar: AppBar(title: Text(p['name'] as String? ?? 'Product')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (offlineCopy) const Padding(padding: EdgeInsets.only(bottom: 8), child: Text('Showing a saved offline copy.')),
        Row(children: [
          if (p['image_url'] != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network(p['image_url'] as String, width: 64, height: 64, fit: BoxFit.contain,
                  errorBuilder: (_, _, _) => const SizedBox(width: 64, height: 64)),
            ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p['name'] as String? ?? 'Unnamed product', style: t.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
              Text([p['brand'], p['quantity']].whereType<String>().join(' · ')),
            ]),
          ),
        ]),
        const SizedBox(height: 12),
        Wrap(spacing: 8, children: [
          OutlinedButton.icon(
            onPressed: () async {
              try {
                await context.read<AppState>().api.post('/favourites', {'product_id': p['id']});
                if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved')));
              } on ApiException catch (e) {
                if (context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
              }
            },
            icon: const Icon(Icons.favorite_border),
            label: const Text('Save'),
          ),
          if (!offlineCopy)
            FilledButton.tonalIcon(
              onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => AssistantScreen(productId: p['id'] as String, productName: p['name'] as String?))),
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Ask AI'),
            ),
          if (!offlineCopy)
            OutlinedButton.icon(onPressed: () => _share(p['id'] as String), icon: const Icon(Icons.share_outlined), label: const Text('Share')),
          if (!offlineCopy && context.read<AppState>().signedIn) ...[
            OutlinedButton.icon(onPressed: () => _log(p['id'] as String), icon: const Icon(Icons.restaurant), label: const Text('Log it')),
            OutlinedButton.icon(
              onPressed: () => runAction(context, () => context.read<AppState>().api.post('/pantry', {'product_id': p['id']}), ok: 'Added to your pantry'),
              icon: const Icon(Icons.kitchen_outlined),
              label: const Text('Pantry'),
            ),
          ],
        ]),
        const SizedBox(height: 12),
        AnalysisView(analysis: data!['analysis'] as Map<String, dynamic>),
        if (!offlineCopy) ...[const SizedBox(height: 12), ProductExtras(productId: p['id'] as String)],
        Padding(
          padding: const EdgeInsets.all(12),
          child: Text('${prov['attribution'] ?? prov['source']}', style: t.bodySmall),
        ),
      ]),
    );
  }
}
