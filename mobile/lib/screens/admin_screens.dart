import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api.dart';
import '../core/app_state.dart';
import '../core/theme.dart';
import '../widgets/common.dart';

/// Admin & moderation for admin/moderator accounts. The API checks the role on every request.
class AdminScreen extends StatelessWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context) {
    const tabs = [
      ('Overview', _Overview()),
      ('Moderation', _Moderation()),
      ('Products', _Products()),
      ('Ingredients', _Ingredients()),
      ('Research', _Research()),
      ('Lab & recalls', _LabRecalls()),
      ('Content', _Content()),
      ('Users', _Users()),
      ('Plans', _Plans()),
      ('Scoring', _Scoring()),
      ('Audit log', _Audit()),
    ];
    return DefaultTabController(
      length: tabs.length,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Admin & moderation'),
          bottom: TabBar(isScrollable: true, tabAlignment: TabAlignment.start, tabs: [for (final t in tabs) Tab(text: t.$1)]),
        ),
        body: TabBarView(children: [for (final t in tabs) t.$2]),
      ),
    );
  }
}

Future<String?> _reason(BuildContext context, String title, {String hint = 'Reason (kept in the audit log)'}) async {
  final c = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(controller: c, autofocus: true, decoration: InputDecoration(hintText: hint)),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('OK')),
      ],
    ),
  );
  return ok == true && c.text.trim().length >= 3 ? c.text.trim() : null;
}

ApiClient _api(BuildContext context) => context.read<AppState>().api;

class _Overview extends StatelessWidget {
  const _Overview();

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/admin/stats',
      builder: (context, s, _) => ListView(padding: const EdgeInsets.all(12), children: [
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final (l, k) in [('Users', 'users'), ('Active 30d', 'active_users_30d'), ('Products', 'products'), ('Scans 30d', 'scans_30d'), ('Pending', 'pending_submissions'), ('Ingredients', 'ingredients')])
            SizedBox(
              width: 108,
              child: Card(child: Padding(padding: const EdgeInsets.all(10), child: Column(children: [Text(l, style: const TextStyle(fontSize: 12)), Text('${s[k] ?? '—'}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800))]))),
            ),
        ]),
        FilledButton.tonalIcon(
          onPressed: () async {
            final r = await runAction(context, () => _api(context).post('/admin/jobs/daily'));
            if (r != null && context.mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Daily jobs: $r')));
          },
          icon: const Icon(Icons.play_arrow),
          label: const Text('Run daily jobs (reminders, reports, tips)'),
        ),
        ApiView(
          path: '/admin/analytics',
          builder: (context, a, _) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const SectionHeader('Popular products (30 days)'),
            for (final p in (a['top_products'] as List).cast<Map<String, dynamic>>()) ListTile(dense: true, title: Text(p['name'] as String? ?? 'Unnamed'), trailing: Text('${p['scans']}')),
            const SectionHeader('Most-scanned missing barcodes'),
            for (final b in (a['top_missing_barcodes'] as List).cast<Map<String, dynamic>>()) ListTile(dense: true, title: Text('${b['barcode']}'), trailing: Text('${b['scans']}')),
            const SectionHeader('Feature & AI usage'),
            for (final f in (a['feature_usage'] as List).cast<Map<String, dynamic>>())
              ListTile(dense: true, title: Text((f['feature'] as String).replaceAll('_', ' ')), trailing: Text('${f['uses']} · \$${f['est_cost_usd']}')),
          ]),
        ),
      ]),
    );
  }
}

class _Moderation extends StatelessWidget {
  const _Moderation();

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/admin/submissions',
      builder: (context, data, reload) {
        final rows = (data as List).cast<Map<String, dynamic>>();
        if (rows.isEmpty) return const Center(child: Text('No pending submissions or corrections.'));
        return ListView(padding: const EdgeInsets.all(12), children: [
          for (final s in rows)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${s['kind']} · ${s['barcode'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  Text(((s['payload'] as Map)['name'] ?? (s['payload'] as Map)['issue'] ?? '').toString()),
                  if ((s['payload'] as Map)['ingredients_text'] != null) Text('Ingredients: ${(s['payload'] as Map)['ingredients_text']}', maxLines: 3, overflow: TextOverflow.ellipsis),
                  Text('${(s['images'] as List).length} photo(s)', style: const TextStyle(fontSize: 12)),
                  Row(children: [
                    for (final (action, label) in [('approve', 'Approve'), ('needs_info', 'Needs info'), ('reject', 'Reject')])
                      Padding(
                        padding: const EdgeInsets.only(right: 6),
                        child: OutlinedButton(
                          onPressed: () async {
                            await runAction(context, () => _api(context).post('/admin/submissions/${s['id']}/review', {'action': action}), ok: label);
                            await reload();
                          },
                          child: Text(label),
                        ),
                      ),
                  ]),
                ]),
              ),
            ),
        ]);
      },
    );
  }
}

class _Products extends StatefulWidget {
  const _Products();

  @override
  State<_Products> createState() => _ProductsState();
}

class _ProductsState extends State<_Products> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search products'), onSubmitted: (v) => setState(() => q = v.trim())),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: OutlinedButton.icon(onPressed: () => _newProduct(context), icon: const Icon(Icons.add_box_outlined), label: const Text('Add a product')),
      ),
      Expanded(
        child: ApiView(
          path: '/admin/products',
          query: {if (q.isNotEmpty) 'q': q},
          builder: (context, data, reload) => ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (final p in (data as List).cast<Map<String, dynamic>>())
              ListTile(
                title: Text(p['name'] as String? ?? 'Unnamed'),
                subtitle: Text('${p['source']} · ${p['status']}${p['verified_at'] != null ? ' · verified' : ''} · ${(p['barcodes'] as List).join(', ')}'),
                trailing: PopupMenuButton<String>(
                  onSelected: (v) async {
                    final why = await _reason(context, v == 'verify' ? 'Verify product' : v == 'hide' ? 'Hide product' : 'Show product');
                    if (why == null || !context.mounted) return;
                    final body = {'reason': why, if (v == 'verify') 'verify': true, if (v == 'hide') 'status': 'hidden', if (v == 'show') 'status': 'active'};
                    await runAction(context, () => _api(context).patch('/admin/products/${p['id']}', body), ok: 'Updated');
                    await reload();
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(value: 'verify', child: Text('Mark verified')),
                    PopupMenuItem(value: p['status'] == 'hidden' ? 'show' : 'hide', child: Text(p['status'] == 'hidden' ? 'Show again' : 'Hide')),
                  ],
                ),
              ),
          ]),
        ),
      ),
    ]);
  }
}

Future<void> _newProduct(BuildContext context) async {
  const labels = {
    'barcode': 'Barcode',
    'name': 'Name',
    'brand': 'Brand',
    'category': 'Category',
    'ingredients_text': 'Ingredients',
    'nafdac_number': 'NAFDAC number',
    'countries': 'Countries sold (e.g. nigeria, united-states)',
  };
  final f = {for (final k in labels.keys) k: TextEditingController()};
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: const Text('Add a product'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [for (final e in f.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key]))]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
      ],
    ),
  );
  if (ok != true || !context.mounted) return;
  String? v(String k) => f[k]!.text.trim().isEmpty ? null : f[k]!.text.trim();
  await runAction(
    context,
    () => _api(context).post('/admin/products', {
      'barcode': f['barcode']!.text.trim(),
      'name': f['name']!.text.trim(),
      'brand': v('brand'),
      'category': v('category'),
      'ingredients_text': v('ingredients_text'),
      'nafdac_number': v('nafdac_number'),
      'countries': [for (final c in f['countries']!.text.split(',')) if (c.trim().isNotEmpty) c.trim()],
    }),
    ok: 'Product added',
  );
}

class _Ingredients extends StatefulWidget {
  const _Ingredients();

  @override
  State<_Ingredients> createState() => _IngredientsState();
}

class _IngredientsState extends State<_Ingredients> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search ingredients'), onSubmitted: (v) => setState(() => q = v.trim())),
      ),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: OutlinedButton.icon(onPressed: () => _newIngredient(context), icon: const Icon(Icons.add), label: const Text('Add an ingredient')),
      ),
      Expanded(
        child: ApiView(
          path: '/ingredients',
          query: {'limit': '100', if (q.isNotEmpty) 'q': q},
          builder: (context, data, reload) => ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (final i in (data['items'] as List).cast<Map<String, dynamic>>())
              ListTile(
                title: Text(i['name'] as String),
                subtitle: Text('${i['category']} · ${i['concern_level']}'),
                trailing: PopupMenuButton<String>(
                  onSelected: (v) async {
                    final why = await _reason(context, v == 'verify' ? 'Verify entry' : 'Set concern: $v');
                    if (why == null || !context.mounted) return;
                    await runAction(context, () => _api(context).patch('/admin/ingredients/${i['slug']}', {'reason': why, if (v == 'verify') 'verify': true, if (v != 'verify') 'concern_level': v}),
                        ok: 'Updated');
                    await reload();
                  },
                  itemBuilder: (_) => [
                    const PopupMenuItem(value: 'verify', child: Text('Mark verified')),
                    for (final c in ['beneficial', 'neutral', 'caution', 'concern', 'unknown']) PopupMenuItem(value: c, child: Text('Concern: $c')),
                  ],
                ),
              ),
          ]),
        ),
      ),
    ]);
  }
}

Future<void> _newIngredient(BuildContext context) async {
  const labels = {
    'slug': 'Slug (lowercase-with-dashes)',
    'name': 'Name',
    'category': 'Category (e.g. colour, oil, grain)',
    'function': 'What it does',
    'plain_language': 'Plain-language explanation',
    'e_number': 'E-number (optional)',
    'synonyms': 'Other names, comma-separated',
  };
  final f = {for (final k in labels.keys) k: TextEditingController()};
  var concern = 'neutral';
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => StatefulBuilder(
      builder: (d, set) => AlertDialog(
        title: const Text('Add an ingredient'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in f.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key])),
            DropdownButtonFormField<String>(
              initialValue: concern,
              decoration: const InputDecoration(labelText: 'Concern level'),
              items: [for (final c in ['beneficial', 'neutral', 'caution', 'concern', 'unknown']) DropdownMenuItem(value: c, child: Text(c))],
              onChanged: (v) => set(() => concern = v ?? 'neutral'),
            ),
            const SizedBox(height: 6),
            const Text('New entries start as pending verification.', style: TextStyle(fontSize: 12)),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      ),
    ),
  );
  if (ok != true || !context.mounted) return;
  String? v(String k) => f[k]!.text.trim().isEmpty ? null : f[k]!.text.trim();
  await runAction(
    context,
    () => _api(context).post('/admin/ingredients', {
      'slug': f['slug']!.text.trim(),
      'name': f['name']!.text.trim(),
      'category': f['category']!.text.trim(),
      'function': f['function']!.text.trim(),
      'plain_language': v('plain_language'),
      'e_number': v('e_number'),
      'concern_level': concern,
      'synonyms': [for (final x in f['synonyms']!.text.split(',')) if (x.trim().isNotEmpty) x.trim()],
    }),
    ok: 'Ingredient added',
  );
}

class _Research extends StatelessWidget {
  const _Research();

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/sources',
      builder: (context, data, reload) => ListView(padding: const EdgeInsets.all(12), children: [
        for (final s in (data as List).cast<Map<String, dynamic>>())
          ListTile(
            title: Text(s['title'] as String),
            subtitle: Text('${s['key']} · ${s['evidence_quality']}'),
            trailing: s['verified'] == true
                ? const Icon(Icons.verified, color: Brand.green)
                : TextButton(
                    onPressed: () async {
                      await runAction(context, () => _api(context).post('/admin/sources/${s['key']}/verify'), ok: 'Verified');
                      await reload();
                    },
                    child: const Text('Verify'),
                  ),
          ),
      ]),
    );
  }
}

class _LabRecalls extends StatelessWidget {
  const _LabRecalls();

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(12), children: [
      const SectionHeader('Lab reports'),
      ApiView(
        path: '/admin/lab-reports',
        builder: (context, data, reload) => Column(children: [
          OutlinedButton.icon(
            onPressed: () async {
              await _newLab(context);
              await reload();
            },
            icon: const Icon(Icons.science_outlined),
            label: const Text('Add a lab report'),
          ),
          if ((data as List).isEmpty) const Text('No lab reports yet.'),
          for (final r in data.cast<Map<String, dynamic>>())
            ListTile(
              title: Text('${r['analyte']}: ${r['value'] ?? 'n.d.'} ${r['unit']}'),
              subtitle: Text('${r['lab_name']}${r['batch'] != null ? ' · batch ${r['batch']}' : ''}'),
              trailing: r['verified'] == true
                  ? const Icon(Icons.verified, color: Brand.green)
                  : TextButton(
                      onPressed: () async {
                        await runAction(context, () => _api(context).post('/admin/lab-reports/${r['id']}/verify'), ok: 'Verified');
                        await reload();
                      },
                      child: const Text('Verify'),
                    ),
            ),
        ]),
      ),
      const SectionHeader('Recalls'),
      FilledButton.tonalIcon(onPressed: () => _newRecall(context), icon: const Icon(Icons.add_alert_outlined), label: const Text('Publish a recall')),
      ApiView(
        path: '/admin/recalls',
        builder: (context, data, _) => Column(children: [
          for (final r in (data as List).cast<Map<String, dynamic>>())
            ListTile(
              title: Text(r['title'] as String),
              subtitle: Text('${r['authority']} (${r['jurisdiction']}) · ${r['status']}${r['notified_at'] != null ? ' · users notified' : ''}'),
            ),
        ]),
      ),
    ]);
  }

  Future<void> _newLab(BuildContext context) async {
    const labels = {
      'barcode': 'Product barcode',
      'lab_name': 'Laboratory',
      'method': 'Method (e.g. ICP-MS)',
      'batch': 'Batch / lot',
      'tested_on': 'Tested on (YYYY-MM-DD)',
      'analyte': 'Analyte (e.g. lead)',
      'value': 'Result value',
      'unit': 'Unit (e.g. mg/kg)',
      'threshold': 'Legal limit (optional)',
      'threshold_jurisdiction': 'Limit jurisdiction (e.g. EU)',
    };
    final f = {for (final k in labels.keys) k: TextEditingController()};
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Add a lab report'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            for (final e in f.entries) TextField(controller: e.value, decoration: InputDecoration(labelText: labels[e.key])),
            const SizedBox(height: 6),
            const Text('Only enter product-specific results from a real report. It shows on the product once verified.', style: TextStyle(fontSize: 12)),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    final api = _api(context);
    String? v(String k) => f[k]!.text.trim().isEmpty ? null : f[k]!.text.trim();
    await runAction(context, () async {
      final product = await api.get('/products/barcode/${f['barcode']!.text.trim()}') as Map;
      return api.post('/admin/lab-reports', {
        'product_id': (product['product'] as Map)['id'],
        'lab_name': v('lab_name'),
        'method': v('method'),
        'batch': v('batch'),
        'tested_on': v('tested_on'),
        'analyte': v('analyte'),
        'value': double.tryParse(f['value']!.text.trim()),
        'unit': v('unit'),
        'threshold': double.tryParse(f['threshold']!.text.trim()),
        'threshold_jurisdiction': v('threshold_jurisdiction'),
      });
    }, ok: 'Lab report saved (unverified)');
  }

  Future<void> _newRecall(BuildContext context) async {
    final title = TextEditingController();
    final reason = TextEditingController();
    final authority = TextEditingController(text: 'NAFDAC');
    final jurisdiction = TextEditingController(text: 'NG');
    final barcode = TextEditingController();
    final url = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Publish a recall'),
        content: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
            TextField(controller: reason, maxLines: 2, decoration: const InputDecoration(labelText: 'Reason')),
            TextField(controller: authority, decoration: const InputDecoration(labelText: 'Authority (FDA, FSA, NAFDAC…)')),
            TextField(controller: jurisdiction, decoration: const InputDecoration(labelText: 'Country code (US, GB, NG…)')),
            TextField(controller: barcode, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Barcode (optional)')),
            TextField(controller: url, decoration: const InputDecoration(labelText: 'Official notice URL (https://)')),
            const SizedBox(height: 6),
            const Text('Only publish recalls confirmed by the authority. People who scanned the product are notified.', style: TextStyle(fontSize: 12)),
          ]),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Publish')),
        ],
      ),
    );
    if (ok != true || title.text.trim().isEmpty || reason.text.trim().isEmpty || !context.mounted) return;
    await runAction(
      context,
      () => _api(context).post('/admin/recalls', {
        'title': title.text.trim(),
        'reason': reason.text.trim(),
        'authority': authority.text.trim(),
        'jurisdiction': jurisdiction.text.trim().toUpperCase(),
        if (barcode.text.trim().isNotEmpty) 'barcode': barcode.text.trim(),
        if (url.text.trim().isNotEmpty) 'url': url.text.trim(),
      }),
      ok: 'Recall published',
    );
  }
}

class _Content extends StatelessWidget {
  const _Content();

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(12), children: [
      const SectionHeader('Articles'),
      FilledButton.tonalIcon(onPressed: () => _editArticle(context, null), icon: const Icon(Icons.post_add), label: const Text('New article')),
      ApiView(
        path: '/admin/articles',
        builder: (context, data, reload) => Column(children: [
          for (final a in (data as List).cast<Map<String, dynamic>>())
            ListTile(
              title: Text(a['title'] as String),
              subtitle: Text('${a['topic']} · ${a['status']}'),
              trailing: const Icon(Icons.edit_outlined),
              onTap: () async {
                await _editArticle(context, a);
                await reload();
              },
            ),
        ]),
      ),
      const SectionHeader('Recipes'),
      ApiView(
        path: '/admin/recipes',
        builder: (context, data, reload) => Column(children: [
          for (final r in (data as List).cast<Map<String, dynamic>>())
            SwitchListTile(
              title: Text(r['title'] as String),
              subtitle: Text(r['verified'] == true ? 'Verified' : 'Not verified'),
              value: r['verified'] == true,
              onChanged: (v) async {
                await runAction(context, () => _api(context).patch('/admin/recipes/${r['id']}', {'verified': v}));
                await reload();
              },
            ),
        ]),
      ),
      const SectionHeader('Announcement'),
      OutlinedButton.icon(
        icon: const Icon(Icons.campaign_outlined),
        label: const Text('Send an announcement to all users'),
        onPressed: () async {
          final title = await _reason(context, 'Announcement title', hint: 'Title');
          if (title == null || !context.mounted) return;
          final body = await _reason(context, 'Announcement text', hint: 'Message');
          if (body == null || !context.mounted) return;
          await runAction(context, () => _api(context).post('/admin/notifications/broadcast', {'title': title, 'body': body}), ok: 'Sent');
        },
      ),
    ]);
  }

  Future<void> _editArticle(BuildContext context, Map<String, dynamic>? a) async {
    final slug = TextEditingController(text: a?['slug'] as String? ?? '');
    final title = TextEditingController(text: a?['title'] as String? ?? '');
    final summary = TextEditingController(text: a?['summary'] as String? ?? '');
    final body = TextEditingController(text: a?['body'] as String? ?? '');
    var topic = a?['topic'] as String? ?? 'nutrition';
    var published = (a?['status'] ?? 'draft') == 'published';
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => StatefulBuilder(
        builder: (d, set) => AlertDialog(
          title: Text(a == null ? 'New article' : 'Edit article'),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: slug, enabled: a == null, decoration: const InputDecoration(labelText: 'Slug (lowercase-with-dashes)')),
              TextField(controller: title, decoration: const InputDecoration(labelText: 'Title')),
              TextField(controller: summary, decoration: const InputDecoration(labelText: 'Summary')),
              TextField(controller: body, maxLines: 6, decoration: const InputDecoration(labelText: 'Body (blank line = new paragraph)')),
              DropdownButtonFormField<String>(
                initialValue: topic,
                items: [for (final t in ['nutrition', 'processing', 'ingredients', 'safety', 'african', 'announcement']) DropdownMenuItem(value: t, child: Text(t))],
                onChanged: (v) => set(() => topic = v ?? 'nutrition'),
              ),
              SwitchListTile(value: published, onChanged: (v) => set(() => published = v), title: const Text('Published')),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true || !context.mounted) return;
    await runAction(
      context,
      () => _api(context).put('/admin/articles/${slug.text.trim()}', {
        'slug': slug.text.trim(),
        'title': title.text.trim(),
        'summary': summary.text.trim(),
        'body': body.text,
        'topic': topic,
        'status': published ? 'published' : 'draft',
        'source_keys': a?['source_keys'] ?? [],
        'region': a?['region'],
      }),
      ok: 'Saved',
    );
  }
}

class _Users extends StatefulWidget {
  const _Users();

  @override
  State<_Users> createState() => _UsersState();
}

class _UsersState extends State<_Users> {
  String q = '';

  @override
  Widget build(BuildContext context) {
    return Column(children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: TextField(decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search by email'), onSubmitted: (v) => setState(() => q = v.trim())),
      ),
      Expanded(
        child: ApiView(
          path: '/admin/users',
          query: {if (q.isNotEmpty) 'q': q},
          builder: (context, data, reload) => ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [
            for (final u in (data as List).cast<Map<String, dynamic>>())
              ListTile(
                title: Text(u['email'] as String),
                subtitle: Text('${u['role']}${u['is_active'] == true ? '' : ' · disabled'} · ${u['country'] ?? ''}'),
                trailing: PopupMenuButton<String>(
                  onSelected: (v) async {
                    final why = await _reason(context, 'Change: $v');
                    if (why == null || !context.mounted) return;
                    final body = <String, dynamic>{'reason': why};
                    if (v.startsWith('role:')) body['role'] = v.substring(5);
                    if (v.startsWith('tier:')) {
                      body['grant_tier'] = v.substring(5);
                      body['grant_days'] = 30;
                    }
                    if (v == 'disable') body['is_active'] = false;
                    if (v == 'enable') body['is_active'] = true;
                    await runAction(context, () => _api(context).patch('/admin/users/${u['id']}', body), ok: 'Updated');
                    await reload();
                  },
                  itemBuilder: (_) => [
                    for (final r in ['user', 'contributor', 'moderator', 'admin']) PopupMenuItem(value: 'role:$r', child: Text('Role: $r')),
                    for (final t in ['plus', 'premium', 'family']) PopupMenuItem(value: 'tier:$t', child: Text('Grant $t for 30 days')),
                    PopupMenuItem(value: u['is_active'] == true ? 'disable' : 'enable', child: Text(u['is_active'] == true ? 'Disable account' : 'Enable account')),
                  ],
                ),
              ),
          ]),
        ),
      ),
    ]);
  }
}

class _Plans extends StatelessWidget {
  const _Plans();

  @override
  Widget build(BuildContext context) {
    return ListView(padding: const EdgeInsets.all(12), children: [
      const SectionHeader('AI usage (30 days)'),
      ApiView(
        path: '/admin/ai-usage',
        builder: (context, data, _) => Column(children: [
          for (final r in (data as List).cast<Map<String, dynamic>>())
            ListTile(dense: true, title: Text('${r['feature']} (${r['status']})'), trailing: Text('${r['calls']} calls · \$${r['est_cost_usd']}')),
        ]),
      ),
      const SectionHeader('Plan limits'),
      const Text('null = unlimited, 0 = not included. Tap to change.', style: TextStyle(fontSize: 12)),
      ApiView(
        path: '/admin/entitlements',
        builder: (context, data, reload) => Column(children: [
          for (final e in (data as List).cast<Map<String, dynamic>>())
            ListTile(
              dense: true,
              title: Text('${e['feature']} · ${e['tier']}'),
              trailing: Text(e['monthly_limit'] == null ? 'unlimited' : '${e['monthly_limit']}'),
              onTap: () async {
                final v = await _reason(context, 'New limit for ${e['feature']} (${e['tier']})', hint: 'Number, or "unlimited"');
                if (v == null || !context.mounted) return;
                final limit = v.toLowerCase() == 'unlimited' ? null : int.tryParse(v);
                if (limit == null && v.toLowerCase() != 'unlimited') return;
                await runAction(context, () => _api(context).put('/admin/entitlements', {'tier': e['tier'], 'feature': e['feature'], 'monthly_limit': limit}), ok: 'Saved');
                await reload();
              },
            ),
        ]),
      ),
    ]);
  }
}

class _Scoring extends StatelessWidget {
  const _Scoring();

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/admin/methodologies',
      builder: (context, data, reload) => ListView(padding: const EdgeInsets.all(12), children: [
        const Text('Scoring versions are immutable: changes are published as a new version, then activated.', style: TextStyle(fontSize: 12)),
        FilledButton.tonalIcon(
          onPressed: () async {
            final all = data.cast<Map<String, dynamic>>();
            final active = all.firstWhere((m) => m['is_active'] == true, orElse: () => all.first);
            await _publish(context, active);
            await reload();
          },
          icon: const Icon(Icons.tune),
          label: const Text('New version from the active one'),
        ),
        for (final m in (data as List).cast<Map<String, dynamic>>())
          ListTile(
            title: Text('${m['version']} · ${m['name']}'),
            subtitle: Text(m['notes'] as String? ?? ''),
            trailing: m['is_active'] == true
                ? const Chip(label: Text('Active'))
                : TextButton(
                    onPressed: () async {
                      await runAction(context, () => _api(context).post('/admin/methodologies/${m['version']}/activate'), ok: 'Activated');
                      await reload();
                    },
                    child: const Text('Activate'),
                  ),
          ),
      ]),
    );
  }
}

Future<void> _publish(BuildContext context, Map<String, dynamic> base) async {
  final config = Map<String, dynamic>.from(base['config'] as Map);
  final weights = Map<String, dynamic>.from(config['weights'] as Map);
  final ctrls = {for (final e in weights.entries) e.key: TextEditingController(text: '${e.value}')};
  final version = TextEditingController();
  final notes = TextEditingController();
  final ok = await showDialog<bool>(
    context: context,
    builder: (d) => AlertDialog(
      title: const Text('Publish a new scoring version'),
      content: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: version, decoration: InputDecoration(labelText: 'Version (e.g. 2026.12-us.2)', hintText: 'was ${base['version']}')),
          for (final e in ctrls.entries)
            TextField(controller: e.value, keyboardType: TextInputType.number, decoration: InputDecoration(labelText: 'Weight: ${e.key.replaceAll('_', ' ')}')),
          TextField(controller: notes, maxLines: 2, decoration: const InputDecoration(labelText: 'What changed and why')),
          const SizedBox(height: 6),
          const Text('Weights must add up to 100. The server validates and dry-runs the new version.', style: TextStyle(fontSize: 12)),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d, false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, true), child: const Text('Publish')),
      ],
    ),
  );
  if (ok != true || !context.mounted) return;
  config['weights'] = {for (final e in ctrls.entries) e.key: int.tryParse(e.value.text.trim()) ?? weights[e.key]};
  config['version'] = version.text.trim();
  await runAction(
    context,
    () => _api(context).post('/admin/methodologies', {
      'version': version.text.trim(),
      'name': base['name'],
      'config': config,
      'notes': notes.text.trim(),
    }),
    ok: 'Published (not yet active)',
  );
}

class _Audit extends StatelessWidget {
  const _Audit();

  @override
  Widget build(BuildContext context) {
    return ApiView(
      path: '/admin/audit-logs',
      builder: (context, data, _) => ListView(padding: const EdgeInsets.all(12), children: [
        for (final r in (data as List).cast<Map<String, dynamic>>())
          ListTile(
            dense: true,
            title: Text('${r['action']} · ${r['entity']} ${r['entity_id'] ?? ''}'),
            subtitle: Text('${(r['created_at'] as String).substring(0, 16).replaceAll('T', ' ')}${r['note'] != null ? ' · ${r['note']}' : ''}'),
          ),
      ]),
    );
  }
}
