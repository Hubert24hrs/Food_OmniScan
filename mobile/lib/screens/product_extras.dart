import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import '../widgets/score_widgets.dart';
import 'more_screens.dart';
import 'product_screen.dart';

/// Extra product sections shown under the analysis on the product screen.
class ProductExtras extends StatelessWidget {
  const ProductExtras({super.key, required this.productId});
  final String productId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Wrap(spacing: 8, runSpacing: 8, children: [
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => AlternativesScreen(productId: productId))),
          icon: const Icon(Icons.swap_horiz),
          label: const Text('Healthier alternatives'),
        ),
        if (app.signedIn) ...[
          OutlinedButton.icon(onPressed: () => _addToList(context), icon: const Icon(Icons.playlist_add), label: const Text('Add to list')),
          OutlinedButton.icon(
            onPressed: () => runAction(context, () => app.api.post('/favourites', {'product_id': productId, 'list_type': 'trusted'}), ok: 'Marked as trusted'),
            icon: const Icon(Icons.verified_outlined),
            label: const Text('Trusted'),
          ),
          OutlinedButton.icon(
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => CompareScreen(initial: [productId]))),
            icon: const Icon(Icons.compare_arrows),
            label: const Text('Compare'),
          ),
        ],
      ]),
      const SizedBox(height: 12),
      _Details(productId: productId),
      _Prices(productId: productId),
      ReviewsCard(productId: productId),
      if (app.signedIn)
        TextButton.icon(onPressed: () => _report(context), icon: const Icon(Icons.flag_outlined), label: const Text('Report incorrect information')),
    ]);
  }

  Future<void> _addToList(BuildContext context) async {
    final api = context.read<AppState>().api;
    await runAction(context, () async {
      final lists = (await api.get('/shopping-lists') as List).cast<Map<String, dynamic>>();
      final id = lists.isNotEmpty ? lists.first['id'] : (await api.post('/shopping-lists', {'name': 'Groceries'}) as Map)['id'];
      return api.post('/shopping-lists/$id/items', {'product_id': productId});
    }, ok: 'Added to your shopping list');
  }

  Future<void> _report(BuildContext context) async {
    var field = 'ingredients';
    final issue = TextEditingController();
    final suggested = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Report a problem'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              DropdownButtonFormField<String>(
                initialValue: field,
                decoration: const InputDecoration(labelText: 'What is wrong?'),
                items: const [
                  DropdownMenuItem(value: 'ingredients', child: Text('Ingredients')),
                  DropdownMenuItem(value: 'nutrition', child: Text('Nutrition facts')),
                  DropdownMenuItem(value: 'allergens', child: Text('Allergens')),
                  DropdownMenuItem(value: 'name', child: Text('Name or brand')),
                  DropdownMenuItem(value: 'image', child: Text('Photo')),
                  DropdownMenuItem(value: 'other', child: Text('Something else')),
                ],
                onChanged: (v) => set(() => field = v ?? 'other'),
              ),
              TextField(controller: issue, maxLines: 3, decoration: const InputDecoration(labelText: 'Describe the problem')),
              TextField(controller: suggested, decoration: const InputDecoration(labelText: 'Correct value (optional)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Send')),
          ],
        ),
      ),
    );
    if (ok != true || issue.text.trim().length < 5 || !context.mounted) return;
    await runAction(
      context,
      () => context.read<AppState>().api.post('/products/$productId/report', {
        'field': field,
        'issue': issue.text.trim(),
        if (suggested.text.trim().isNotEmpty) 'suggested_value': suggested.text.trim(),
      }),
      ok: 'Thanks, a moderator will review it',
    );
  }
}

class _Details extends StatelessWidget {
  const _Details({required this.productId});
  final String productId;

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/products/$productId/details',
      builder: (context, d, _) {
        final maker = d['manufacturer'] as Map<String, dynamic>?;
        final nafdac = d['nafdac'] as Map<String, dynamic>?;
        final labs = (d['lab_results'] as List).cast<Map<String, dynamic>>();
        final history = (d['history'] as List).cast<Map<String, dynamic>>();
        if (maker == null && nafdac == null && labs.isEmpty && history.isEmpty && d['brand'] == null) return const SizedBox.shrink();
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Product details', style: TextStyle(fontWeight: FontWeight.w800)),
              if (d['brand'] != null) Text('Brand: ${d['brand']}'),
              if (maker != null) Text('Made by: ${maker['name']}${maker['parent_company'] != null ? ' (part of ${maker['parent_company']})' : ''}'),
              if (nafdac != null) ...[
                const SizedBox(height: 6),
                Text('NAFDAC ${nafdac['number']}${nafdac['format_ok'] == true ? '' : ' (unusual format)'}', style: const TextStyle(fontWeight: FontWeight.w700)),
                Text('${nafdac['note']} Check it at greenbook.nafdac.gov.ng', style: const TextStyle(fontSize: 12)),
              ],
              if (labs.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Lab test results (this product)', style: TextStyle(fontWeight: FontWeight.w700)),
                for (final l in labs)
                  Text('• ${l['analyte']}: ${l['value'] ?? 'not detected'} ${l['unit']}'
                      '${l['exceeds_threshold'] == true ? ' — above limit' : ''} (${l['lab']}${l['batch'] != null ? ', batch ${l['batch']}' : ''})'),
              ],
              if (history.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Update history', style: TextStyle(fontWeight: FontWeight.w700)),
                for (final h in history.take(5))
                  Text('• ${(h['at'] as String).substring(0, 10)}: ${(h['action'] as String).replaceAll('.', ' ')}', style: const TextStyle(fontSize: 12)),
              ],
            ]),
          ),
        );
      },
    );
  }
}

class _Prices extends StatelessWidget {
  const _Prices({required this.productId});
  final String productId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return ApiView(
      path: '/products/$productId/prices',
      builder: (context, p, reload) {
        final stores = (p['where_to_buy'] as List).cast<Map<String, dynamic>>();
        final byStore = (p['by_store'] as List?)?.cast<Map<String, dynamic>>();
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Prices & where to buy', style: TextStyle(fontWeight: FontWeight.w800)),
              if (p['reports'] == 0) const Text('No prices reported yet.'),
              if (p['locked'] == true && stores.isNotEmpty) ...[
                Text('Seen at ${stores.map((s) => [s['store'], s['city']].whereType<String>().join(', ')).join('; ')}'),
                const UpgradeNotice(message: 'Compare prices across stores with Plus.', tier: 'plus'),
              ],
              if (byStore != null)
                for (final s in byStore) Text('${s['store']}${s['city'] != null ? ', ${s['city']}' : ''}: ${s['currency']} ${s['price']}'),
              Text(p['note'] as String, style: const TextStyle(fontSize: 12)),
              if (app.signedIn)
                TextButton.icon(
                  onPressed: () async {
                    await _reportPrice(context, app);
                    await reload();
                  },
                  icon: const Icon(Icons.sell_outlined),
                  label: const Text('Report a price'),
                ),
            ]),
          ),
        );
      },
    );
  }

  Future<void> _reportPrice(BuildContext context, AppState app) async {
    final price = TextEditingController();
    final store = TextEditingController();
    final city = TextEditingController();
    final currency = app.me?['currency'] as String? ?? 'USD';
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Report a shelf price'),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: price, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: InputDecoration(labelText: 'Price ($currency)')),
          TextField(controller: store, decoration: const InputDecoration(labelText: 'Store')),
          TextField(controller: city, decoration: const InputDecoration(labelText: 'City (optional)')),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Send')),
        ],
      ),
    );
    final p = double.tryParse(price.text);
    if (ok != true || p == null || store.text.trim().isEmpty || !context.mounted) return;
    await runAction(
      context,
      () => app.api.post('/products/$productId/prices', {
        'price': p,
        'currency': currency,
        'store': store.text.trim(),
        if (city.text.trim().isNotEmpty) 'city': city.text.trim(),
        'country': app.me?['country'] as String? ?? 'US',
      }),
      ok: 'Thanks for reporting a price',
    );
  }
}

class ReviewsCard extends StatelessWidget {
  const ReviewsCard({super.key, required this.productId});
  final String productId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return ApiView(
      path: '/products/$productId/reviews',
      builder: (context, r, reload) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Community reviews', style: TextStyle(fontWeight: FontWeight.w800)),
            Text(r['count'] == 0 ? 'No reviews yet.' : '${r['average']} / 5 from ${r['count']} review(s). Reviews don\'t change the score.'),
            for (final x in (r['reviews'] as List).take(5).cast<Map<String, dynamic>>())
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('★' * (x['rating'] as int) + '☆' * (5 - (x['rating'] as int)), style: const TextStyle(color: Brand.orange)),
                subtitle: x['body'] != null ? Text(x['body'] as String) : null,
                trailing: app.signedIn && x['mine'] != true
                    ? PopupMenuButton<String>(
                        tooltip: 'Report or block',
                        icon: const Icon(Icons.more_vert, size: 20),
                        onSelected: (v) async {
                          final done = v == 'report' ? await _report(context, app, x['id'] as String) : await _block(context, app, x['id'] as String);
                          if (done) await reload();
                        },
                        itemBuilder: (_) => const [
                          PopupMenuItem(value: 'report', child: ListTile(leading: Icon(Icons.flag_outlined), title: Text('Report review'))),
                          PopupMenuItem(value: 'block', child: ListTile(leading: Icon(Icons.block), title: Text('Block this reviewer'))),
                        ],
                      )
                    : null,
              ),
            if (app.signedIn)
              TextButton.icon(
                onPressed: () async {
                  await _write(context, app);
                  await reload();
                },
                icon: const Icon(Icons.rate_review_outlined),
                label: const Text('Write a review'),
              ),
          ]),
        ),
      ),
    );
  }

  /// Report a review as objectionable; it disappears for the reporter at once and for everyone after several reports.
  Future<bool> _report(BuildContext context, AppState app, String reviewId) async {
    var reason = 'spam';
    final note = TextEditingController();
    const reasons = {'spam': 'Spam or advertising', 'offensive': 'Offensive or abusive', 'false_info': 'False or misleading', 'other': 'Something else'};
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Report review'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              RadioGroup<String>(
                groupValue: reason,
                onChanged: (v) => set(() => reason = v ?? reason),
                child: Column(children: [for (final e in reasons.entries) RadioListTile<String>(value: e.key, title: Text(e.value))]),
              ),
              TextField(controller: note, maxLength: 500, decoration: const InputDecoration(hintText: 'Details (optional)')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Report')),
          ],
        ),
      ),
    );
    if (ok != true || !context.mounted) return false;
    final r = await runAction(
      context,
      () => app.api.post('/reviews/$reviewId/report', {'reason': reason, if (note.text.trim().isNotEmpty) 'note': note.text.trim()}),
      ok: "Thanks. You won't see this review again, and our moderators will check it.",
    );
    return r != null;
  }

  Future<bool> _block(BuildContext context, AppState app, String reviewId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('Block this reviewer?'),
        content: const Text("You won't see any of their reviews. They aren't told. You can unblock from Profile → Privacy & data."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Block')),
        ],
      ),
    );
    if (ok != true || !context.mounted) return false;
    return await runAction(context, () => app.api.post('/reviews/$reviewId/block-author'), ok: 'Reviewer blocked') != null;
  }

  Future<void> _write(BuildContext context, AppState app) async {
    var rating = 0;
    final body = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, set) => AlertDialog(
          title: const Text('Your review'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              for (var i = 1; i <= 5; i++)
                IconButton(
                  tooltip: '$i star${i > 1 ? 's' : ''}',
                  onPressed: () => set(() => rating = i),
                  icon: Icon(i <= rating ? Icons.star : Icons.star_border, color: Brand.orange),
                ),
            ]),
            TextField(controller: body, maxLines: 3, decoration: const InputDecoration(hintText: 'What did you think? (optional)')),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(c, true), child: const Text('Post')),
          ],
        ),
      ),
    );
    if (ok != true || rating == 0 || !context.mounted) return;
    await runAction(context, () => app.api.put('/products/$productId/reviews', {'rating': rating, if (body.text.trim().isNotEmpty) 'body': body.text.trim()}),
        ok: 'Review posted');
  }
}

class AlternativesScreen extends StatelessWidget {
  const AlternativesScreen({super.key, required this.productId});
  final String productId;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Healthier alternatives')),
      body: ApiView(
        path: '/products/$productId/alternatives',
        query: {if (app.activeProfile != null) 'profile_ids': app.activeProfile!['id'] as String},
        builder: (context, r, _) {
          final alts = (r['alternatives'] as List).cast<Map<String, dynamic>>();
          if (alts.isEmpty) return const Center(child: Padding(padding: EdgeInsets.all(24), child: Text('No better-scoring alternatives found in this category yet.')));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final a in alts)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text((a['product'] as Map)['name'] as String? ?? 'Unnamed', style: const TextStyle(fontWeight: FontWeight.w700)),
                      subtitle: Text([(a['product'] as Map)['brand'], if (a['sold_in_country'] == true) 'Sold in your country'].whereType<String>().join(' · ')),
                      trailing: MiniScore(score: a['score'] as int?, color: a['color'] as String?),
                      onTap: () => Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => ProductScreen(productId: (a['product'] as Map)['id'] as String))),
                    ),
                    for (final b in ((a['reasons'] as Map)['better'] as List).take(3)) Text('↑ $b', style: const TextStyle(color: Brand.good)),
                    for (final b in ((a['reasons'] as Map)['not_better'] as List).take(2)) Text('↓ $b', style: const TextStyle(color: Brand.warn)),
                  ]),
                ),
              ),
            Text(r['price_comparison'] as String, style: const TextStyle(fontSize: 12)),
          ]);
        },
      ),
    );
  }
}
